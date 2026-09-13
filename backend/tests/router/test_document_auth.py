"""T04 回归测试：document_router 的所有端点都必须要求认证。

背景（事实 F-03）：该路由原先**全文件没有任何鉴权依赖**，任何未登录请求都能调用文档上传、
列表、删除与检索接口。本票在 router 级挂了一次 `get_current_user_required`。

验收优先取**真实请求**（`TestClient`）：对 4 个端点各发一次不带 Token 的请求，断言一律 401。
另补两条结构性断言，锁定「依赖挂在 router 级」这一实现选择 —— 逐端点挂容易在新增端点时漏加。
"""

import pathlib

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from router import document_router
from router.auth_router import get_current_user_required

# 注意：不能把 APIRouter 直接交给 TestClient —— FastAPI 0.141 的请求作用域要求
# `fastapi_middleware_astack` 存在，而该键只有经过 `FastAPI` 应用的中间件栈才会注入
# （直接挂 router 会报 `AssertionError: fastapi_middleware_astack not found`）。
# 这里用一个最小 `FastAPI` 应用只挂载被测 router，既能触发该栈，又不引入 DB / Redis 等重依赖。
_app = FastAPI()
_app.include_router(document_router.router)
client = TestClient(_app)

# body 一律填合法值，确保唯一的拦截原因是「没有 Token」而不是参数校验失败
UNAUTHENTICATED_CALLS = [
    (
        "post",
        "/documents/upload",
        {"files": {"file": ("政策文件.pdf", b"%PDF-1.4 test", "application/pdf")}},
    ),
    ("get", "/documents/list", {}),
    ("post", "/documents/delete", {"json": {"document_ids": []}}),
    ("post", "/documents/retrieve", {"json": {"question": "测试问题"}}),
]


# 鉴权依赖抛出的固定文案（`router/auth_router.py` 的 credentials_exception）。
# 断言它可确保 401 来自「鉴权未通过」，而不是恰好某个环节也返回 401。
CREDENTIALS_DETAIL = "无法验证凭据"


@pytest.mark.parametrize("method,path,kwargs", UNAUTHENTICATED_CALLS)
def test_endpoint_without_token_returns_401(method, path, kwargs):
    """未带 Token → 401，不得放行。"""
    response = getattr(client, method)(path, **kwargs)

    assert response.status_code == 401, (
        f"{method.upper()} {path} 未带 Token 时返回 {response.status_code}，应为 401"
    )
    assert response.json()["detail"] == CREDENTIALS_DETAIL


@pytest.mark.parametrize("method,path,kwargs", UNAUTHENTICATED_CALLS)
def test_endpoint_with_invalid_token_returns_401(method, path, kwargs):
    """伪造 / 损坏的 Token 同样必须被拒。"""
    response = getattr(client, method)(
        path, headers={"Authorization": "Bearer not-a-real-token"}, **kwargs
    )

    assert response.status_code == 401
    assert response.json()["detail"] == CREDENTIALS_DETAIL


def test_auth_dependency_is_mounted_at_router_level():
    """锁定实现选择：依赖挂在 router 级，新增端点自动受保护。"""
    source = pathlib.Path(document_router.__file__).read_text(encoding="utf-8")

    assert "dependencies=[Depends(get_current_user_required)]" in source


def test_every_route_is_covered_by_the_router_dependency():
    """路由级依赖必须覆盖该 router 下的全部端点（当前 4 个）。"""
    routes = list(document_router.router.routes)

    assert len(routes) == 4, (
        f"端点数量变为 {len(routes)}；新增端点请确认是否也应鉴权，并更新本断言"
    )

    for route in routes:
        calls = [dep.call for dep in route.dependant.dependencies]
        assert get_current_user_required in calls, f"{route.path} 未被鉴权依赖覆盖"
