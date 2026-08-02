"""
Agent Service

提供自主分析和问答交互两种模式。
"""
import time
import logging
from datetime import datetime, timedelta
from typing import Any, AsyncIterator
from uuid import uuid4

from sqlalchemy import func, select

from app.agent.core import AgentCore
from app.agent.planner import AgentPlanner
from app.agent.prompt_loader import get_agent_system_prompt, render_agent_prompt
from app.services.portfolio_service import get_user_portfolio
from app.models.agent import AgentAnalysis, AgentConversation, AgentMessage
from app.utils.db import AsyncSessionLocal

logger = logging.getLogger(__name__)

RECENT_MESSAGE_LIMIT = 8
SUMMARY_THRESHOLD = 20
ARCHIVE_AFTER_DAYS = 90


class AgentService:
    """Agent 服务"""

    def __init__(self):
        self.planner = AgentPlanner()

    async def analyze_portfolio(self, user_id: str) -> str:
        """自主分析模式：分析用户持仓基金，生成投资建议。

        Returns:
            str: 分析报告
        """
        async for event in self.stream_portfolio_analysis(user_id):
            if event["type"] == "complete":
                return event["answer"]
            if event["type"] == "error":
                raise RuntimeError(event["message"])
        raise RuntimeError("组合分析未生成结果")

    async def ask_question(self, question: str, user_id: str, conversation_id: str | None = None) -> str:
        """问答交互模式：回答用户投资问题。

        Args:
            question: 用户问题

        Returns:
            str: Agent 回答
        """
        async for event in self.stream_question(question, user_id, conversation_id):
            if event["type"] == "complete":
                return event["answer"]
            if event["type"] == "error":
                raise RuntimeError(event["message"])
        raise RuntimeError("问答未生成结果")

    async def stream_question(
        self, question: str, user_id: str, conversation_id: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream a question's tool progress and generated answer."""
        conversation, active_context, prior_messages = await self._prepare_conversation(
            question, user_id, conversation_id,
        )
        yield {
            "type": "conversation",
            "conversation_id": conversation.id,
            "title": conversation.title,
        }

        async with AsyncSessionLocal() as session:
            portfolio_codes = [fund["code"] for fund in await get_user_portfolio(session, user_id)]
        prompt = render_agent_prompt(
            "interactive_question",
            portfolio_codes=", ".join(portfolio_codes),
            question=question,
            conversation_context=self._format_conversation_context(
                conversation.summary, prior_messages,
            ),
        )
        plan = self.planner.plan_question(question, active_context)
        async for event in self._stream_and_save(
            analysis_type="interactive",
            prompt=prompt,
            plan=plan,
            trace_question=question,
            user_id=user_id,
        ):
            if event["type"] == "complete":
                event["conversation_id"] = conversation.id
                try:
                    message = await self._save_assistant_message(
                        conversation.id,
                        user_id,
                        question,
                        event["answer"],
                        plan,
                        event.get("analysis_id"),
                    )
                    event["message_id"] = message.id
                except Exception:
                    logger.exception("[Agent] 保存会话消息失败")
                    event["persistence_error"] = True
            yield event

    async def stream_portfolio_analysis(self, user_id: str) -> AsyncIterator[dict[str, Any]]:
        """Stream the autonomous portfolio analysis for a background task."""
        async with AsyncSessionLocal() as session:
            portfolio = await get_user_portfolio(session, user_id)
        portfolio_str = "\n".join(
            f"- {fund['code']} ({fund['name']}): 权重 {fund['weight'] * 100:.0f}%"
            for fund in portfolio
        )
        prompt = render_agent_prompt("autonomous_portfolio_analysis", portfolio=portfolio_str)
        async for event in self._stream_and_save(
            analysis_type="autonomous",
            prompt=prompt,
            plan=self.planner.plan_portfolio_analysis(),
            user_id=user_id,
            trace_question="组合自主分析",
        ):
            yield event

    async def _stream_and_save(
        self,
        analysis_type: str,
        prompt: str,
        plan,
        trace_question: str,
        user_id: str,
    ) -> AsyncIterator[dict[str, Any]]:
        core = AgentCore(user_id=user_id)
        start_time = time.time()
        try:
            async for event in core.stream_planned(
                prompt,
                plan=plan,
                system_prompt=get_agent_system_prompt(),
                trace_question=trace_question,
            ):
                if event["type"] == "complete":
                    event["analysis_id"] = await self._save_analysis(
                        core=core,
                        analysis_type=analysis_type,
                        execution_record=core.get_execution_trace(),
                        summary=event["answer"],
                        duration_seconds=int(time.time() - start_time),
                        user_id=user_id,
                    )
                yield event
        except Exception as e:
            logger.exception("[Agent] 流式执行失败")
            yield {"type": "error", "message": str(e)}

    async def _prepare_conversation(
        self, question: str, user_id: str, conversation_id: str | None,
    ) -> tuple[AgentConversation, dict[str, Any], list[AgentMessage]]:
        """Create or load a conversation and persist its incoming user message."""
        async with AsyncSessionLocal() as session:
            if conversation_id:
                conversation = await session.get(AgentConversation, conversation_id)
                if conversation and conversation.user_id != user_id:
                    conversation = None
                if not conversation or conversation.archived_at:
                    raise ValueError("会话不存在或已归档")
            else:
                conversation = AgentConversation(
                    id=str(uuid4()),
                    title=self._make_title(question),
                    active_context={},
                    user_id=user_id,
                )
                session.add(conversation)
                await session.flush()

            prior_messages = list((await session.execute(
                select(AgentMessage)
                .where(AgentMessage.conversation_id == conversation.id)
                .order_by(AgentMessage.created_at.desc())
                .limit(RECENT_MESSAGE_LIMIT)
            )).scalars().all())
            prior_messages.reverse()
            active_context = dict(conversation.active_context or {})
            session.add(AgentMessage(
                conversation_id=conversation.id,
                role="user",
                content=question,
            ))
            conversation.last_message_at = datetime.now()
            conversation.updated_at = datetime.now()
            await session.commit()
            await session.refresh(conversation)
            return conversation, active_context, prior_messages

    async def _save_assistant_message(
        self,
        conversation_id: str,
        user_id: str,
        question: str,
        answer: str,
        plan,
        analysis_id: int | None,
    ) -> AgentMessage:
        """Persist the answer and update context used by deterministic follow-ups."""
        async with AsyncSessionLocal() as session:
            conversation = await session.get(AgentConversation, conversation_id)
            if not conversation or conversation.user_id != user_id:
                raise ValueError("会话不存在")
            message = AgentMessage(
                conversation_id=conversation_id,
                role="assistant",
                content=answer,
                intent=plan.intent,
                plan=plan.to_dict(),
                analysis_id=analysis_id,
            )
            session.add(message)
            await session.flush()

            active_context = dict(conversation.active_context or {})
            if plan.fund_codes:
                active_context["last_fund_codes"] = plan.fund_codes
            active_context["last_intent"] = plan.intent
            active_context["last_question"] = question[:200]
            conversation.active_context = active_context
            conversation.last_message_at = datetime.now()
            conversation.updated_at = datetime.now()
            conversation.summary = await self._build_summary(session, conversation)
            await session.commit()
            await session.refresh(message)
            return message

    async def create_conversation(self, user_id: str) -> dict:
        async with AsyncSessionLocal() as session:
            conversation = AgentConversation(
                id=str(uuid4()), title="新对话", active_context={},
            )
            conversation.user_id = user_id
            session.add(conversation)
            await session.commit()
            return self._conversation_to_dict(conversation, 0)

    async def list_conversations(self, user_id: str, limit: int = 30) -> list[dict]:
        limit = max(1, min(limit, 100))
        async with AsyncSessionLocal() as session:
            await session.execute(
                AgentConversation.__table__.update()
                .where(AgentConversation.user_id == user_id)
                .where(AgentConversation.archived_at.is_(None))
                .where(AgentConversation.last_message_at < datetime.now() - timedelta(days=ARCHIVE_AFTER_DAYS))
                .values(archived_at=datetime.now(), updated_at=datetime.now())
            )
            await session.commit()
            conversations = list((await session.execute(
                select(AgentConversation)
                .where(AgentConversation.user_id == user_id)
                .where(AgentConversation.archived_at.is_(None))
                .order_by(AgentConversation.last_message_at.desc())
                .limit(limit)
            )).scalars().all())
            return [self._conversation_to_dict(
                conversation,
                await session.scalar(select(func.count(AgentMessage.id)).where(
                    AgentMessage.conversation_id == conversation.id,
                )) or 0,
            ) for conversation in conversations]

    async def get_conversation(self, user_id: str, conversation_id: str) -> dict:
        async with AsyncSessionLocal() as session:
            conversation = await session.get(AgentConversation, conversation_id)
            if not conversation or conversation.user_id != user_id:
                raise ValueError("会话不存在")
            messages = list((await session.execute(
                select(AgentMessage)
                .where(AgentMessage.conversation_id == conversation_id)
                .order_by(AgentMessage.created_at.asc())
            )).scalars().all())
            return {
                **self._conversation_to_dict(conversation, len(messages)),
                "messages": [self._message_to_dict(message) for message in messages],
            }

    async def archive_conversation(self, user_id: str, conversation_id: str) -> None:
        async with AsyncSessionLocal() as session:
            conversation = await session.get(AgentConversation, conversation_id)
            if not conversation or conversation.user_id != user_id:
                raise ValueError("会话不存在")
            conversation.archived_at = datetime.now()
            conversation.updated_at = datetime.now()
            await session.commit()

    async def get_analysis_report(self, user_id: str, analysis_id: int) -> dict:
        async with AsyncSessionLocal() as session:
            analysis = await session.get(AgentAnalysis, analysis_id)
            if not analysis or analysis.user_id != user_id:
                raise ValueError("报告不存在")
            return {
                "id": analysis.id,
                "summary": analysis.summary,
                "trace": analysis.tool_calls,
                "created_at": str(analysis.created_at),
                "duration": analysis.duration_seconds,
            }

    async def _build_summary(
        self, session, conversation: AgentConversation,
    ) -> str | None:
        messages = list((await session.execute(
            select(AgentMessage)
            .where(AgentMessage.conversation_id == conversation.id)
            .order_by(AgentMessage.created_at.asc())
        )).scalars().all())
        if len(messages) <= SUMMARY_THRESHOLD:
            return conversation.summary
        older_messages = messages[:-RECENT_MESSAGE_LIMIT]
        lines = ["早期对话摘要："]
        for message in older_messages[-12:]:
            role = "用户" if message.role == "user" else "助手"
            content = " ".join(message.content.split())[:220]
            lines.append(f"{role}：{content}")
        return "\n".join(lines)[:3000]

    @staticmethod
    def _make_title(question: str) -> str:
        return " ".join(question.split())[:80] or "新对话"

    @staticmethod
    def _format_conversation_context(
        summary: str | None, messages: list[AgentMessage],
    ) -> str:
        sections = [summary] if summary else []
        for message in messages:
            role = "用户" if message.role == "user" else "助手"
            sections.append(f"{role}：{' '.join(message.content.split())[:500]}")
        return "\n".join(section for section in sections if section) or "无"

    @staticmethod
    def _conversation_to_dict(conversation: AgentConversation, message_count: int) -> dict:
        return {
            "id": conversation.id,
            "title": conversation.title,
            "summary": conversation.summary,
            "last_message_at": str(conversation.last_message_at),
            "created_at": str(conversation.created_at),
            "message_count": message_count,
        }

    @staticmethod
    def _message_to_dict(message: AgentMessage) -> dict:
        return {
            "id": message.id,
            "role": message.role,
            "content": message.content,
            "intent": message.intent,
            "plan": message.plan,
            "analysis_id": message.analysis_id,
            "created_at": str(message.created_at),
        }

    async def _save_analysis(
        self,
        core: AgentCore,
        analysis_type: str,
        execution_record: dict,
        summary: str,
        duration_seconds: int,
        user_id: str,
    ) -> int | None:
        """保存分析历史到数据库"""
        try:
            provider_info = core.get_provider_info()
            async with AsyncSessionLocal() as session:
                analysis = AgentAnalysis(
                    user_id=user_id,
                    analysis_type=analysis_type,
                    tool_calls=execution_record,
                    summary=summary,
                    llm_provider=provider_info["provider"],
                    llm_model=provider_info["model"],
                    duration_seconds=duration_seconds
                )
                session.add(analysis)
                await session.commit()
                await session.refresh(analysis)
                return analysis.id
        except Exception as e:
            logger.error(f"[Agent] 保存分析历史失败: {e}")
            return None

    async def get_latest_analysis(self, user_id: str, limit: int = 10) -> list:
        """获取最新的分析历史"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(AgentAnalysis)
                .where(AgentAnalysis.user_id == user_id)
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
