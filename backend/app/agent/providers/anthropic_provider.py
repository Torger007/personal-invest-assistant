"""Anthropic Claude API Provider 实现"""
from typing import List, Dict, Optional
from anthropic import AsyncAnthropic
from app.agent.providers.base import BaseLLMProvider, LLMResponse, ToolCall


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude API Provider"""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514",
                 base_url: str = ""):
        super().__init__(api_key, model)
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = AsyncAnthropic(**kwargs)

    async def chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        max_tokens: int = 4000,
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        # 转换工具格式（Anthropic 使用 input_schema）
        anthropic_tools = None
        if tools:
            anthropic_tools = [
                {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "input_schema": tool.get("input_schema", {})
                }
                for tool in tools
            ]

        # 调用 API
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=messages,
            system=system_prompt or None,
            tools=anthropic_tools
        )

        # 解析响应
        content = None
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                content = block.text
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    arguments=block.input
                ))

        return LLMResponse(
            content=content,
            tool_calls=tool_calls if tool_calls else None,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens
            }
        )

    def get_provider_name(self) -> str:
        return "anthropic"
