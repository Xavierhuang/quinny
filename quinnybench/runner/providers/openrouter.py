from .openai import OpenAIProvider


class OpenRouterProvider(OpenAIProvider):
    """OpenRouter is the escape hatch for models we don't have a direct API
    for — Kimi, Qwen, Llama, older Grok/Gemini snapshots, etc. Model ids on
    OpenRouter are namespaced (e.g. 'moonshotai/kimi-k2', 'meta-llama/llama-3.3-70b-instruct').
    """
    name = "openrouter"
    env_var = "OPENROUTER_API_KEY"
    base_url = "https://openrouter.ai/api/v1"
