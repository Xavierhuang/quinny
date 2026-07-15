---
description: Spec + verify the correctness-critical logic with Quinny (scaffold → implement → verify)
argument-hint: <english description of what to build>
allowed-tools: Bash(quinny:*), Read, Edit, Write
---

The user wants to build: **$ARGUMENTS**

Use Quinny to put a **verifiable contract** around the part of this where
correctness matters, then hold your own code to it. Quinny does NOT write the
code — you do; it verifies it. `quinny` is on your PATH (also `$QUINNY_BIN`).

**First decide whether there's correctness-critical logic here at all.** Quinny is
for pricing, cart/checkout math, business rules, state machines, validation, auth,
parsing, calculations — anywhere a silent bug is expensive. It is NOT for UI,
layout, styling, static pages, simple scripts, or one-off edits — skip it there and
just build.

If there IS real logic, run this loop:

1. **Draft the contract + a stub** for the logic (not the whole app):
   ```
   quinny scaffold "$ARGUMENTS" -o <dir>
   ```
   It scopes the verifiable logic, writes a `.qn` contract with acceptance
   criteria, and stubs the module. Read the `.qn` and show the user the criteria.
   (Add `--lang js` or `--lang swift` to target those instead of Python.)

2. **Implement the module** — write the real code to satisfy the contract.

3. **Verify and iterate:**
   ```
   quinny verify <dir>/<name>.qn <dir>
   ```
   It reports per-criterion PASS/FAIL. Keep fixing your code until **all gating
   (test) criteria pass**. Show the user the final green result.

4. **Lock it into the repo** so it re-runs deterministically with no model:
   ```
   quinny verify <dir>/<name>.qn <dir> --emit <name>_contract_test.py
   ```
   Commit the `.qn` + the emitted suite; add it to CI (see the project's docs/ci.md).

Build the rest of the app around that verified core. Rationale: agents write code
that *looks* done but misses edge cases — `verify` turns "is it correct?" into an
objective command, and the contract keeps catching regressions after you move on.
If verify can't reach a model (no credentials), say so and continue building — never
let a verification hiccup block the task.
