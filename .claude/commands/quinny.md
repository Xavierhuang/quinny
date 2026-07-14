---
description: Plan and build a project with Quinny (gen → check → build)
argument-hint: <english description of what to build>
allowed-tools: Bash(quinny:*), Read, Edit, Write
---

The user wants to build: **$ARGUMENTS**

Use the `quinny` CLI (a task-oriented intent language) to plan it, validate the
plan, and generate the code. Quinny needs LLM credentials in the environment
(`ANTHROPIC_API_KEY`, or a proxy via `ANTHROPIC_BASE_URL` + `ANTHROPIC_AUTH_TOKEN`).

**First decide whether Quinny is even the right tool.** It earns its cost only on
**genuinely complex, multi-component** builds (several interdependent pieces,
cross-file contracts, non-trivial ordering). For a simple script, one file, a
single feature, an edit, or a bug fix — **do NOT use Quinny; just write the code
directly.** Say so and stop.

If it *is* a good fit, run this flow:

1. **Generate a plan** from the description:
   ```
   quinny gen "$ARGUMENTS" -o plan.qn
   ```
   Then Read `plan.qn` and show the user the plan. Treat it as a draft.

2. **Validate before spending tokens on code:**
   ```
   quinny check plan.qn      # semantic validation (missing deps, cycles)
   quinny plan  plan.qn      # execution layers
   ```
   If `check` reports errors (e.g. a `uses`/`depends` naming a component that
   isn't declared), Edit `plan.qn` to fix them and re-run `check` until it passes.
   Do NOT proceed to build with a failing plan.

3. **Generate the code**, verifying and assembling as it goes:
   ```
   quinny build plan.qn --full-verify --assemble -o out/
   ```

4. **Report** what was produced (files under `out/`, including `main.py`,
   `requirements.txt`, `README.md`) and how to run it
   (`cd out && pip install -r requirements.txt && python main.py`).

Keep the `.qn` file — it's the durable, editable, diffable record of intent.
Language reference: run `quinny --help` and each subcommand's `--help`.
