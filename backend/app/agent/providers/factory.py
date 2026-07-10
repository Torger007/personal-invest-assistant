"""Provider 工厂模块"""
from app.agent.providers.base import BaseLLMProvider
from app.agent.providers.anthropic_provider import AnthropicProvider
from app.agent.providers.openai_provider import OpenAIProvider
from app.config import settings


def create_provider() -> BaseLLMProvider:
    """根据配置创建 LLM Provider

    Returns:
        BaseLLMProvider: LLM Provider 实例

    Raises:
        ValueError: 当配置的 provider 名称不支持时
    """
    provider_name = getattr(settings, 'LLM_PROVIDER', 'anthropic')

    if provider_name == "anthropic":
        api_key = settings.ANTHROPIC_API_KEY
        model = getattr(settings, 'ANTHROPIC_MODEL', 'claude-sonnet-4-20250514')
        base_url = getattr(settings, 'ANTHROPIC_BASE_URL', '')
        return AnthropicProvider(api_key, model, base_url)

    elif provider_name == "openai":
        api_key = settings.OPENAI_API_KEY
        model = getattr(settings, 'OPENAI_MODEL', 'gpt-4-turbo-preview')
        base_url = getattr(settings, 'OPENAI_BASE_URL', '')
        return OpenAIProvider(api_key, model, base_url)

    else:
        raise ValueError(f"未知的 LLM provider: {provider_name}")
