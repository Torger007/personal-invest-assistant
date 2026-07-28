"""
Agent Service

提供自主分析和问答交互两种模式。
"""
import time
import logging
from sqlalchemy import select

from app.agent.core import AgentCore
from app.agent.prompt_loader import get_agent_system_prompt, render_agent_prompt
from app.portfolio import get_portfolio_codes, get_portfolio_info
from app.models.agent import AgentAnalysis
from app.utils.db import AsyncSessionLocal

logger = logging.getLogger(__name__)


class AgentService:
    """Agent 服务"""

    def __init__(self):
        self.core = AgentCore()

    async def analyze_portfolio(self) -> str:
        """自主分析模式：分析用户持仓基金，生成投资建议。

        Returns:
            str: 分析报告
        """
        start_time = time.time()

        # 构建分析提示
        portfolio = get_portfolio_info()
        portfolio_str = "\n".join([
            f"- {fund['code']} ({fund['name']}): 权重 {fund['weight']*100:.0f}%"
            for fund in portfolio
        ])

        prompt = render_agent_prompt(
            "autonomous_portfolio_analysis",
            portfolio=portfolio_str,
        )
        system_prompt = get_agent_system_prompt()

        self.core.reset()
        result = await self.core.run(prompt, system_prompt=system_prompt)

        duration = int(time.time() - start_time)

        await self._save_analysis(
            analysis_type="autonomous",
            tool_calls=self.core.get_conversation(),
            summary=result,
            duration_seconds=duration
        )

        return result

    async def ask_question(self, question: str) -> str:
        """问答交互模式：回答用户投资问题。

        Args:
            question: 用户问题

        Returns:
            str: Agent 回答
        """
        start_time = time.time()

        portfolio_codes = get_portfolio_codes()
        context_prompt = render_agent_prompt(
            "interactive_question",
            portfolio_codes=", ".join(portfolio_codes),
            question=question,
        )
        system_prompt = get_agent_system_prompt()

        self.core.reset()
        result = await self.core.run(context_prompt, system_prompt=system_prompt)

        duration = int(time.time() - start_time)

        await self._save_analysis(
            analysis_type="interactive",
            tool_calls=self.core.get_conversation(),
            summary=result,
            duration_seconds=duration
        )

        return result

    async def _save_analysis(
        self,
        analysis_type: str,
        tool_calls: list,
        summary: str,
        duration_seconds: int
    ):
        """保存分析历史到数据库"""
        try:
            provider_info = self.core.get_provider_info()
            async with AsyncSessionLocal() as session:
                analysis = AgentAnalysis(
                    analysis_type=analysis_type,
                    tool_calls=tool_calls,
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
