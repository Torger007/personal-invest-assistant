"""
Agent Core

负责对话管理和工具调用循环。
实现 LLM 与工具的交互闭环：LLM 决定调用工具 → 执行工具 → 结果回传 LLM → 直到给出最终回答。
"""
import json
import logging
from typing import Any, List, Dict

from app.agent.providers import create_provider, LLMResponse
from app.agent.tools import tool_registry

logger = logging.getLogger(__name__)

# 防止无限循环的最大迭代次数
MAX_ITERATIONS = 15


class AgentCore:
    """Agent 核心"""

    def __init__(self):
        self.llm = create_provider()
        self.tools = tool_registry
        self.conversation: List[Dict[str, Any]] = []

    async def run(self, user_input: str, system_prompt: str | None = None) -> str:
        """
        运行 Agent（工具调用循环）

        Args:
            user_input: 用户输入
            system_prompt: 系统提示词

        Returns:
            str: Agent 最终回答
        """
        # 添加用户消息
        self.conversation.append({"role": "user", "content": user_input})

        iteration = 0

        while iteration < MAX_ITERATIONS:
            iteration += 1

            # 调用 LLM
            response: LLMResponse = await self.llm.chat(
                messages=self.conversation,
                tools=self.tools.get_definitions(),
                system_prompt=system_prompt
            )

            # 检查是否需要调用工具
            if response.tool_calls:
                # 添加标准 assistant tool-call 消息
                self.conversation.append({
                    "role": "assistant",
                    "content": response.content or "",
                    "tool_calls": [
                        {
                            "id": tool_call.id,
                            "name": tool_call.name,
                            "arguments": tool_call.arguments,
                        }
                        for tool_call in response.tool_calls
                    ],
                })

                # 执行所有工具调用
                for tool_call in response.tool_calls:
                    logger.info(f"[Agent] 调用工具: {tool_call.name} 参数: {tool_call.arguments}")
                    result = await self.tools.execute(tool_call.name, tool_call.arguments)
                    logger.info(f"[Agent] 工具 {tool_call.name} 返回: {result.get('status')}")

                    # 添加标准 tool result 消息
                    self.conversation.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_call.name,
                        "content": json.dumps(result, ensure_ascii=False, default=str),
                    })

            else:
                # 没有工具调用，返回最终回答
                if response.content:
                    self.conversation.append({
                        "role": "assistant",
                        "content": response.content
                    })
                    return response.content

                # 既无工具调用也无内容，退出
                return "分析完成，但未生成有效回答。"

        logger.warning(f"[Agent] 达到最大迭代次数 {MAX_ITERATIONS}，强制退出")
        return "分析过程涉及过多步骤，已截断。请尝试缩小问题范围。"

    def reset(self):
        """重置对话历史"""
        self.conversation = []

    def get_conversation(self) -> List[Dict[str, Any]]:
        """获取当前对话历史"""
        return self.conversation.copy()

    def get_provider_info(self) -> Dict[str, str]:
        """获取当前使用的 LLM 信息"""
        return {
            "provider": self.llm.get_provider_name(),
            "model": self.llm.model,
        }
