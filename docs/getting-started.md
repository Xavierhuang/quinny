# Getting started with Quinny

This walks you from install to a generated, running project in ~10 minutes.

## 1. Install

```bash
pip install quinny        # or: pip install -e .  from a clone
quinny --help
```

## 2. Write your first plan

A Quinny program describes **what** to build, not how. Create `todo.qn`:

```
project TodoService

component Store
    goal
        In-memory store mapping ids to todo items.
    output
        Store

task AddTodo
    goal
        Add a todo item and return its id.
    uses
        Store
    input
        text
    output
        id
    success
        The new id is retrievable from the store.

task ListTodos
    goal
        Return all todo items, newest first.
    uses
        Store
    output
        items
```

Notes:
- The file starts with exactly one `project`.
- `task` = a unit of work; `component` = an architectural building block.
- `uses` / `depends` are **edges** — the target must be a name declared in the
  same file. `uses` is for components you build on; `depends` for ordering.
- `goal` is required on every task/component. Everything else is optional but
  makes the generated code better.

## 3. Validate before you spend a token

```bash
quinny check todo.qn      # parses + validates the graph
quinny plan  todo.qn      # shows execution layers
quinny graph todo.qn      # shows the task graph
```

`check` is where Quinny earns its keep: if `AddTodo` said `uses Storee` (a typo),
you'd get a **semantic error here** — for free — instead of a broken import after
the LLM already wrote the code. Fix the `.qn` and re-run until `check` passes.

## 4. Generate the code

`build` needs LLM credentials (see the README's *Credentials* section):

```bash
export ANTHROPIC_API_KEY=sk-...          # or a proxy: ANTHROPIC_BASE_URL + ANTHROPIC_AUTH_TOKEN
quinny build todo.qn --full-verify --assemble -o out/
```

What happens:
1. **Types** — a shared-types file is synthesized first.
2. **Nodes** — each `task`/`component` is generated in dependency order.
3. **Verify** — each file is checked (syntax + import; `--full-verify` also runs it).
4. **Repair** — failures are fed back to the model for up to `--max-repair` rounds.
5. **Assemble** — `--assemble` emits `main.py`, `requirements.txt`, `README.md`.

Then:

```bash
cd out && python main.py
```

## 5. From English, if you prefer

Skip writing the `.qn` by hand:

```bash
quinny gen "a URL shortener with base62 ids and an in-memory store" -o url.qn
quinny check url.qn        # always review + validate the generated plan
quinny build url.qn --full-verify --assemble -o out/
```

Treat `gen`'s output as a **draft** — read it, edit it, `check` it. The `.qn` is
small and human-readable precisely so you can.

## Next

- [Language reference](LANGUAGE_SPEC.md) — every keyword + the grammar.
- [AI prompt kit](AI_PROMPT.md) — teach any LLM to write valid Quinny.
- Run `quinny build --help` for all the per-stage flags.
