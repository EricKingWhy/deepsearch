import importlib
import os
import sys
import types
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP_DIR))
os.environ.setdefault("ENV", "test")

# 自 T02 起 core.security 在**导入期**校验 JWT_SECRET_KEY，而 core/__init__.py 会导入 security，
# 于是任何 `import core.<anything>`（含与鉴权无关的模块）都要求该变量存在。
# 这里给测试环境一个固定占位值；T02 自身的用例会用 monkeypatch 先清掉它，再断言「缺失即失败」。
os.environ.setdefault(
    "JWT_SECRET_KEY", "test-only-jwt-secret-key-do-not-use-in-production-0123456789"
)


def _register_namespace_package(name: str, path: Path) -> types.ModuleType:
    package = types.ModuleType(name)
    package.__path__ = [str(path)]
    sys.modules.setdefault(name, package)
    return sys.modules[name]


_register_namespace_package("service", APP_DIR / "service")
_register_namespace_package("core", APP_DIR / "core")
_register_namespace_package("models", APP_DIR / "models")
_register_namespace_package("router", APP_DIR / "router")
_register_namespace_package(
    "service.deep_research_v2",
    APP_DIR / "service" / "deep_research_v2",
)
_register_namespace_package(
    "service.deep_research_v2.agents",
    APP_DIR / "service" / "deep_research_v2" / "agents",
)


# --- 让占位包能顶替真实的 `service` 包 ------------------------------------------
# 上面的占位包**故意不执行** `service/__init__.py`（它会连带拉起 langchain / langgraph /
# dashscope 等重型依赖，实测单次导入 >35s）。但这带来一个副作用：
# `router/document_router.py` 等模块用 `from service import DocumentService, ServiceConfig`
# 取**顶层名字**，而占位包里没有这些名字，于是 router 测试在收集阶段直接 ImportError。
#
# 修法：把 router 实际用到的顶层名字，从对应的**轻量子模块**取出来挂到占位包上。
# 代价接近 0（config / web_search_service / session_service 约 0s，document_service 约 1s、
# chat_service 约 1.7s），且不再要求测试拉起整条重型链。
# 若后续 router 用到更多顶层名字，在此按同一方式追加即可。
_service = sys.modules["service"]

# 顶层名字 → 定义它的轻量子模块（对应 `service/__init__.py` 里的 `from .X import Y`）。
_SERVICE_PUBLIC_NAMES = {
    "config": ("ServiceConfig",),
    "document_service": ("DocumentService",),
    "web_search_service": ("WebSearchService",),
    "chat_service": ("ChatService",),
    "session_service": ("SessionService",),
}

for _submodule, _exported_names in _SERVICE_PUBLIC_NAMES.items():
    _module = importlib.import_module(f"service.{_submodule}")
    for _exported_name in _exported_names:
        setattr(_service, _exported_name, getattr(_module, _exported_name))


# --- 重型协作者替身 -------------------------------------------------------------
# `router/document_router.py` 在**模块级**导入 `service.docmind_service`，而该模块实测
# 导入耗时约 48s（拉起 docmind / llama-index 重依赖）。鉴权与路由装配类测试不会真正执行
# 文档解析，因此这里注入轻量替身，把验收压到秒级。
# 替身故意抛 NotImplementedError（而不是伪造成功），以便任何真实的解析调用立刻暴露，
# 而不是被静默吞掉当成「测试通过」。
# ⚠️ 将来若有测试需要真实的 docmind 行为，请在该测试内先 `del sys.modules[...]` 再导入。
if "service.docmind_service" not in sys.modules:
    _docmind_stub = types.ModuleType("service.docmind_service")

    def process_document_with_docmind(*args, **kwargs):
        raise NotImplementedError(
            "tests/conftest.py 注入了 service.docmind_service 替身；"
            "本测试不应真正执行文档解析。如需真实行为请先移除该替身。"
        )

    _docmind_stub.process_document_with_docmind = process_document_with_docmind
    sys.modules["service.docmind_service"] = _docmind_stub
    _service.docmind_service = _docmind_stub
