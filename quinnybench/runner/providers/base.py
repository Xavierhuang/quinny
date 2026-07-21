from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Response:
    text: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    raw: dict = field(default_factory=dict)


class Provider:
    """Adapter: prompt in, code out. One concrete class per API.

    Adapters keep API-shape differences out of the runner. They must:
      - return `Response.text` = the assistant's raw reply (fenced code block(s) included);
      - record token counts if the API provides them;
      - raise on network/auth errors so the runner records a `skipped` outcome.
    """

    name: str = "base"

    def is_available(self) -> bool:
        """Return True iff credentials for this provider are configured."""
        raise NotImplementedError

    def complete(self, prompt: str, *, model: str, temperature: float = 0.0,
                 max_tokens: int = 4096) -> Response:
        raise NotImplementedError
