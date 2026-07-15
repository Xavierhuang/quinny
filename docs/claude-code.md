# Using Quinny with Claude Code

Quinny is a normal CLI on your PATH, so [Claude Code](https://claude.com/claude-code)
can use it the moment it's installed — no plugin required. Its job is to
**verify** the code Claude writes against a contract, not to write code (Claude is
better at that alone). Three levels, cheapest first.

## 0. It already works (nothing to set up)

Because `quinny` is just a command, Claude Code runs it via Bash. The natural loop:

> "Build a shopping cart module. Use `quinny scaffold` to draft a contract for the
> logic, implement it, then `quinny verify` and fix until it passes."

Claude runs `quinny scaffold`, writes the code, runs `quinny verify`, and iterates
to green. `verify`/`scaffold` need LLM credentials in the environment
(`ANTHROPIC_API_KEY`, or `ANTHROPIC_BASE_URL` + `ANTHROPIC_AUTH_TOKEN`).
`check`/`graph`/`plan` and `verify --suite` need none.

## 1. A `/quinny` slash command

This repo ships a ready-made command at
[`.claude/commands/quinny.md`](../.claude/commands/quinny.md) that runs the whole
scaffold → implement → verify loop. Install it once, globally:

```bash
mkdir -p ~/.claude/commands
curl -fsSL https://raw.githubusercontent.com/Xavierhuang/quinny/main/.claude/commands/quinny.md \
  -o ~/.claude/commands/quinny.md
```

Then, in any Claude Code session:

```
/quinny a checkout with per-item quantity, tax, and a discount code that rejects invalid percentages
```

It scopes the *logic* (not the UI), contracts it, implements, verifies to green,
and — importantly — declines when there's no correctness-critical logic to gate.

## 2. Teach Claude *when* to reach for Quinny (paste-in CLAUDE.md)

Add this to your project's `CLAUDE.md` (or `~/.claude/CLAUDE.md`) so Claude uses
Quinny at the right time:

```markdown
## Quinny (verify correctness-critical logic)

`quinny` is installed. It VERIFIES code against acceptance criteria — it does not
write code. Use it ONLY where correctness matters: pricing, cart/checkout math,
business rules, state machines, validation, auth, parsing, calculations. Do NOT
use it for UI, styling, static pages, simple scripts, or one-off edits.

When it fits:
1. `quinny scaffold "<what to build>" -o <dir>` — draft a `.qn` contract for the
   logic + a module stub. (`--lang js` / `--lang swift` for those targets.)
2. Implement the module (write the real code).
3. `quinny verify <dir>/<name>.qn <dir>` — fix your code until all gating criteria pass.
4. `quinny verify … --emit <name>_contract_test.py` and commit it for CI.

If verify can't reach a model, note it and keep building — never let it block.
```

## 3. In CI

The emitted suite is a plain test file — commit it and gate every push with no
model in the loop. See [docs/ci.md](ci.md) for the ready-to-copy GitHub Action.
