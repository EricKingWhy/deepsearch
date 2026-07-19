"""Low-cardinality Prometheus metrics for HTTP and research workloads."""

from __future__ import annotations

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    REGISTRY,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from starlette.responses import Response


class ApplicationMetrics:
    """Own all application instruments and their bounded label sets."""

    def __init__(self, *, registry: CollectorRegistry = REGISTRY) -> None:
        self.registry = registry
        self.http_requests = Counter(
            "industry_http_requests_total",
            "HTTP requests handled by the API.",
            ("method", "route", "status"),
            registry=registry,
        )
        self.http_duration = Histogram(
            "industry_http_request_duration_seconds",
            "HTTP request latency in seconds.",
            ("method", "route"),
            registry=registry,
        )
        self.research_runs = Counter(
            "industry_research_runs_total",
            "Deep-research runs by terminal outcome.",
            ("outcome",),
            registry=registry,
        )
        self.research_phase_duration = Histogram(
            "industry_research_phase_duration_seconds",
            "Deep-research phase latency in seconds.",
            ("phase", "outcome"),
            registry=registry,
        )
        self.llm_calls = Counter(
            "industry_llm_calls_total",
            "LLM calls by provider, model, and outcome.",
            ("provider", "model", "outcome"),
            registry=registry,
        )
        self.llm_duration = Histogram(
            "industry_llm_request_duration_seconds",
            "LLM call latency in seconds.",
            ("provider", "model"),
            registry=registry,
        )
        self.llm_tokens = Counter(
            "industry_llm_tokens_total",
            "LLM token consumption.",
            ("provider", "model", "direction"),
            registry=registry,
        )
        self.retrieval_duration = Histogram(
            "industry_retrieval_duration_seconds",
            "Retrieval latency in seconds.",
            ("source", "outcome"),
            registry=registry,
        )
        self.tool_calls = Counter(
            "industry_tool_calls_total",
            "Research tool calls by type and outcome.",
            ("tool", "outcome"),
            registry=registry,
        )
        self.queue_depth = Gauge(
            "industry_research_queue_depth",
            "Number of research jobs waiting to run.",
            registry=registry,
        )

    def observe_http(self, *, method: str, route: str, status: int, duration: float) -> None:
        normalized_method = method.upper()
        normalized_route = route if route.startswith("/") else "unmatched"
        self.http_requests.labels(normalized_method, normalized_route, str(status)).inc()
        self.http_duration.labels(normalized_method, normalized_route).observe(max(duration, 0.0))


application_metrics = ApplicationMetrics()


def metrics_response(registry: CollectorRegistry = REGISTRY) -> Response:
    """Render a Prometheus text exposition response."""

    return Response(content=generate_latest(registry), media_type=CONTENT_TYPE_LATEST)

