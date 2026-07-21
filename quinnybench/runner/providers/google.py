"""Google Gemini adapter.

Uses the `google-genai` SDK (the current maintained one; `google-generativeai`
is the older namespace). Gemini's message shape differs enough from OpenAI's
that a real adapter is clearer than shoehorning it into the OpenAI path.
"""
import os

from .base import Provider, Response


class GoogleProvider(Provider):
    name = "google"
    env_var = "GOOGLE_API_KEY"

    def is_available(self) -> bool:
        return bool(os.environ.get(self.env_var))

    def complete(self, prompt, *, model, temperature=0.0, max_tokens=4096):
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=os.environ[self.env_var])
        resp = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            ),
        )
        meta = getattr(resp, "usage_metadata", None)
        return Response(
            text=resp.text or "",
            model=model,
            input_tokens=getattr(meta, "prompt_token_count", 0) if meta else 0,
            output_tokens=getattr(meta, "candidates_token_count", 0) if meta else 0,
            raw={},
        )
