"""T55 回归：聊天附件路由的**归属校验**（越权读写删他人会话附件）。

背景：`attachment_router.py` 在 §4 总门禁第一轮只补了一半 ——
把 `get_current_user`（可选认证）换成 router 级 `get_current_user_required`，
堵住了**匿名**访问；但读 / 删四个端点仍只校验资源**存在**、不校验**归属**。
`upload_attachment` 写入时记了 `user_id`（:161）却从不在读 / 删时回看，
属「写时记、读时不查」的半修复。后果是任何已登录用户凭一个 UUID 即可
读取他人会话的附件清单与详情、删除他人附件及其落盘文件、乃至把附件
塞进他人会话（IDOR）。终审 §4 复检（标准轴 N1）发现，立项 T55。

本文件**不依赖任何基础设施**（Postgres / Redis / Milvus）：

- 用 `_FakeDB` 顶替 `get_db`，其查询引擎**真的执行** WHERE 约束，
  并且**只认 `chat_sessions.user_id` 这一列**才能解析归属 —— 于是
  「去掉归属过滤」会真的导致非本人也能查到行（= 修复前的漏洞行为），
  从而让下面的 404 断言失败。这是本文件具备判别力的关键，
  而不是「断言某个滤条件字符串存在」那种恒真写法。
- 用户身份用 `dependency_overrides` 注入，不签发真 JWT。
"""
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.sql.elements import BinaryExpression, BindParameter
from sqlalchemy.sql.schema import Column

# 注册 `User` 的关系目标（`User.knowledge_bases -> KnowledgeBase` 等）。conftest 为提速把
# `models` 注册成**命名空间占位包**（不执行 `models/__init__.py`），所以必须显式导入子模块；
# 否则上传路径构造 `ChatAttachment(...)` 触发 mapper 配置时会因解析不到 `KnowledgeBase`
# 抛 `InvalidRequestError`。
from models import chat as _chat_models  # noqa: F401
from models import knowledge as _knowledge_models  # noqa: F401
from core.database import get_db
from models.chat import ChatAttachment, ChatSession
from router import attachment_router as ar
from router.auth_router import get_current_user_required

OWNER_ID = uuid4()
INTRUDER_ID = uuid4()
OWNER_SESSION_ID = uuid4()
INTRUDER_SESSION_ID = uuid4()
OWNER_ATTACHMENT_ID = uuid4()


class _Row:
    """最小行对象：只提供属性访问（不碰 SQLAlchemy 元类）。"""

    def __init__(self, **fields):
        self.__dict__.update(fields)


def _attachment(**overrides):
    base = dict(
        id=OWNER_ATTACHMENT_ID,
        session_id=OWNER_SESSION_ID,
        message_id=None,
        filename="note.txt",
        file_type="txt",
        file_size=12,
        file_path=None,
        status="completed",
        error_message=None,
        created_at=datetime(2026, 9, 16, 12, 0, 0),
    )
    base.update(overrides)
    return _Row(**base)


class _Query:
    """极简查询对象：支持 `.join/.filter/.order_by/.first/.all`。

    `_matches` 是判别力的来源 —— 它会**真的解析** `Column == 值` 形态的条件：
    - `chat_sessions.user_id == <uid>` 会拿行所属会话的 user_id 去比；
    - 条件里**没有**该列时，行永远通过（复现修复前「裸查」的行为）。
    """

    def __init__(self, db, model):
        self._db = db
        self._model = model
        self._criteria = []
        self._joined_session = False

    def join(self, *_args, **_kwargs):
        self._joined_session = True
        return self

    def filter(self, *criteria):
        self._criteria.extend(criteria)
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    # --- 求值 ---

    def _owner_of(self, row):
        for session in self._db.sessions:
            if getattr(session, "id", None) == getattr(row, "session_id", None):
                return session.user_id
        return None

    def _matches(self, row):
        for criterion in self._criteria:
            if not isinstance(criterion, BinaryExpression):
                continue
            left, right = criterion.left, criterion.right
            if not isinstance(left, Column):
                continue
            value = right.value if isinstance(right, BindParameter) else getattr(right, "value", right)
            table = left.table.name
            value = right.value if isinstance(right, BindParameter) else getattr(right, "value", right)
            if table == "chat_sessions" and left.key == "user_id":
                # 归属约束：查会话时直接比 `row.user_id`；
                # 查附件（join 过 sessions）时比「行所属会话的 user_id」。
                actual = (
                    getattr(row, "user_id", None)
                    if self._model is ChatSession
                    else self._owner_of(row)
                )
                if actual != value:
                    return False
            elif getattr(row, left.key, None) != value:
                return False
        return True

    def _rows(self):
        source = self._db.sessions if self._model is ChatSession else self._db.attachments
        return [row for row in source if self._matches(row)]

    def first(self):
        rows = self._rows()
        return rows[0] if rows else None

    def all(self):
        return list(self._rows())


class _FakeDB:
    def __init__(self, sessions=(), attachments=()):
        self.sessions = list(sessions)
        self.attachments = list(attachments)
        self.deleted = []
        self.added = []
        self.commits = 0

    def query(self, model):
        return _Query(self, model)

    def add(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = uuid4()
        if getattr(obj, "created_at", None) is None:
            obj.created_at = datetime(2026, 9, 16, 12, 0, 0)
        self.added.append(obj)
        if isinstance(obj, ChatAttachment):
            self.attachments.append(obj)

    def delete(self, obj):
        self.deleted.append(obj)

    def commit(self):
        self.commits += 1

    def refresh(self, _obj):
        return None

    def close(self):
        return None


def _make_db():
    """构造数据：OWNER 的会话 + 一条附件，另有 INTRUDER 的会话。"""
    sessions = [
        _Row(id=OWNER_SESSION_ID, user_id=OWNER_ID, title="owner session"),
        _Row(id=INTRUDER_SESSION_ID, user_id=INTRUDER_ID, title="intruder session"),
    ]
    attachments = [_attachment()]
    return _FakeDB(sessions=sessions, attachments=attachments)


def _client(db, user_id) -> TestClient:
    app = FastAPI()
    app.include_router(ar.router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user_required] = lambda: _Row(id=user_id)
    return TestClient(app)


# --------------------------------------------------------------------------
# 1) GET /attachments/{id}
# --------------------------------------------------------------------------


def test_owner_can_read_own_attachment():
    db = _make_db()
    response = _client(db, OWNER_ID).get(f"/attachments/{OWNER_ATTACHMENT_ID}")

    assert response.status_code == 200
    assert response.json()["id"] == str(OWNER_ATTACHMENT_ID)


def test_intruder_reading_attachment_gets_404():
    """核心断言：已登录的**他人**不得凭 UUID 读到附件。"""
    db = _make_db()
    response = _client(db, INTRUDER_ID).get(f"/attachments/{OWNER_ATTACHMENT_ID}")

    assert response.status_code == 404, (
        "非本人读取他人附件未被拦截 —— 归属校验缺失（T55 / 终审 §4 N1）"
    )


def test_unknown_attachment_gets_404():
    db = _make_db()
    response = _client(db, OWNER_ID).get(f"/attachments/{uuid4()}")

    assert response.status_code == 404


# --------------------------------------------------------------------------
# 2) GET /attachments/session/{session_id}
# --------------------------------------------------------------------------


def test_owner_can_list_own_session_attachments():
    db = _make_db()
    response = _client(db, OWNER_ID).get(f"/attachments/session/{OWNER_SESSION_ID}")

    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_intruder_listing_others_session_gets_404():
    db = _make_db()
    response = _client(db, INTRUDER_ID).get(f"/attachments/session/{OWNER_SESSION_ID}")

    assert response.status_code == 404, (
        "非本人列出他人会话的附件清单未被拦截（T55 / 终审 §4 N1）"
    )


# --------------------------------------------------------------------------
# 3) DELETE /attachments/{id}
# --------------------------------------------------------------------------


def test_intruder_deleting_attachment_gets_404_and_leaves_evidence(tmp_path):
    """越权删除必须 404，且**记录与落盘文件都不能被删**。"""
    victim_file = tmp_path / "victim.txt"
    victim_file.write_text("secret", encoding="utf-8")

    db = _make_db()
    db.attachments[0].file_path = str(victim_file)

    response = _client(db, INTRUDER_ID).delete(f"/attachments/{OWNER_ATTACHMENT_ID}")

    assert response.status_code == 404, "非本人删除他人附件未被拦截（T55 / 终审 §4 N1）"
    assert db.deleted == [], "越权删除把记录删掉了"
    assert victim_file.exists(), "越权删除把落盘文件删掉了"


def test_owner_deleting_own_attachment_removes_record_and_file(tmp_path):
    victim_file = tmp_path / "mine.txt"
    victim_file.write_text("mine", encoding="utf-8")

    db = _make_db()
    db.attachments[0].file_path = str(victim_file)

    response = _client(db, OWNER_ID).delete(f"/attachments/{OWNER_ATTACHMENT_ID}")

    assert response.status_code == 204
    assert len(db.deleted) == 1
    assert not victim_file.exists()


# --------------------------------------------------------------------------
# 4) POST /attachments（上传目标会话也必须属于本人）
# --------------------------------------------------------------------------


def _stub_upload(monkeypatch, tmp_path):
    stored = tmp_path / "stored.txt"
    stored.write_text("payload", encoding="utf-8")

    async def _fake_save_upload(*_args, **_kwargs):
        return str(stored)

    monkeypatch.setattr(ar, "save_upload", _fake_save_upload)
    # 后台处理不参与本票断言，且会去连真库，故置空
    monkeypatch.setattr(ar, "process_attachment", lambda *_a, **_k: None)
    return stored


def test_upload_into_others_session_gets_404(monkeypatch, tmp_path):
    _stub_upload(monkeypatch, tmp_path)
    db = _make_db()

    response = _client(db, INTRUDER_ID).post(
        "/attachments",
        files={"file": ("note.txt", b"hi", "text/plain")},
        data={"session_id": str(OWNER_SESSION_ID)},
    )

    assert response.status_code == 404, "非本人可把附件塞进他人会话（T55 / 终审 §4 N1）"
    assert db.added == []


def test_upload_into_own_session_succeeds(monkeypatch, tmp_path):
    _stub_upload(monkeypatch, tmp_path)
    db = _make_db()

    response = _client(db, OWNER_ID).post(
        "/attachments",
        files={"file": ("note.txt", b"hi", "text/plain")},
        data={"session_id": str(OWNER_SESSION_ID)},
    )

    assert response.status_code == 201
    assert len(db.added) == 1
    assert db.added[0].user_id == OWNER_ID


# --------------------------------------------------------------------------
# 5) 源码锁：防未来回退
# --------------------------------------------------------------------------

_SOURCE = Path(ar.__file__).read_text(encoding="utf-8")


def _function_body(name: str, next_name=None) -> str:
    """截取 `async def <name>` 到 `async def <next_name>` 之间的片段；`next_name=None` 取到文件末。

    缺锚点即刻断言失败（而不是抛 IndexError），否则锚点被改掉时锁会静默失效。
    """
    assert f"async def {name}" in _SOURCE, f"源码里找不到 async def {name}"
    body = _SOURCE.split(f"async def {name}", 1)[1]
    if next_name is None:
        return body
    assert f"async def {next_name}" in body, f"源码里找不到 async def {next_name}"
    return body.split(f"async def {next_name}", 1)[0]


@pytest.mark.parametrize(
    "name,next_name",
    [
        ("upload_attachment", "get_attachment"),
        ("get_attachment", "get_session_attachments"),
        ("get_session_attachments", "delete_attachment"),
        ("delete_attachment", None),
    ],
)
def test_each_endpoint_filters_by_session_ownership(name, next_name):
    """四个入口都必须按 `chat_sessions.user_id` 过滤 —— 少一处就是一个越权口子。"""
    body = _function_body(name, next_name)

    assert "ChatSession.user_id == current_user.id" in body, (
        f"{name} 未按会话归属过滤；去掉它会把该端点退回「任何登录用户凭 UUID 即可跨用户操作」"
    )


def test_no_bare_attachment_lookup_remains():
    """防回退：不允许再出现「只按 id 查附件、不带归属」的裸查询形态。"""
    bare = "db.query(ChatAttachment).filter(ChatAttachment.id == att_uuid).first()"

    assert bare not in _SOURCE, "附件查询又回到了不带归属过滤的裸查形态"


def test_read_delete_endpoints_declare_current_user():
    """三个读 / 删端点必须显式拿到 current_user（只有拿到它才谈得上校验归属）。"""
    for name, next_name in (
        ("get_attachment", "get_session_attachments"),
        ("get_session_attachments", "delete_attachment"),
        ("delete_attachment", None),
    ):
        body = _function_body(name, next_name)
        assert "current_user: User = Depends(get_current_user_required)" in body, (
            f"{name} 未声明 current_user 依赖"
        )
