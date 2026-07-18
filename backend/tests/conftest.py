import os
import sys
import types
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP_DIR))
os.environ.setdefault("ENV", "test")


def _register_namespace_package(name: str, path: Path) -> None:
    package = types.ModuleType(name)
    package.__path__ = [str(path)]
    sys.modules.setdefault(name, package)


_register_namespace_package("service", APP_DIR / "service")
_register_namespace_package("core", APP_DIR / "core")
_register_namespace_package("models", APP_DIR / "models")
_register_namespace_package(
    "service.deep_research_v2",
    APP_DIR / "service" / "deep_research_v2",
)
_register_namespace_package(
    "service.deep_research_v2.agents",
    APP_DIR / "service" / "deep_research_v2" / "agents",
)
