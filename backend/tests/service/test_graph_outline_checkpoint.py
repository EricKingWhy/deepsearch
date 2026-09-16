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


class FakeArchitect:
    name = "ChiefArchitect"

    async def process(self, state):
        state.update(
            {
                "phase": "awaiting_outline_approval",
                "outline_revision": "revision-1",
                "outline": [
                    {
                        "id": f"section-{index}",
                        "title": f"章节 {index}",
                        "description": f"描述 {index}",
                        "section_type": "mixed",
                        "requires_data": False,
                        "requires_chart": False,
                    }
                    for index in range(1, 4)
                ],
                "research_questions": [
                    {"id": f"question-{index}", "text": f"问题 {index}"}
                    for index in range(1, 4)
                ],
            }
        )
        return state


class FailingCheckpointService:
    def save_checkpoint(self, **_kwargs):
        return None


class CompletingCritic:
    name = "CriticMaster"

    async def process(self, state):
        state["phase"] = "completed"
        state["final_report"] = "final revised report"
        return state


class RecordingCheckpointService:
    def __init__(self):
        self.saved = []
        self.status_updates = []

    def save_checkpoint(self, **kwargs):
        self.saved.append(kwargs)
        return "checkpoint-1"

    def update_status(self, *args, **kwargs):
        self.status_updates.append((args, kwargs))
        return True


_AGENT_ROLES = ("architect", "scout", "data_analyst", "wizard", "critic", "writer")


def _graph(agent, checkpoint_service):
    """走真实构造器：六个角色全部注入同一个替身（该阶段用不到的不会被访问）。"""
    return DeepResearchGraph(
        agents={role: agent for role in _AGENT_ROLES},
        checkpoint_service=checkpoint_service,
    )


@pytest.mark.asyncio
async def test_failed_checkpoint_never_emits_outline_approval(monkeypatch):
    graph = _graph(FakeArchitect(), FailingCheckpointService())
    monkeypatch.setattr(graph_module, "clear_cancel_flag", lambda _session_id: None)
    monkeypatch.setattr(
        graph_module,
        "is_research_cancelled",
        lambda _session_id: False,
    )
    state = {
        "query": "产业研究",
        "session_id": "session-1",
        "phase": "init",
        "messages": [],
        "facts": [],
        "references": [],
        "charts": [],
        "knowledge_graph": {"nodes": [], "edges": []},
        "final_report": "",
    }

    events = [event async for event in graph._run_simplified(state)]

    assert any(event["type"] == "error" for event in events)
    assert not any(
        event["type"] == "outline_pending_approval" for event in events
    )


@pytest.mark.asyncio
async def test_completion_saves_final_state_and_ui_before_emitting_report(monkeypatch):
    graph = _graph(CompletingCritic(), RecordingCheckpointService())
    monkeypatch.setattr(graph_module, "clear_cancel_flag", lambda _session_id: None)
    monkeypatch.setattr(
        graph_module,
        "is_research_cancelled",
        lambda _session_id: False,
    )
    state = {
        "query": "industry research",
        "session_id": "session-1",
        "phase": "reviewing",
        "iteration": 0,
        "max_iterations": 1,
        "messages": [],
        "facts": [],
        "references": [],
        "charts": [],
        "knowledge_graph": {"nodes": [], "edges": []},
        "final_report": "pre-review draft",
    }

    events = [event async for event in graph._run_simplified(state)]

    assert graph.checkpoint_service.saved
    final_save = graph.checkpoint_service.saved[-1]
    assert final_save["status"] == "completed"
    assert final_save["state"]["phase"] == "completed"
    assert final_save["final_report"] == "final revised report"
    assert final_save["ui_state"]["streaming_report"] == "final revised report"
    event_types = [event.get("type") for event in events]
    assert event_types.index("checkpoint_saved") < event_types.index("research_complete")
    assert any(
        event.get("type") == "research_complete"
        and event.get("final_report") == "final revised report"
        for event in events
    )


@pytest.mark.asyncio
async def test_failed_final_checkpoint_never_emits_research_complete(monkeypatch):
    graph = _graph(CompletingCritic(), FailingCheckpointService())
    monkeypatch.setattr(graph_module, "clear_cancel_flag", lambda _session_id: None)
    monkeypatch.setattr(
        graph_module,
        "is_research_cancelled",
        lambda _session_id: False,
    )
    state = {
        "query": "industry research",
        "session_id": "session-1",
        "phase": "reviewing",
        "iteration": 0,
        "max_iterations": 1,
        "messages": [],
        "facts": [],
        "references": [],
        "charts": [],
        "knowledge_graph": {"nodes": [], "edges": []},
        "final_report": "pre-review draft",
    }

    events = [event async for event in graph._run_simplified(state)]

    assert any(event.get("type") == "error" for event in events)
    assert not any(event.get("type") == "research_complete" for event in events)
