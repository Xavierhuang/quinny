from .base import Provider, Response
from .anthropic import AnthropicProvider
from .openai import OpenAIProvider
from .google import GoogleProvider
from .xai import XAIProvider
from .deepseek import DeepSeekProvider
from .openrouter import OpenRouterProvider

REGISTRY = {
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
    "google": GoogleProvider,
    "xai": XAIProvider,
    "deepseek": DeepSeekProvider,
    "openrouter": OpenRouterProvider,
}


def get(name: str) -> Provider:
    if name not in REGISTRY:
        raise KeyError(f"unknown provider '{name}'. known: {sorted(REGISTRY)}")
    return REGISTRY[name]()
