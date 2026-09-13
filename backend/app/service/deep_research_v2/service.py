# Copyright © 2026 深圳市深维智见教育科技有限公司 版权所有
# 未经授权，禁止转售或仿制。

"""
DeepResearch V2.0 - 服务入口

提供与现有路由兼容的接口，支持 SSE 流式输出。
"""

import os
import json
import uuid
import logging
from contextlib import nullcontext
from time import perf_counter
from typing import AsyncGenerator, Dict, Any, Optional

from observability.context import bind_context, current_context
from observability.events import bind_event_recorder, bind_run_usage, record_research_event
from observability.metrics import application_metrics
from observability.tracing import span
from service.research_observability_service import ResearchObservabilityService

from .graph import DeepResearchGraph

# 导入配置
try:
    from config.llm_config import get_config
except ImportError:
    try:
        from app.config.llm_config import get_config
    except ImportError:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        from config.llm_config import get_config

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("DeepResearchV2Service")


class DeepResearchV2Service:
    """
    DeepResearch V2.0 服务

    特点：
    - 多智能体协作
    - 对抗式质检
    - 代码解释器
    - 流式输出
    """

    def __init__(
        self,
        llm_api_key: Optional[str] = None,
        llm_base_url: Optional[str] = None,
        search_api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_iterations: Optional[int] = None,
        observability_service: Optional[ResearchObservabilityService] = None,
    ):
        """
        初始化服务

        所有参数都是可选的，会从配置文件读取默认值

        Args:
            llm_api_key: LLM API 密钥（可选，默认从配置读取）
            llm_base_url: LLM API 基础 URL（可选，默认从配置读取）
            search_api_key: 搜索 API 密钥（可选，默认从配置读取）
            model: 默认模型名称（可选，默认从配置读取）
            max_iterations: 最大迭代次数（可选，默认从配置读取）
        """
        # 获取配置
        config = get_config()

        self.llm_api_key = llm_api_key or config.api_key
        self.llm_base_url = llm_base_url or config.base_url
        self.search_api_key = search_api_key or config.search_api_key
        self.model = model or config.default_model
        self.max_iterations = max_iterations or config.research.max_iterations
        self.observability_service = observability_service or ResearchObservabilityService()

        # 创建工作流图（使用配置）
        self.graph = DeepResearchGraph(
            llm_api_key=self.llm_api_key,
            llm_base_url=self.llm_base_url,
            search_api_key=self.search_api_key,
            model=self.model,
            max_iterations=self.max_iterations
        )

        logger.info(f"DeepResearch V2 Service initialized with default model: {self.model}")

    async def research(
        self,
        query: str,
        session_id: Optional[str] = None,
        kb_name: Optional[str] = None,
        resume: bool = False,
        user_id: Optional[str] = None,
        search_web: bool = True,
        search_local: bool = False,
    ) -> AsyncGenerator[str, None]:
        """Execute a correlated deep-research run and stream enriched SSE events."""

        session_id = session_id or str(uuid.uuid4())
        previous_research_id = None
        if resume and user_id:
            try:
                previous_runs = self.observability_service.list_runs(
                    session_id=session_id,
                    user_id=user_id,
                    limit=1,
                )["items"]
                if previous_runs:
                    previous_research_id = previous_runs[0]["research_id"]
            except Exception:
                logger.exception(
                    "Failed to find a previous run; starting a new research lineage",
                    extra={"event": "research.previous_run_lookup_failed"},
                )

        run = None
        terminal_status = None
        with bind_context(session_id=session_id):
            with span(
                "deep_research.run",
                kind="agent",
                attributes={
                    "resume": resume,
                    "search_web": search_web,
                    "search_local": search_local,
                },
            ) as root_trace:
                if user_id:
                    try:
                        context = current_context()
                        run = self.observability_service.start_run(
                            session_id=session_id,
                            user_id=user_id,
                            query=query,
                            research_id=previous_research_id,
                            request_id=context.request_id if context else None,
                            trace_id=root_trace.trace_id,
                            metadata={
                                "resume": resume,
                                "search_web": search_web,
                                "search_local": search_local,
                                "kb_name": kb_name,
                            },
                        )
                    except Exception:
                        logger.exception(
                            "Failed to create run ledger; research will continue",
                            extra={"event": "research.run_start_persistence_failed"},
                        )

                with bind_context(
                    research_id=run["research_id"] if run else None,
                    run_id=run["run_id"] if run else None,
                    trace_id=root_trace.trace_id,
                    span_id=root_trace.span_id,
                ):
                    def persist_event(**event_fields):
                        context = current_context()
                        return self.observability_service.record_event(
                            run_id=run["run_id"],
                            trace_id=context.trace_id if context else None,
                            span_id=context.span_id if context else None,
                            **event_fields,
                        )

                    recorder_context = bind_event_recorder(persist_event) if run else nullcontext()
                    with recorder_context, bind_run_usage() as usage:
                        phase_name = None
                        phase_started_at = None
                        try:
                            async for chunk in self._research_stream(
                                query=query,
                                session_id=session_id,
                                kb_name=kb_name,
                                resume=resume,
                                user_id=user_id,
                                search_web=search_web,
                                search_local=search_local,
                            ):
                                if chunk == "data: [DONE]\n\n":
                                    continue
                                try:
                                    event = json.loads(chunk.removeprefix("data: "))
                                except (json.JSONDecodeError, TypeError):
                                    yield chunk
                                    continue

                                event_type = str(event.get("type", "unknown"))
                                event_phase = event.get("phase")
                                record_research_event(
                                    event_type,
                                    phase=str(event_phase) if event_phase else None,
                                    status="error" if event_type == "error" else "info",
                                    payload=event,
                                )

                                if event_type == "phase" and event_phase:
                                    now = perf_counter()
                                    if phase_name and phase_started_at is not None:
                                        application_metrics.research_phase_duration.labels(
                                            phase_name,
                                            "success",
                                        ).observe(now - phase_started_at)
                                    phase_name = str(event_phase)[:48]
                                    phase_started_at = now

                                terminal_status = {
                                    "research_complete": "completed",
                                    "outline_pending_approval": "paused",
                                    "research_cancelled": "cancelled",
                                    "error": "failed",
                                }.get(event_type, terminal_status)

                                if run:
                                    event.update(
                                        run_id=run["run_id"],
                                        research_id=run["research_id"],
                                        trace_id=root_trace.trace_id,
                                    )
                                yield self._format_sse(event)
                        finally:
                            if phase_name and phase_started_at is not None:
                                outcome = "failure" if terminal_status == "failed" else "success"
                                application_metrics.research_phase_duration.labels(
                                    phase_name,
                                    outcome,
                                ).observe(perf_counter() - phase_started_at)

                            final_status = terminal_status or "cancelled"
                            if run:
                                try:
                                    self.observability_service.finish_run(
                                        run_id=run["run_id"],
                                        status=final_status,
                                        input_tokens=usage.input_tokens,
                                        output_tokens=usage.output_tokens,
                                        estimated_cost=usage.estimated_cost,
                                        error_code="research_failed" if final_status == "failed" else None,
                                    )
                                    application_metrics.research_runs.labels(final_status).inc()
                                except Exception:
                                    logger.exception(
                                        "Failed to finalize run ledger",
                                        extra={"event": "research.run_finalize_failed"},
                                    )
                            root_trace.update(
                                output={
                                    "status": final_status,
                                    "input_tokens": usage.input_tokens,
                                    "output_tokens": usage.output_tokens,
                                }
                            )

        yield "data: [DONE]\n\n"

    async def _research_stream(
        self,
        query: str,
        session_id: Optional[str] = None,
        kb_name: Optional[str] = None,
        resume: bool = False,
        user_id: Optional[str] = None,
        search_web: bool = True,
        search_local: bool = False
    ) -> AsyncGenerator[str, None]:
        """
        执行深度研究（SSE 流式输出）

        Args:
            query: 用户问题
            session_id: 会话ID（可选）
            kb_name: 知识库名称（可选）
            resume: 是否从检查点恢复
            user_id: 用户ID（用于检查点）
            search_web: 是否启用网络搜索（默认True）
            search_local: 是否启用本地知识库搜索（默认False）

        Yields:
            SSE 格式的事件字符串
        """
        if not session_id:
            session_id = str(uuid.uuid4())

        if resume:
            logger.info(f"Resuming research for session {session_id}")
        else:
            logger.info(f"Starting research for session {session_id}: {query[:50]}...")
            logger.info(f"Search modes - web: {search_web}, local: {search_local}")

        try:
            async for event in self.graph.run(
                query, session_id,
                resume=resume,
                user_id=user_id,
                search_web=search_web,
                search_local=search_local,
                kb_name=kb_name
            ):
                # 转换为 SSE 格式
                yield self._format_sse(event)

        except Exception as e:
            logger.error(f"Research error: {e}")
            yield self._format_sse({
                "type": "error",
                "content": str(e)
            })

        # 发送结束标记
        yield "data: [DONE]\n\n"

    def _format_sse(self, event: Dict[str, Any]) -> str:
        """格式化为 SSE 事件"""
        return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    async def research_sync(
        self,
        query: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        同步执行研究（返回完整结果）

        Args:
            query: 用户问题
            session_id: 会话ID

        Returns:
            完整的研究结果
        """
        if not session_id:
            session_id = str(uuid.uuid4())

        state = await self.graph.run_sync(query, session_id)

        return {
            "session_id": session_id,
            "query": query,
            "final_report": state.get("final_report", ""),
            "quality_score": state.get("quality_score", 0.0),
            "outline": state.get("outline", []),
            "facts": state.get("facts", []),
            "data_points": state.get("data_points", []),
            "charts": state.get("charts", []),
            "references": state.get("references", []),
            "insights": state.get("insights", []),
            "iterations": state.get("iteration", 0),
            "phase": state.get("phase", ""),
            "logs": state.get("logs", [])
        }


def create_service(
    llm_api_key: Optional[str] = None,
    llm_base_url: Optional[str] = None,
    search_api_key: Optional[str] = None,
    model: Optional[str] = None
) -> DeepResearchV2Service:
    """
    工厂函数：创建 DeepResearch V2 服务

    所有参数都是可选的，会从配置文件读取默认值

    Args:
        llm_api_key: LLM API 密钥（可选）
        llm_base_url: LLM API 基础 URL（可选）
        search_api_key: 搜索 API 密钥（可选）
        model: 默认模型名称（可选）

    Returns:
        DeepResearchV2Service 实例
    """
    return DeepResearchV2Service(
        llm_api_key=llm_api_key,
        llm_base_url=llm_base_url,
        search_api_key=search_api_key,
        model=model
    )
