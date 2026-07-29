"""
Agent Service

提供自主分析和问答交互两种模式。
"""
import time
import logging
from typing import Any, AsyncIterator
from sqlalchemy import select

from app.agent.core import AgentCore
from app.agent.planner import AgentPlanner
from app.agent.prompt_loader import get_agent_system_prompt, render_agent_prompt
from app.portfolio import get_portfolio_codes, get_portfolio_info
from app.models.agent import AgentAnalysis
from app.utils.db import AsyncSessionLocal

logger = logging.getLogger(__name__)


class AgentService:
    """Agent 服务"""

    def __init__(self):
        self.planner = AgentPlanner()

    async def analyze_portfolio(self) -> str:
        """自主分析模式：分析用户持仓基金，生成投资建议。

        Returns:
            str: 分析报告
        """
        async for event in self.stream_portfolio_analysis():
            if event["type"] == "complete":
                return event["answer"]
            if event["type"] == "error":
                raise RuntimeError(event["message"])
        raise RuntimeError("组合分析未生成结果")

    async def ask_question(self, question: str) -> str:
        """问答交互模式：回答用户投资问题。

        Args:
            question: 用户问题

        Returns:
            str: Agent 回答
        """
        async for event in self.stream_question(question):
            if event["type"] == "complete":
                return event["answer"]
            if event["type"] == "error":
                raise RuntimeError(event["message"])
        raise RuntimeError("问答未生成结果")

    async def stream_question(self, question: str) -> AsyncIterator[dict[str, Any]]:
        """Stream a question's tool progress and generated answer."""
        portfolio_codes = get_portfolio_codes()
        prompt = render_agent_prompt(
            "interactive_question",
            portfolio_codes=", ".join(portfolio_codes),
            question=question,
        )
        async for event in self._stream_and_save(
            analysis_type="interactive",
            prompt=prompt,
            plan=self.planner.plan_question(question),
            trace_question=question,
        ):
            yield event

    async def stream_portfolio_analysis(self) -> AsyncIterator[dict[str, Any]]:
        """Stream the autonomous portfolio analysis for a background task."""
        portfolio = get_portfolio_info()
        portfolio_str = "\n".join(
            f"- {fund['code']} ({fund['name']}): 权重 {fund['weight'] * 100:.0f}%"
            for fund in portfolio
        )
        prompt = render_agent_prompt("autonomous_portfolio_analysis", portfolio=portfolio_str)
        async for event in self._stream_and_save(
            analysis_type="autonomous",
            prompt=prompt,
            plan=self.planner.plan_portfolio_analysis(),
            trace_question="组合自主分析",
        ):
            yield event

    async def _stream_and_save(
        self,
        analysis_type: str,
        prompt: str,
        plan,
        trace_question: str,
    ) -> AsyncIterator[dict[str, Any]]:
        core = AgentCore()
        start_time = time.time()
        try:
            async for event in core.stream_planned(
                prompt,
                plan=plan,
                system_prompt=get_agent_system_prompt(),
                trace_question=trace_question,
            ):
                if event["type"] == "complete":
                    await self._save_analysis(
                        core=core,
                        analysis_type=analysis_type,
                        execution_record=core.get_execution_trace(),
                        summary=event["answer"],
                        duration_seconds=int(time.time() - start_time),
                    )
                yield event
        except Exception as e:
            logger.exception("[Agent] 流式执行失败")
            yield {"type": "error", "message": str(e)}

    async def _save_analysis(
        self,
        core: AgentCore,
        analysis_type: str,
        execution_record: dict,
        summary: str,
        duration_seconds: int
    ):
        """保存分析历史到数据库"""
        try:
            provider_info = core.get_provider_info()
            async with AsyncSessionLocal() as session:
                analysis = AgentAnalysis(
                    analysis_type=analysis_type,
                    tool_calls=execution_record,
                    summary=summary,
                    llm_provider=provider_info["provider"],
                    llm_model=provider_info["model"],
                    duration_seconds=duration_seconds
                )
                session.add(analysis)
                await session.commit()
        except Exception as e:
            logger.error(f"[Agent] 保存分析历史失败: {e}")

    async def get_latest_analysis(self, limit: int = 10) -> list:
        """获取最新的分析历史"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(AgentAnalysis)
                .order_by(AgentAnalysis.created_at.desc())
                .limit(limit)
            )
            analyses = result.scalars().all()

            return [
                {
                    "id": a.id,
                    "type": a.analysis_type,
                    "summary": a.summary,
                    "created_at": str(a.created_at),
                    "duration": a.duration_seconds
                }
                for a in analyses
            ]


# 全局 Agent Service 实例
agent_service = AgentService()
