"""OpenAI GPT API Provider 实现"""
import json
from typing import AsyncIterator, Any, List, Dict, Optional
from openai import AsyncOpenAI
from app.agent.providers.base import BaseLLMProvider, LLMResponse, ToolCall


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT API Provider"""

    def __init__(self, api_key: str, model: str = "gpt-4-turbo-preview",
                 base_url: str = ""):
        super().__init__(api_key, model)
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = AsyncOpenAI(**kwargs)

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict]] = None,
        max_tokens: int = 4000,
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        # 转换工具格式（OpenAI 使用 function calling）
        openai_tools = None
        if tools:
            openai_tools = [
                {
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool.get("input_schema", {})
                    }
                }
                for tool in tools
            ]

        request_messages = self._convert_messages(messages)
        if system_prompt:
            request_messages = [
                {"role": "system", "content": system_prompt},
                *request_messages,
            ]

        # 调用 API
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=request_messages,
            tools=openai_tools,
            max_tokens=max_tokens
        )

        # 解析响应
        choice = response.choices[0]
        content = choice.message.content
        tool_calls = []

        if choice.message.tool_calls:
            for tool_call in choice.message.tool_calls:
                tool_calls.append(ToolCall(
                    id=tool_call.id,
                    name=tool_call.function.name,
                    arguments=json.loads(tool_call.function.arguments)
                ))

        return LLMResponse(
            content=content,
            tool_calls=tool_calls if tool_calls else None,
            usage={
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens
            }
        )

    def get_provider_name(self) -> str:
        return "openai"

    async def stream_chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict]] = None,
        max_tokens: int = 4000,
        system_prompt: Optional[str] = None,
    ) -> AsyncIterator[str]:
        request_messages = self._convert_messages(messages)
        if system_prompt:
            request_messages = [{"role": "system", "content": system_prompt}, *request_messages]

        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=request_messages,
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices and (content := chunk.choices[0].delta.content):
                yield content

    def _convert_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert normalized agent messages to OpenAI chat messages."""
        converted = []

        for message in messages:
            role = message.get("role")

            if role == "tool":
                converted.append({
                    "role": "tool",
                    "tool_call_id": message["tool_call_id"],
                    "content": message.get("content", ""),
                })
                continue

            converted_message = {
                "role": role,
                "content": message.get("content", ""),
            }

            if role == "assistant" and message.get("tool_calls"):
                converted_message["tool_calls"] = [
                    {
                        "id": tool_call["id"],
                        "type": "function",
                        "function": {
                            "name": tool_call["name"],
                            "arguments": json.dumps(
                                tool_call.get("arguments", {}),
                                ensure_ascii=False,
                                default=str,
                            ),
                        },
                    }
                    for tool_call in message["tool_calls"]
                ]

            converted.append(converted_message)

        return converted
