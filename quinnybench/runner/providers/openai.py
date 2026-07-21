"""OpenAI-compatible providers.

`OpenAIProvider` is the real thing. Subclass it and set `name`, `env_var`, and
`base_url` to reach any vendor that speaks the same protocol (xAI, DeepSeek,
OpenRouter, and many self-hosted runtimes). Overriding is cheaper than adding a
new client library per vendor.
"""
import os

from .base import Provider, Response


class OpenAIProvider(Provider):
    name = "openai"
    env_var = "OPENAI_API_KEY"
    base_url = None   # None → SDK default

    def is_available(self) -> bool:
        return bool(os.environ.get(self.env_var))

    def _client(self):
        from openai import OpenAI
        return OpenAI(api_key=os.environ[self.env_var], base_url=self.base_url)

    def complete(self, prompt, *, model, temperature=0.0, max_tokens=4096):
        resp = self._client().chat.completions.create(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        choice = resp.choices[0]
        u = getattr(resp, "usage", None)
        return Response(
            text=choice.message.content or "",
            model=model,
            input_tokens=getattr(u, "prompt_tokens", 0) if u else 0,
            output_tokens=getattr(u, "completion_tokens", 0) if u else 0,
            raw=resp.model_dump() if hasattr(resp, "model_dump") else {},
        )
