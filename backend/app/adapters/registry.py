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
    from app.adapters.deepseek import DeepSeekAdapter
    from app.adapters.openrouter import OpenRouterAdapter

    register(DeepSeekAdapter())
    register(OpenRouterAdapter())
    # TODO: zai（社区逆向端点，待实测补录）/ anthropic / openai / siliconflow


_bootstrap()
