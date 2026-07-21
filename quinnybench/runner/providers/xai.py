from .openai import OpenAIProvider


class XAIProvider(OpenAIProvider):
    name = "xai"
    env_var = "XAI_API_KEY"
    base_url = "https://api.x.ai/v1"
