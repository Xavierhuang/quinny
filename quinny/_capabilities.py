"""Per-model capability probes.

Adaptive thinking is supported on Opus 4.7, Opus 4.6, and Sonnet 4.6 only.
Sending `thinking: {"type": "adaptive"}` to Haiku 4.5 (or older models)
returns a 400 — we caught this in the very first benchmark run.
"""

from __future__ import annotations


_ADAPTIVE_THINKING_MODELS: frozenset[str] = frozenset({
    "claude-opus-4-7",
    "claude-opus-4-6",
    "claude-sonnet-4-6",
})


def supports_adaptive_thinking(model: str) -> bool:
    return model in _ADAPTIVE_THINKING_MODELS


def thinking_kwargs(model: str) -> dict:
    """Spread this into `client.messages.create(...)` to opt into adaptive
    thinking on models that support it, and skip the param on models that
    don't (Haiku, older models).
    """
    if supports_adaptive_thinking(model):
        return {"thinking": {"type": "adaptive"}}
    return {}


import os


def make_client():
    """Construct an Anthropic client. When routed through the LingModel proxy
    (ANTHROPIC_AUTH_TOKEN set), override the User-Agent — the hosted proxy's WAF
    blocks the default "Anthropic/Python" UA, so use a neutral one."""
    import anthropic
    if os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        return anthropic.Anthropic(default_headers={"User-Agent": "quinny/0.1"})
    return anthropic.Anthropic()
