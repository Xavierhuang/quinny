"""English -> Quinny planner using the Claude API.

Wraps a Claude model call in a retry loop: if the returned source fails to
parse or fails semantic validation, the compiler error is fed back to the
model as a "fix it" turn. This is the Stage-1 pattern from docs/AI_PROMPT.md.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any

import anthropic

from quinny._capabilities import thinking_kwargs, make_client
from quinny.graph import GraphError, build_graph
from quinny.json_format import PLAN_SCHEMA, JsonPlanError, ast_to_json, json_to_ast
from quinny.nodes import Project
from quinny.parser import QuinnyParseError, parse
from quinny.usage import UsageTracker


SYSTEM_PROMPT = """You are a Quinny engineer. Quinny is a task-oriented intent language.
Output ONLY Quinny source. No prose. No markdown fences. No explanations.

## Quinny in one paragraph
A Quinny file describes WHAT should be built, not HOW. It has NO loops,
variables, or control flow — those belong to the target language. Your job
is to translate the user's request into a task graph made of `task` and
`component` declarations with `goal`, `input`, `output`, `constraint`,
`depends`, `uses`, `test`, and `success` fields.

## The 10 keywords (this is the entire surface)
    project      task         component
    goal         input        output
    constraint   depends      uses
    test         success

## Syntax rules
- Indentation is 4 spaces, Python-style.
- `#` starts a comment.
- Blank lines are ignored.
- Every task and component MUST have a `goal`.
- Names are CamelCase identifiers.
- `depends` and `uses` targets MUST be declared elsewhere in the same file.
- The graph must be acyclic.

## Field kinds
- Prose fields (one sentence per line): `goal`, `constraint`, `test`, `success`.
- Identifier fields (one CamelCase name per line): `input`, `output`, `depends`, `uses`.

## Canonical example
project InstagramClone

component Postgres
    goal
        Managed relational database.

component Database
    goal
        Durable storage for users, posts, and follows.
    uses
        Postgres

task Login
    goal
        Authenticate users securely.
    input
        email
        password
    output
        jwt_token
    constraint
        Under 300ms p95 latency.
    depends
        Database
    test
        Invalid password is rejected.
    success
        Valid credentials reach the feed.

## How to think
1. Pick a CamelCase project name.
2. Emit shared infrastructure as `component`s (databases, auth, queues) first.
3. Emit user-facing capabilities as `task`s.
4. Write ONE clear `goal` sentence per node.
5. Add `constraint`/`test`/`success` only when the user gave specifics — do
   NOT invent latency numbers, quotas, or SLAs the user did not state.
6. Wire dependencies. Fewer, sharper edges are better than many weak ones.
7. Do NOT write code. Do NOT explain. Output Quinny only."""


class PlannerError(Exception):
    """Raised when the planner cannot produce valid Quinny within max_retries."""


@dataclass
class PlanResult:
    project: Project
    source: str
    attempts: int


_FENCE_RE = re.compile(r"^\s*```[a-zA-Z0-9_]*\s*\n(.*?)\n\s*```\s*$", re.DOTALL)


def _strip_fences(text: str) -> str:
    """Remove markdown code fences if the model wrapped its output."""
    m = _FENCE_RE.match(text)
    return m.group(1) if m else text.strip()


def _extract_text(response: Any) -> str:
    parts = [b.text for b in response.content if getattr(b, "type", None) == "text"]
    return "\n".join(parts)


JSON_SYSTEM_PROMPT = """You are a Quinny plan designer. Emit a JSON object \
that describes the task graph.

## Concepts
`project` names the whole thing. Each `declaration` is either a `task`
(user-visible capability) or a `component` (shared infrastructure).

## Required fields
- `project`: CamelCase project name.
- `declarations`: list of nodes, each with:
  - `kind`: "task" or "component".
  - `name`: CamelCase identifier, globally unique.
  - `goal`: one sentence — what "done" means.

## Optional fields per declaration
- `constraint`, `test`, `success`: arrays of prose sentences (one per element).
- `input`, `output`, `depends`, `uses`: arrays of CamelCase names.
- `subtasks`, `subcomponents`: nested declarations (recursive).

## Rules
- Every `depends`/`uses` name MUST be declared elsewhere in the plan.
- The dependency graph MUST be acyclic.
- Add `constraint`/`test` only when the user specifies them — do NOT invent
  latency numbers, quotas, or SLAs.
- Prefer fewer, sharper edges over many weak ones.

Output ONLY the JSON object. No prose. No markdown fences."""


def plan_from_english_json(
    request: str,
    *,
    client: anthropic.Anthropic | None = None,
    model: str = "claude-opus-4-7",
    max_retries: int = 3,
    max_tokens: int = 4096,
    tracker: "UsageTracker | None" = None,
) -> PlanResult:
    """JSON-format planner. Uses Anthropic's structured-output enforcement
    (`output_config.format.json_schema`) so the response is guaranteed to
    conform to `PLAN_SCHEMA`. Semantic errors (unresolved refs, cycles) still
    go through the same repair loop.
    """
    if client is None:
        if not (os.environ.get("ANTHROPIC_API_KEY")
                or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
            raise PlannerError("ANTHROPIC_API_KEY is not set.")
        client = make_client()

    messages: list[dict[str, Any]] = [{"role": "user", "content": request}]
    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=JSON_SYSTEM_PROMPT,
            messages=messages,
            output_config={
                "format": {"type": "json_schema", "schema": PLAN_SCHEMA},
            },
            **thinking_kwargs(model),
        )
        if tracker is not None:
            tracker.record("planner", model, response)
        raw = _extract_text(response)

        try:
            project = json_to_ast(raw)
            build_graph(project)
            # Persist the pretty-printed JSON as the plan source, not the raw
            # (structured-output responses are already valid JSON, but we
            # want stable formatting for the cache file).
            source = ast_to_json(project)
            return PlanResult(project=project, source=source, attempts=attempt)
        except (JsonPlanError, GraphError, json.JSONDecodeError) as e:
            last_error = e
            messages.append({"role": "assistant", "content": raw})
            messages.append({
                "role": "user",
                "content": (
                    f"Your previous JSON plan failed validation with:\n"
                    f"    {e}\n\n"
                    f"Fix it and output only the corrected JSON object."
                ),
            })

    raise PlannerError(
        f"JSON planner failed after {max_retries} attempts. "
        f"Last error: {last_error}"
    )


def plan_from_english(
    request: str,
    *,
    client: anthropic.Anthropic | None = None,
    model: str = "claude-opus-4-7",
    max_retries: int = 3,
    max_tokens: int = 4096,
    tracker: "UsageTracker | None" = None,
    format: str = "quinny",
) -> PlanResult:
    """Translate an English request into a validated Quinny Project.

    `format="quinny"` (default) uses the indented DSL and text-based parsing.
    `format="json"` uses structured-output JSON via `PLAN_SCHEMA`.

    Both routes return the same `Project` AST — downstream generation is
    format-agnostic.
    """
    if format == "json":
        return plan_from_english_json(
            request, client=client, model=model, max_retries=max_retries,
            max_tokens=max_tokens, tracker=tracker,
        )

    if client is None:
        if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
            raise PlannerError(
                "ANTHROPIC_API_KEY is not set. Export it or pass an "
                "anthropic.Anthropic client explicitly."
            )
        client = make_client()

    messages: list[dict[str, Any]] = [{"role": "user", "content": request}]
    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=SYSTEM_PROMPT,
            messages=messages,
            **thinking_kwargs(model),
        )
        if tracker is not None:
            tracker.record("planner", model, response)
        raw = _extract_text(response)
        source = _strip_fences(raw)

        try:
            project = parse(source)
            build_graph(project)
            return PlanResult(project=project, source=source, attempts=attempt)
        except (QuinnyParseError, GraphError) as e:
            last_error = e
            messages.append({"role": "assistant", "content": raw})
            messages.append({
                "role": "user",
                "content": (
                    f"Your previous Quinny output failed compilation with:\n"
                    f"    {e}\n\n"
                    f"Fix it and output only the corrected Quinny source. "
                    f"No prose, no markdown fences."
                ),
            })

    raise PlannerError(
        f"Planner failed to produce valid Quinny after {max_retries} attempts. "
        f"Last error: {last_error}"
    )
