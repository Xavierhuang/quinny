# Teaching an LLM to write Quinny

You have four progressively stronger options. All of them work; pick the
cheapest one that gets you the reliability you need.

| Stage | Cost | Reliability | When to use |
|-------|------|-------------|-------------|
| 1. Prompt only | free | ~90% | Prototyping, day 1 |
| 2. Grammar-constrained decoding | free | ~100% syntax | Once you have real users |
| 3. Fine-tune | $$ | Higher quality plans | Once you have ≥1k good examples |
| 4. RL from compiler feedback | $$$ | Best | Once verifier is solid |

You almost certainly want Stage 1 today.

## Stage 1 — System prompt (copy this)

Drop this straight into the `system` message of Claude / GPT / any capable
LLM. It teaches the language in-context.

```
You are a Quinny engineer. Quinny is an executable specification language.
Output ONLY Quinny source — no prose, no markdown fences, no explanations.

## Quinny in one paragraph
A Quinny file describes WHAT should be built, not HOW. It has NO loops,
variables, or control flow — those belong to the target language. Your job
is to translate the user's request into a task graph made of `task` and
`component` declarations with `goal`, `input`, `output`, `constraint`,
`depends`, `uses`, `test`, and `success` fields.

## Syntax rules (all 10 keywords)
    project      task         component
    goal         input        output
    constraint   depends      uses
    test         success

Indentation is 4 spaces, Python-style. `#` starts a comment. Blank lines
are ignored. Every task and component MUST have a `goal`. Names are
CamelCase identifiers. `depends`/`uses` targets MUST be declared elsewhere
in the same file. The graph must be acyclic.

## Field rules
- `goal`, `constraint`, `test`, `success`: one prose sentence per line.
- `input`, `output`, `depends`, `uses`: one identifier per line.

## Canonical example
project InstagramClone

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
1. Identify the top-level project name.
2. Find shared infrastructure — emit those as `component`s first.
3. Find user-facing capabilities — emit those as `task`s.
4. For each, write ONE `goal` sentence. Then add constraints only if the
   user gave you specifics; do NOT invent latency numbers.
5. Wire dependencies. Prefer fewer, sharper edges over many weak ones.
6. Do NOT write code. Do NOT explain. Output Quinny only.
```

## Stage 2 — Grammar-constrained decoding

The Lark grammar (`quinny/grammar.lark`) is the source of truth. Convert it
to whatever constrained-decoding format your runtime accepts:

- **Outlines / LM Format Enforcer** — accept Lark directly.
- **llama.cpp** — convert to GBNF.
- **Anthropic / OpenAI** — no server-side grammar yet; wrap generation in
  `parse()` and rejection-sample on `QuinnyParseError`.

A robust runtime loop:

```python
from quinny import parse, build_graph, QuinnyParseError, GraphError

for attempt in range(3):
    source = llm.complete(system=SYSTEM_PROMPT, user=user_request)
    try:
        project = parse(source)
        build_graph(project)  # semantic check
        return project
    except (QuinnyParseError, GraphError) as e:
        user_request += f"\n\n# Your previous output failed: {e}. Fix it."
```

## Stage 3 — Fine-tuning dataset

You need triples:

```
(English requirement, Quinny source, generated code)
```

Bootstrap it cheaply:

1. Prompt Claude with the Stage 1 prompt over 500 English requests you
   already have (issues, PRDs, Slack threads, etc.).
2. Filter to only those whose Quinny **passes `quinny check`** — that's
   your syntactic gate.
3. Manually score 100 for quality; keep the top 60%.
4. Fine-tune an open model (Qwen, Llama) on `(English → Quinny)` and a
   second head on `(Quinny → Python/Swift/…)`.

## Stage 4 — RL from compiler feedback

The verifier is your reward model. A rollout is:

1. English → LLM → Quinny.
2. `quinny check` — reject on parse/graph errors (reward 0).
3. Code generator → target-language source.
4. Run the generated code's own tests → reward = fraction passing.
5. Reward high if all constraints from the Quinny source are also met
   (latency, size, etc. — measurable ones).

Optimize with GRPO / DPO on paired good/bad rollouts.

## What NOT to do

- **Don't** train from scratch. Modern LLMs learn Quinny in-context.
- **Don't** invent extra keywords in prompts. Ten is the whole surface.
- **Don't** let the model output code inside Quinny. The whole point is
  separation of intent from implementation.
