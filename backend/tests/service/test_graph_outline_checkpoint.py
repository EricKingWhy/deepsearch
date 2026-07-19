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


@pytest.mark.asyncio
async def test_failed_checkpoint_never_emits_outline_approval(monkeypatch):
    graph = object.__new__(DeepResearchGraph)
    graph.architect = FakeArchitect()
    graph.checkpoint_service = FailingCheckpointService()
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
