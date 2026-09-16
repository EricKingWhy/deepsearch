"""T61 / P-16：SSE 流在研究中途被关闭时，在飞的 agent 任务必须被取消。

复现依据：`.runlogs/t49_backend8001c.log`

  - 10:25:03.786 在 `service.py:227  yield self._format_sse(event)` 处被抛入
    `GeneratorExit` —— Starlette 检测到 SSE 客户端断连后关闭了响应生成器；
  - 此后 DeepScout 的 `asyncio.create_task(execute_agent())` 任务**脱管继续运行约 6 分钟**
    （日志一路跑到 10:31:45），期间每条事件都因 `_run_simplified` 的 finally 已把
    `state["_message_queue"]` 置为 None 而落到 `[SSE] No queue available`（全文 246 条），
    事件全部丢失；`search_results` 丢失最集中。

本用例不依赖任何基础设施（不起 Postgres/Redis/Milvus，也不调 LLM）：用一个替身 agent
驱动 `_run_simplified`，在流式阶段 `aclose()` 模拟断连，断言替身 agent 收到取消，
且不再产生「无队列」事件。
"""

import asyncio

import pytest

import service.deep_research_v2.agents as agents_package


for agent_name in (
    "ChiefArchitect",
    "DeepScout",
    "CodeWizard",
    "CriticMaster",
    "LeadWriter",
    "DataAnalyst",
):
    if not hasattr(agents_package, agent_name):
        setattr(agents_package, agent_name, type(agent_name, (), {}))


import service.deep_research_v2.graph as graph_module
from service.deep_research_v2.graph import DeepResearchGraph


class StreamingScout:
    """替身 agent：与 `BaseAgent.add_message` 同构地持续把事件推进实时队列。"""

    name = "DeepScout"
    role = "scout"

    def __init__(self):
        self.cancelled = False
        self.completed = False
        self.dropped_events = 0

    def add_message(self, state, event_type, content):
        message = {"type": event_type, "agent": self.name, "content": content}
        state["messages"].append(message)
        queue = state.get("_message_queue")
        if queue is not None:
            queue.put_nowait(message)
        else:
            self.dropped_events += 1

    async def process(self, state):
        try:
            for index in range(2000):
                await asyncio.sleep(0.002)
                self.add_message(state, "search_results", index)
        except asyncio.CancelledError:
            self.cancelled = True
            raise
        self.completed = True
        return state


def _researching_state():
    return {
        "query": "产业研究",
        "session_id": "session-1",
        "phase": "researching",
        "iteration": 0,
        "max_iterations": 1,
        "messages": [],
        "facts": [],
        "references": [],
        "charts": [],
        "knowledge_graph": {"nodes": [], "edges": []},
        "final_report": "",
    }


def _graph_with_scout(scout, monkeypatch):
    graph = object.__new__(DeepResearchGraph)
    for attribute in (
        "architect",
        "scout",
        "data_analyst",
        "wizard",
        "critic",
        "writer",
    ):
        setattr(graph, attribute, scout)
    graph.checkpoint_service = None
    monkeypatch.setattr(graph_module, "clear_cancel_flag", lambda _session_id: None)
    monkeypatch.setattr(
        graph_module, "is_research_cancelled", lambda _session_id: False
    )
    return graph


@pytest.mark.asyncio
async def test_closing_stream_cancels_inflight_agent(monkeypatch):
    scout = StreamingScout()
    graph = _graph_with_scout(scout, monkeypatch)
    state = _researching_state()

    stream = graph._run_simplified(state)
    received = 0
    async for event in stream:
        if event.get("type") == "search_results":
            received += 1
            if received >= 2:
                break
    assert received >= 2, "预期在 agent 流式阶段收到事件"

    await stream.aclose()  # 模拟 SSE 客户端断连
    await asyncio.sleep(0.05)  # 给取消/脱管任务留出推进窗口

    cancelled = scout.cancelled
    completed = scout.completed
    dropped = scout.dropped_events
    assert (cancelled, completed, dropped) == (True, False, 0), (
        f"流被关闭后：cancelled={cancelled}（应 True，否则任务脱管）、"
        f"completed={completed}（应 False）、"
        f"dropped_events={dropped}（应 0；非 0 即 P-16 观测到的大量 "
        "`[SSE] No queue available`）"
    )
