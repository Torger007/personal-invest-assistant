"""LLM Provider 基础接口定义"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ToolCall:
    """工具调用"""
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class LLMResponse:
    """LLM 响应"""
    content: Optional[str] = None  # 最终回答
    tool_calls: Optional[List[ToolCall]] = None  # 工具调用列表
    usage: Optional[Dict[str, int]] = None  # token 使用统计


class BaseLLMProvider(ABC):
    """LLM Provider 基础类"""

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict]] = None,
        max_tokens: int = 4000,
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        """发送聊天请求

        Args:
            messages: 标准化消息列表，支持 user/assistant/tool role
            tools: 可用工具列表（可选）
            max_tokens: 最大生成 token 数
            system_prompt: 系统提示词（可选）

        Returns:
            LLMResponse: LLM 响应对象
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """获取 provider 名称"""
        pass
