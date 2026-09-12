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


def _register_namespace_package(name: str, path: Path) -> None:
    package = types.ModuleType(name)
    package.__path__ = [str(path)]
    sys.modules.setdefault(name, package)


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
