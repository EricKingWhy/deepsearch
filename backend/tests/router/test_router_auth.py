"""回归测试：document / chat / search / news 四个路由的所有端点都必须要求认证。

背景：事实 F-03 —— `document_router.py` 与 `chat_router.py` / `search_router.py` /
`news_router.py` 原先都**没有任何鉴权依赖**，未登录即可上传与检索文档、创建会话、
发起补全、消耗第三方搜索配额，甚至触发资讯采集。T04 修了前者，T05 修了后三者。

本文件是这四个路由的**唯一**鉴权回归测试（T04 原有的 `test_document_auth.py` 已在
第 2 批审查中并入此处，避免同一套断言维护两份）。

「是否需要保留匿名端点」的判定依据（已实测，见 `tickets.md` T05）：
前端**没有任何匿名调用方** —— `frontend/src/router/routes.tsx` 里除 `/login` 外，
所有页面（含 `/404`）都在 `AuthGuard` 子树内，未登录即重定向到 `/login`；
`/search/web` 在 `frontend/src` 中命中 0 处。因此不存在「公开落地页依赖匿名检索」的场景。

验收优先取**真实请求**：对 17 个端点各发一次不带 Token 的请求，断言一律 401，
且 detail 为鉴权依赖的固定文案 —— 以确保 401 来自鉴权，而不是恰好某个环节也返回 401。
"""

import importlib
import types
from typing import Dict, Iterable, Tuple

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from router.auth_router import get_current_user_required

ROUTER_MODULES = ("document_router", "chat_router", "search_router", "news_router")

# 端点数量护栏：新增端点时本断言失败，提醒确认新端点是否也应鉴权。
EXPECTED_ENDPOINT_COUNTS = {
    "document_router": 4,
    "chat_router": 4,
    "search_router": 1,
    "news_router": 8,
}

# 鉴权依赖抛出的固定文案（`router/auth_router.py` 的 credentials_exception）。
CREDENTIALS_DETAIL = "无法验证凭据"

_MODULES = {name: importlib.import_module(f"router.{name}") for name in ROUTER_MODULES}


def _iter_endpoints(module_name: str) -> Iterable[Tuple[str, str]]:
    """产出 (HTTP 方法, 路径)，忽略自动生成的 HEAD / OPTIONS。"""
    for route in _MODULES[module_name].router.routes:
        for method in sorted(route.methods - {"HEAD", "OPTIONS"}):
            yield method, route.path


def _request_kwargs(method: str, path: str) -> Dict[str, object]:
    """构造请求体。

    POST 端点给一个**形态正确的最小请求体**（文档上传用 multipart，其余用空 JSON），
    这样「唯一的拦截原因是没带 Token」而不是参数形态不对。
    依赖解析先于请求体校验，所以即便空 JSON 也能拿到 401；这里仍按真实形态发送，
    避免测试与真实调用方式脱节。
    """
    if method != "POST":
        return {}
    if path.endswith("/upload"):
        return {"files": {"file": ("测试文件.pdf", b"%PDF-1.4 test", "application/pdf")}}
    return {"json": {}}


def _client(module_name: str) -> TestClient:
    # 注意：FastAPI 0.141 下不能把 APIRouter 直接交给 TestClient
    # （会报 `AssertionError: fastapi_middleware_astack not found`），需经最小 FastAPI 应用挂载。
    app = FastAPI()
    app.include_router(_MODULES[module_name].router)
    return TestClient(app)


ALL_ENDPOINTS = [
    pytest.param(module_name, method, path, id=f"{module_name}-{method}-{path}")
    for module_name in ROUTER_MODULES
    for method, path in _iter_endpoints(module_name)
]


@pytest.mark.parametrize("module_name,method,path", ALL_ENDPOINTS)
def test_endpoint_without_token_returns_401(module_name: str, method: str, path: str) -> None:
    """未带 Token → 401，不得放行。"""
    response = _client(module_name).request(method, path, **_request_kwargs(method, path))

    assert response.status_code == 401, (
        f"{method} {path}（{module_name}）未带 Token 时返回 {response.status_code}，应为 401"
    )
    assert response.json()["detail"] == CREDENTIALS_DETAIL


@pytest.mark.parametrize("module_name,method,path", ALL_ENDPOINTS)
def test_endpoint_with_invalid_token_returns_401(module_name: str, method: str, path: str) -> None:
    """伪造 / 损坏的 Token 同样必须被拒。"""
    response = _client(module_name).request(
        method,
        path,
        headers={"Authorization": "Bearer not-a-real-token"},
        **_request_kwargs(method, path),
    )

    assert response.status_code == 401
    assert response.json()["detail"] == CREDENTIALS_DETAIL


@pytest.mark.parametrize("module_name", ROUTER_MODULES)
def test_auth_dependency_is_mounted_at_router_level(module_name: str) -> None:
    """锁定实现选择：依赖挂在 **router 级**，新增端点自动受保护。

    直接读 `APIRouter.dependencies`（结构化对象），而不是在源码里做字符串匹配 ——
    后者会被格式化（换行 / 尾逗号）轻易打翻，且与 `route.dependant.dependencies`
    的真实依赖图不一致。

    注意两种容器的形状不同：`APIRouter.dependencies` 装的是 `Depends`（取 `.dependency`），
    而 `route.dependant.dependencies` 装的是 `Dependant`（取 `.call`）。
    """
    mounted = [dependency.dependency for dependency in _MODULES[module_name].router.dependencies]

    assert any(
        call is get_current_user_required for call in mounted
    ), f"{module_name} 未在 router 级挂载鉴权依赖；改为逐端点挂载会让新增端点漏加鉴权"


@pytest.mark.parametrize("module_name", ROUTER_MODULES)
def test_every_route_is_covered_by_the_router_dependency(module_name: str) -> None:
    """路由级依赖必须覆盖该 router 下的全部端点。"""
    routes: list = list(_MODULES[module_name].router.routes)

    assert routes, f"{module_name} 没有任何端点，断言失去意义"

    for route in routes:
        calls = [dependency.call for dependency in route.dependant.dependencies]
        assert get_current_user_required in calls, f"{route.path}（{module_name}）未被鉴权依赖覆盖"


@pytest.mark.parametrize("module_name,expected", sorted(EXPECTED_ENDPOINT_COUNTS.items()))
def test_endpoint_count_is_expected(module_name: str, expected: int) -> None:
    """端点数量护栏：数量变化时提醒复核是否所有端点都应鉴权，并同步更新本断言。"""
    actual = len(_MODULES[module_name].router.routes)

    assert actual == expected, (
        f"{module_name} 端点数量由 {expected} 变为 {actual}；"
        "请确认新增/删除的端点是否也应鉴权，并更新 EXPECTED_ENDPOINT_COUNTS"
    )


def test_all_four_routers_are_covered() -> None:
    """四个路由一个都不能漏 —— 本文件的参数表就是「已鉴权路由」的清单。"""
    assert set(ROUTER_MODULES) == set(EXPECTED_ENDPOINT_COUNTS)
    assert isinstance(_MODULES["document_router"], types.ModuleType)
