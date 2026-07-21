import os

from .base import Provider, Response


class AnthropicProvider(Provider):
    name = "anthropic"

    def is_available(self) -> bool:
        return bool(os.environ.get("ANTHROPIC_API_KEY"))

    def complete(self, prompt, *, model, temperature=0.0, max_tokens=4096):
        from anthropic import Anthropic
        client = Anthropic()
        msg = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        return Response(
            text=text,
            model=model,
            input_tokens=msg.usage.input_tokens,
            output_tokens=msg.usage.output_tokens,
            raw=msg.model_dump() if hasattr(msg, "model_dump") else {},
        )
