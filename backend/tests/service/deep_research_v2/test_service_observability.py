import json
import importlib
import sys
from contextlib import contextmanager
from types import SimpleNamespace
from uuid import uuid4

from service.deep_research_v2.agents.architect import ChiefArchitect
from service.deep_research_v2.agents.critic import CriticMaster
from service.deep_research_v2.agents.data_analyst import DataAnalyst
from service.deep_research_v2.agents.scout import DeepScout
from service.deep_research_v2.agents.wizard import CodeWizard
from service.deep_research_v2.agents.writer import LeadWriter


_agents_package = sys.modules["service.deep_research_v2.agents"]
for _agent_class in (
    ChiefArchitect,
    CriticMaster,
    DataAnalyst,
    DeepScout,
    CodeWizard,
    LeadWriter,
):
    setattr(_agents_package, _agent_class.__name__, _agent_class)

service_module = importlib.import_module("service.deep_research_v2.service")


class FakeGraph:
    def __init__(self, **_kwargs):
        self.events = [
            {"type": "phase", "phase": "researching", "content": "starting"},
            {"type": "research_complete", "facts_count": 2, "charts_count": 1},
        ]

    async def run(self, *_args, **_kwargs):
        for event in self.events:
            yield dict(event)


class FakeLedger:
    def __init__(self):
        self.started = []
        self.recorded = []
        self.finished = []
        self.previous_research_id = None

    def list_runs(self, **_kwargs):
        items = []
        if self.previous_research_id:
            items.append({"research_id": self.previous_research_id})
        return {"items": items, "next_cursor": None}

    def start_run(self, **kwargs):
        self.started.append(kwargs)
        return {
            "run_id": str(uuid4()),
            "research_id": kwargs.get("research_id") or str(uuid4()),
            "status": "running",
        }

    def record_event(self, **kwargs):
        self.recorded.append(kwargs)
        return kwargs

    def finish_run(self, **kwargs):
        self.finished.append(kwargs)
        return kwargs


class FakeRootTrace:
    trace_id = "trace-root"
    span_id = "span-root"

    def update(self, **_kwargs):
        pass


def make_service(monkeypatch, ledger):
    config = SimpleNamespace(
        api_key="llm-key",
        base_url="http://llm.invalid/v1",
        search_api_key="search-key",
        default_model="qwen-plus",
        research=SimpleNamespace(max_iterations=2),
    )
    monkeypatch.setattr(service_module, "get_config", lambda: config)
    monkeypatch.setattr(service_module, "DeepResearchGraph", FakeGraph)

    @contextmanager
    def fake_span(*_args, **_kwargs):
        yield FakeRootTrace()

    monkeypatch.setattr(service_module, "span", fake_span, raising=False)
    return service_module.DeepResearchV2Service(observability_service=ledger)


async def test_research_creates_correlated_run_events_and_completion(monkeypatch):
    ledger = FakeLedger()
    service = make_service(monkeypatch, ledger)
    session_id = str(uuid4())
    user_id = str(uuid4())

    chunks = [
        chunk
        async for chunk in service.research(
            "private research question",
            session_id=session_id,
            user_id=user_id,
        )
    ]

    first_event = json.loads(chunks[0].removeprefix("data: "))
    assert first_event["run_id"]
    assert first_event["research_id"]
    assert first_event["trace_id"] == "trace-root"
    assert ledger.started[0]["session_id"] == session_id
    assert [event["event_type"] for event in ledger.recorded] == ["phase", "research_complete"]
    assert ledger.finished[0]["status"] == "completed"
    assert chunks[-1] == "data: [DONE]\n\n"


async def test_resume_reuses_research_id_and_closes_outline_pause(monkeypatch):
    ledger = FakeLedger()
    ledger.previous_research_id = str(uuid4())
    service = make_service(monkeypatch, ledger)
    service.graph.events = [
        {"type": "outline_pending_approval", "phase": "awaiting_outline_approval"}
    ]

    _ = [
        chunk
        async for chunk in service.research(
            "continue research",
            session_id=str(uuid4()),
            user_id=str(uuid4()),
            resume=True,
        )
    ]

    assert ledger.started[0]["research_id"] == ledger.previous_research_id
    assert ledger.finished[0]["status"] == "paused"
