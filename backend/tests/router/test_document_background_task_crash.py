"""T53 回归测试：后台文档处理的清理失败 / 意外异常不得打死服务（P-17）。

背景（2026-09-16 补跑 T08 时实测）：

    POST /knowledge-bases/{kb_id}/documents  →  HTTP 200
    后台 process_document：DocMind 解析 → 27 切片 → 1024 维向量 → 成功写入 Milvus kb_demo
    紧接着 finally 里的 os.remove(file_path) 抛异常
    → 异常逸出整个 Starlette BackgroundTask、穿透 ASGI
    → **整个 uvicorn 进程终止**；客户端已收到的 200 因 socket 未正常关闭而表现为读超时

根因与触发值无关：`os.remove` 在**外层** try 的 finally 中，而内层 `except Exception`
只包住文档处理那一段 → 清理异常**必然逸出**；且该函数由 `background_tasks.add_task` 调度，
运行时机在响应发出**之后**，异常没有任何调用方接管。

本文件按三层验证，**都不依赖基础设施**（无 Docker / 无 LLM / 无网络）：

1. **清理守卫层** —— `_remove_file_quietly` 正常删、抛 OSError 时只告警不外抛、文件不存在时无操作；
2. **处理过程层** —— 清理抛异常时 `process_document` 仍正常返回、文档状态仍为 `completed`
   （即「清理失败不污染处理结果」），且保留文件而非假装成功；
3. **调度边界层** —— `run_document_processing` 吞掉任意未预期异常、成功路径原样透传；
4. **源码锁** —— 上传路由必须把 `run_document_processing` 交给 `background_tasks`，
   且全文件只剩唯一的 `os.remove(`（在守卫内部、被 `except OSError` 包住）。

变异检查见 PR 描述：① 撤掉 `_remove_file_quietly` 的 try/except → 用例失败；
② 把 `add_task` 目标改回 `process_document` → 用例失败。
"""

import logging
import os
import pathlib
import re
import sys
import types

import pytest

import router.knowledge_router as kr

ROUTER = pathlib.Path(__file__).resolve().parents[2] / "app" / "router" / "knowledge_router.py"


# --------------------------------------------------------------------------
# 替身：最小化的 DB 会话与文档模型，避免拉起真实 Postgres
# --------------------------------------------------------------------------

class _FakeDoc:
    def __init__(self):
        self.filename = "华电科工.pdf"
        self.status = "pending"
        self.chunk_count = None
        self.error_message = None


class _FakeQuery:
    def __init__(self, doc):
        self._doc = doc

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._doc


class _FakeSession:
    def __init__(self, doc):
        self._doc = doc
        self.commits = 0
        self.closed = False

    def query(self, *args, **kwargs):
        return _FakeQuery(self._doc)

    def commit(self):
        self.commits += 1

    def close(self):
        self.closed = True


def _stub_docmind(monkeypatch, result):
    """把 `service.docmind_service` 换成最小替身。

    `process_document` 是在**函数体内**执行 `from service.docmind_service import ...`，
    因此改写 sys.modules 即可命中，无需导入真实模块（它依赖外部配置）。
    """
    fake = types.ModuleType("service.docmind_service")
    fake.process_document_with_docmind = lambda **kwargs: result
    monkeypatch.setitem(sys.modules, "service.docmind_service", fake)


# --------------------------------------------------------------------------
# 1) 清理守卫层
# --------------------------------------------------------------------------

def test_remove_file_quietly_deletes_existing_file(tmp_path):
    """正常路径必须仍然真的删掉文件 —— 守卫不是「不再清理」的借口。"""
    target = tmp_path / "upload.pdf"
    target.write_bytes(b"%PDF-1.7")

    kr._remove_file_quietly(str(target))

    assert not target.exists()


def test_remove_file_quietly_is_noop_when_missing(tmp_path):
    """文件不存在时静默通过（并发/重试场景：别人已删）。"""
    kr._remove_file_quietly(str(tmp_path / "never-existed.pdf"))


def test_remove_file_quietly_swallows_oserror(tmp_path, monkeypatch, caplog):
    """🔒 P-17 直接修复点：`os.remove` 抛 OSError 时**只告警、绝不外抛**。

    修复前 `os.remove` 直接写在 finally 里，PermissionError 会一路逸出后台任务。
    """
    target = tmp_path / "locked.pdf"
    target.write_bytes(b"%PDF-1.7")

    def _boom(path):
        raise PermissionError(13, "file is in use by another process")

    monkeypatch.setattr(os, "remove", _boom)

    with caplog.at_level(logging.WARNING, logger=kr.__name__):
        kr._remove_file_quietly(str(target))  # 修复前这里会抛 PermissionError

    assert target.exists(), "清理失败时应保留文件，而不是假装成功"
    assert any("临时文件清理失败" in r.message for r in caplog.records), "清理失败必须留下 warning"


# --------------------------------------------------------------------------
# 2) 处理过程层：清理失败不得污染处理结果
# --------------------------------------------------------------------------

async def test_process_document_survives_cleanup_failure(tmp_path, monkeypatch):
    """🔒 P-17 核心断言：**清理临时文件失败时，process_document 必须正常返回**。

    修复前：finally 里的裸 `os.remove` 抛出 → 异常逸出 process_document
    → 穿透 Starlette BackgroundTask → 实测终止 uvicorn 进程。
    """
    temp_file = tmp_path / "upload.pdf"
    temp_file.write_bytes(b"%PDF-1.7")

    doc = _FakeDoc()
    session = _FakeSession(doc)
    _stub_docmind(monkeypatch, {"success": True, "document_count": 27})

    def _boom(path):
        raise PermissionError(13, "file is in use by another process")

    monkeypatch.setattr(os, "remove", _boom)

    # 修复前：这一行抛 PermissionError，测试直接 error
    await kr.process_document("doc-1", str(temp_file), "demo", lambda: session)

    # 处理结果不被清理失败污染
    assert doc.status == "completed"
    assert doc.chunk_count == 27
    assert doc.error_message is None
    assert session.closed is True, "数据库会话必须在 finally 中关闭"


async def test_process_document_still_reports_processing_failure(tmp_path, monkeypatch):
    """反向对照：**处理本身**失败仍必须被记为 failed（守卫不能顺手吞掉真实错误）。"""
    temp_file = tmp_path / "upload.pdf"
    temp_file.write_bytes(b"%PDF-1.7")

    doc = _FakeDoc()
    session = _FakeSession(doc)

    def _raise(**kwargs):
        raise RuntimeError("DocMind 解析失败")

    fake = types.ModuleType("service.docmind_service")
    fake.process_document_with_docmind = _raise
    monkeypatch.setitem(sys.modules, "service.docmind_service", fake)

    await kr.process_document("doc-2", str(temp_file), "demo", lambda: session)

    assert doc.status == "failed"
    assert "DocMind 解析失败" in (doc.error_message or "")
    assert not temp_file.exists(), "处理失败后临时文件仍应被清理（清理本身没问题时）"


# --------------------------------------------------------------------------
# 3) 调度边界层
# --------------------------------------------------------------------------

async def test_boundary_wrapper_swallows_unexpected_exception(monkeypatch):
    """🔒 结构性修复：后台任务的**任意**未预期异常都不得逸出到 ASGI。

    这是最外层兜底 —— 即使将来 process_document 内部新增出未预料的异常，
    也只会留下日志，不会打死服务。
    """

    async def _explode(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(kr, "process_document", _explode)

    # 修复前（直接 add_task(process_document)）等价于把 _explode 交给 Starlette → 服务死
    await kr.run_document_processing("doc-3", "/tmp/x.pdf", "demo", lambda: _FakeSession(_FakeDoc()))


async def test_boundary_wrapper_delegates_success(monkeypatch):
    """成功路径必须原样透传（不得把「正常返回」也当成异常处理掉）。"""
    calls = []

    async def _ok(document_id, file_path, kb_name, factory):
        calls.append((document_id, file_path, kb_name))
        return "done"

    monkeypatch.setattr(kr, "process_document", _ok)

    await kr.run_document_processing("doc-4", "/tmp/y.pdf", "kb1", "FACTORY")

    assert calls == [("doc-4", "/tmp/y.pdf", "kb1")]


# --------------------------------------------------------------------------
# 4) 源码锁
# --------------------------------------------------------------------------

def _source() -> str:
    return ROUTER.read_text(encoding="utf-8")


def test_upload_route_schedules_the_boundary_wrapper():
    """🔒 兜底必须真的被挂在调度点上 —— 定义了不接线的守卫等于没有。"""
    src = _source()

    assert re.search(r"background_tasks\.add_task\(\s*run_document_processing,", src), (
        "上传路由未把 run_document_processing 交给 background_tasks"
    )
    assert not re.search(r"background_tasks\.add_task\(\s*process_document,", src), (
        "上传路由仍直接调度 process_document（异常将穿透 ASGI）"
    )


def test_the_only_os_remove_lives_inside_the_guard():
    """🔒 全文件只剩唯一一处 `os.remove(`，且必须被 try/except OSError 包住。

    这一处即守卫的唯一实现；任何新增的裸 `os.remove` 都会让本用例失败 ——
    该文件里已经出现过两处（后台 finally + 删除文档端点），两次都属于同一族缺陷。
    """
    src = _source()

    assert src.count("os.remove(") == 1, f"仍存在 {src.count('os.remove(')} 处裸 os.remove"

    helper = src.split("def _remove_file_quietly", 1)[1].split("async def process_document", 1)[0]
    assert "os.remove(" in helper, "唯一一处 os.remove 不在守卫函数内"
    assert "except OSError" in helper, "os.remove 未被 except OSError 包住"


def test_finally_delegates_cleanup_to_the_guard():
    """🔒 finally 里必须调用守卫，而不是内联删除逻辑。"""
    src = _source()
    assert "_remove_file_quietly(file_path)" in src, "finally 未委派给守卫函数"

    body = src.split("async def process_document", 1)[1].split("async def run_document_processing", 1)[0]
    assert "_remove_file_quietly(file_path)" in body, "守卫调用不在 process_document 内"


def test_delete_document_delegates_file_removal_to_the_guard():
    """🔒 删除文档端点也必须走守卫：文件删不掉不该让请求 500、更不该让记录删不掉。"""
    src = _source()
    region = src.split("async def delete_document", 1)[1]

    assert "_remove_file_quietly(doc.file_path)" in region, "delete_document 未委派给守卫"
    assert "os.remove(" not in region, "delete_document 仍有裸 os.remove"


def test_boundary_wrapper_catches_broad_exception():
    """🔒 兜底必须是 `except Exception`（窄化会漏掉不可预料的异常类型）。"""
    src = _source()
    wrapper = src.split("async def run_document_processing", 1)[1].split('@router.get(""', 1)[0]

    assert "except Exception" in wrapper, "边界兜底未捕获 Exception"
    assert "logger.exception" in wrapper, "兜底静默了 —— 必须留下可排查的日志"
