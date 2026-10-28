"""适配器注册表 — 新增厂商 = 实现一个 Adapter 并在此注册"""
from app.adapters.base import ProviderAdapter

_registry: dict[str, ProviderAdapter] = {}


def register(adapter: ProviderAdapter) -> None:
    _registry[adapter.provider] = adapter


def get_adapter(provider: str) -> ProviderAdapter:
    a = _registry.get(provider)
    if a is None:
        raise KeyError(f"Unknown provider: {provider}")
    return a


def available_providers() -> list[str]:
    return sorted(_registry)


def _bootstrap() -> None:
    from app.adapters.anthropic import AnthropicAdapter
    from app.adapters.deepseek import DeepSeekAdapter
    from app.adapters.openai import OpenAIAdapter
    from app.adapters.openrouter import OpenRouterAdapter
    from app.adapters.siliconflow import SiliconFlowAdapter
    from app.adapters.zai import ZaiAdapter

    register(DeepSeekAdapter())
    register(OpenRouterAdapter())
    register(AnthropicAdapter())
    register(OpenAIAdapter())
    register(SiliconFlowAdapter())
    register(ZaiAdapter())


_bootstrap()
