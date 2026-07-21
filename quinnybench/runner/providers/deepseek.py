from .openai import OpenAIProvider


class DeepSeekProvider(OpenAIProvider):
    name = "deepseek"
    env_var = "DEEPSEEK_API_KEY"
    base_url = "https://api.deepseek.com/v1"
