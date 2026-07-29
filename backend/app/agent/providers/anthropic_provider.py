"""Anthropic Claude API Provider 实现"""
from typing import AsyncIterator, Any, List, Dict, Optional
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
        messages: List[Dict[str, Any]],
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
            messages=self._convert_messages(messages),
            system=system_prompt or None,
            tools=anthropic_tools
        )

        # 解析响应
        text_blocks = []
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                text_blocks.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    arguments=block.input
                ))

        return LLMResponse(
            content="\n".join(text_blocks) if text_blocks else None,
            tool_calls=tool_calls if tool_calls else None,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens
            }
        )

    def get_provider_name(self) -> str:
        return "anthropic"

    async def stream_chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict]] = None,
        max_tokens: int = 4000,
        system_prompt: Optional[str] = None,
    ) -> AsyncIterator[str]:
        async with self.client.messages.stream(
            model=self.model,
            max_tokens=max_tokens,
            messages=self._convert_messages(messages),
            system=system_prompt or None,
            tools=None,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    def _convert_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert normalized agent messages to Anthropic Messages API format."""
        converted = []

        for message in messages:
            role = message.get("role")

            if role == "tool":
                tool_result = {
                    "type": "tool_result",
                    "tool_use_id": message["tool_call_id"],
                    "content": message.get("content", ""),
                }
                if converted and converted[-1]["role"] == "user" and isinstance(converted[-1]["content"], list):
                    converted[-1]["content"].append(tool_result)
                else:
                    converted.append({
                        "role": "user",
                        "content": [tool_result],
                    })
                continue

            if role == "assistant" and message.get("tool_calls"):
                content = []
                if message.get("content"):
                    content.append({
                        "type": "text",
                        "text": message["content"],
                    })
                content.extend([
                    {
                        "type": "tool_use",
                        "id": tool_call["id"],
                        "name": tool_call["name"],
                        "input": tool_call.get("arguments", {}),
                    }
                    for tool_call in message["tool_calls"]
                ])
                converted.append({
                    "role": "assistant",
                    "content": content,
                })
                continue

            converted.append({
                "role": role,
                "content": message.get("content", ""),
            })

        return converted
