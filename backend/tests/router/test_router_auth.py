"""T05 回归测试：chat / search / news 三个路由的所有端点都必须要求认证。

背景（事实 F-04）：`chat_router.py`、`search_router.py`、`news_router.py` 三个路由原先
**没有任何鉴权依赖**，与 `research_router` 的鉴权现状不一致。本票按 T04 的同一模式
（router 级 `dependencies=[...]`）补齐，保持四个路由写法一致。

「是否需要保留匿名端点」的判定依据（已实测，见 `tickets.md` T05）：
前端**没有任何匿名调用方** —— 除 `/login` 与 `/404` 外，所有页面都包在 `AuthGuard` 里
（`frontend/src/router/routes.tsx`），未登录即重定向到 `/login`；`/search/web` 甚至
在 `frontend/src` 中命中 0 处调用。因此不存在「公开落地页依赖匿名检索」的场景。

验收优先取**真实请求**：对 13 个端点各发一次不带 Token 的请求，断言一律 401，
且 detail 为鉴权依赖的固定文案 —— 以确保 401 来自鉴权，而不是恰好某个环节也返回 401。
"""

import importlib
import pathlib

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from router.auth_router import get_current_user_required

ROUTER_MODULES = ("chat_router", "search_router", "news_router")

# 端点数量下限护栏：新增端点时本断言失败，提醒确认新端点是否也应鉴权。
EXPECTED_ENDPOINT_COUNTS = {
    "chat_router": 4,
    "search_router": 1,
    "news_router": 8,
}

# 鉴权依赖抛出的固定文案（`router/auth_router.py` 的 credentials_exception）。
CREDENTIALS_DETAIL = "无法验证凭据"

_MODULES = {name: importlib.import_module(f"router.{name}") for name in ROUTER_MODULES}


def _iter_endpoints(module_name):
    """产出 (HTTP 方法, 路径)，忽略自动生成的 HEAD / OPTIONS。"""
    for route in _MODULES[module_name].router.routes:
        for method in sorted(route.methods - {"HEAD", "OPTIONS"}):
            yield method, route.path


def _client(module_name):
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
def test_endpoint_without_token_returns_401(module_name, method, path):
    """未带 Token → 401，不得放行。"""
    response = _client(module_name).request(method, path, json={} if method == "POST" else None)

    assert response.status_code == 401, (
        f"{method} {path}（{module_name}）未带 Token 时返回 {response.status_code}，应为 401"
    )
    assert response.json()["detail"] == CREDENTIALS_DETAIL


@pytest.mark.parametrize("module_name,method,path", ALL_ENDPOINTS)
def test_endpoint_with_invalid_token_returns_401(module_name, method, path):
    """伪造 / 损坏的 Token 同样必须被拒。"""
    response = _client(module_name).request(
        method,
        path,
        headers={"Authorization": "Bearer not-a-real-token"},
        json={} if method == "POST" else None,
    )

    assert response.status_code == 401
    assert response.json()["detail"] == CREDENTIALS_DETAIL


@pytest.mark.parametrize("module_name", ROUTER_MODULES)
def test_auth_dependency_is_mounted_at_router_level(module_name):
    """锁定实现选择：依赖挂在 router 级，新增端点自动受保护（与 T04 写法一致）。"""
    source = pathlib.Path(_MODULES[module_name].__file__).read_text(encoding="utf-8")

    assert "dependencies=[Depends(get_current_user_required)]" in source


@pytest.mark.parametrize("module_name", ROUTER_MODULES)
def test_every_route_is_covered_by_the_router_dependency(module_name):
    """路由级依赖必须覆盖该 router 下的全部端点。"""
    routes = list(_MODULES[module_name].router.routes)

    assert routes, f"{module_name} 没有任何端点，断言失去意义"

    for route in routes:
        calls = [dep.call for dep in route.dependant.dependencies]
        assert get_current_user_required in calls, f"{route.path}（{module_name}）未被鉴权依赖覆盖"


@pytest.mark.parametrize("module_name,expected", sorted(EXPECTED_ENDPOINT_COUNTS.items()))
def test_endpoint_count_is_expected(module_name, expected):
    """端点数量护栏：数量变化时提醒复核是否所有端点都应鉴权，并同步更新本断言。"""
    actual = len(_MODULES[module_name].router.routes)

    assert actual == expected, (
        f"{module_name} 端点数量由 {expected} 变为 {actual}；"
        "请确认新增/删除的端点是否也应鉴权，并更新 EXPECTED_ENDPOINT_COUNTS"
    )
