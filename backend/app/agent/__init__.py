"""
投资 Agent 模块

提供 LLM 驱动的自主分析和问答交互能力。
"""

__all__ = ["AgentCore"]


def __getattr__(name: str):
    """Lazy-load heavy agent components when requested."""
    if name == "AgentCore":
        from app.agent.core import AgentCore

        return AgentCore
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
