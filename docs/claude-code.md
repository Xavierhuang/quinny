# Using Quinny with Claude Code

Quinny is a normal CLI on your PATH, so [Claude Code](https://claude.com/claude-code)
can use it the moment it's installed — no plugin required. There are three levels
of integration, cheapest first.

## 0. It already works (nothing to set up)

Because `quinny` is just a command, Claude Code can run it via Bash. In any
project, ask:

> "Use `quinny` to plan and build a URL shortener with base62 ids."

Claude will run `quinny gen`, `quinny check`, and `quinny build` on its own. This
is the zero-config path — the same way it already uses `git`, `jq`, or `pytest`.

Quinny's `gen`/`build` need LLM credentials in the environment
(`ANTHROPIC_API_KEY`, or a proxy via `ANTHROPIC_BASE_URL` + `ANTHROPIC_AUTH_TOKEN`).
Everything before them (`parse`/`check`/`graph`/`plan`) needs no credentials.

## 1. A `/quinny` slash command

This repo ships a ready-made command at
[`.claude/commands/quinny.md`](../.claude/commands/quinny.md). Install it once,
globally:

```bash
mkdir -p ~/.claude/commands
curl -fsSL https://raw.githubusercontent.com/Xavierhuang/quinny/main/.claude/commands/quinny.md \
  -o ~/.claude/commands/quinny.md
```

Then, in any Claude Code session:

```
/quinny a task queue with a Redis-backed store, a worker pool, and retry/backoff
```

It runs the full gen → check (fix loop) → build flow, and — importantly — it will
**decline** and tell you to just write the code directly when the task is too
simple to be worth Quinny's cost.

## 2. Teach Claude *when* to reach for Quinny (paste-in CLAUDE.md)

Add this block to your project's `CLAUDE.md` (or `~/.claude/CLAUDE.md` for all
projects) so Claude reaches for Quinny at the right time and writes valid `.qn`:

```markdown
## Quinny (intent-language planner)

`quinny` is installed. Use it ONLY for genuinely complex, multi-component builds
— several interdependent pieces, cross-file contracts, non-trivial ordering.
For simple scripts, single features, edits, or bug fixes, write the code directly;
Quinny would cost more tokens for no benefit.

When it fits:
1. `quinny gen "<description>" -o plan.qn` — draft a plan; review/edit it.
2. `quinny check plan.qn` — validate (missing deps, cycles) BEFORE generating code.
   Fix plan.qn and re-run until it passes.
3. `quinny build plan.qn --full-verify --assemble -o out/` — generate, verify, assemble.

The `.qn` file is the durable, diffable record of intent — keep it in the repo.
To hand-write a plan, see the syntax guide the project links from docs/AI_PROMPT.md.
```

The full syntax primer an LLM needs to author `.qn` by hand lives in
[`docs/AI_PROMPT.md`](AI_PROMPT.md); the language reference is
[`docs/LANGUAGE_SPEC.md`](LANGUAGE_SPEC.md).

## 3. (Optional / future) An MCP server

A `quinny mcp` stdio server exposing `check`/`plan`/`build` as structured tools —
`claude mcp add quinny -- quinny mcp` — is not implemented yet. Levels 0–2 cover
the common cases without it. Track it in the issues if you want it.
