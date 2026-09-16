"""跨 Context 退出上下文管理器时不得抛 ValueError（T62；SSE 断连 teardown 族）。

背景：SSE 客户端断连时 Starlette 会关闭响应生成器，`GeneratorExit` 展开经过
`service.py` 的 `with bind_context(...), bind_run_usage()`。这些上下文管理器的 token 是在
**另一个** Context 里 `set` 的，于是 `__exit__` 里的 `ContextVar.reset(token)` 抛
`ValueError: … was created in a different Context`，把干净的关闭路径掩盖成 context 错误。

归档证据 `.runlogs/t49_backend8001c.log`：
  - `10:25:03.786` `opentelemetry.context | ERROR | Failed to detach context`
    （堆栈：`observability/events.py:126` → `service.py:227 yield …` → `GeneratorExit`）
  - `10:25:03.838` `asyncio | ERROR | Task exception was never retrieved`（同一 ValueError）

不依赖任何基础设施。
"""

from __future__ import annotations

import asyncio
from contextvars import copy_context

import pytest

from observability.context import bind_context, current_context
from observability.events import bind_event_recorder, bind_run_usage


def _managers():
    """每个用例用**新建**的上下文管理器，避免复用已被 enter 的实例。"""
    return [
        pytest.param(lambda: bind_context(request_id="req-teardown"), id="bind_context"),
        pytest.param(bind_run_usage, id="bind_run_usage"),
        pytest.param(
            lambda: bind_event_recorder(lambda **_kwargs: None),
            id="bind_event_recorder",
        ),
    ]


@pytest.mark.parametrize("manager_factory", _managers())
def test_exit_from_another_context_does_not_raise(manager_factory):
    manager = manager_factory()
    other = copy_context()
    other.run(manager.__enter__)  # token 在【另一个 Context】里创建

    # 在本 Context 退出：修复前抛 ValueError("… created in a different Context")
    manager.__exit__(None, None, None)


def test_exit_in_the_same_context_still_restores_the_previous_value():
    """回归：同 Context 下必须照常复原，守卫不能把正常路径也吞掉。"""

    assert current_context() is None
    with bind_context(request_id="req-normal"):
        inner = current_context()
        assert inner is not None and inner.request_id == "req-normal"
    assert current_context() is None


@pytest.mark.asyncio
async def test_async_generator_closed_from_another_task_does_not_raise():
    """复现生产机制：生成器在一个任务里推进，被另一个任务 `aclose()`。"""

    seen = []

    async def stream():
        with bind_context(request_id="req-stream"), bind_run_usage():
            seen.append(current_context().request_id)
            yield "chunk"
            seen.append("resumed-after-yield")

    stream_gen = stream()
    assert await stream_gen.__anext__() == "chunk"
    assert seen == ["req-stream"]

    async def teardown():
        # 新任务 → 复制出的另一个 Context，等价于 Starlette 的断连 teardown
        await stream_gen.aclose()

    await asyncio.create_task(teardown())

    assert seen == ["req-stream"], "GeneratorExit 关闭时不应再推进生成器"
