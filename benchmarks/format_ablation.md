# Does the `.qn` language improve output vs md / json / yaml?

The honest, evidence-backed answer: **no for output quality; a narrow yes for
catching malformed specs.** This documents the eval so the claim is reproducible.

## Method

Hold everything constant except the FORMAT the acceptance criteria are authored
in. For each task, take the same criteria and render them four ways — `.qn`,
JSON array, YAML, Markdown numbered list — then run the identical
`build_suite` → `run_suite` pipeline (same weak model, Haiku) and measure:

- **extraction fidelity** — does parsing the format back recover every criterion?
- **pass-on-correct** — does the generated suite false-alarm on a known-correct impl?
- **catches-injected-bug** — does it fail the one criterion covering an injected bug?

Run: `QUINNY_REF_DIR=<dir with textkit.py, cron.py> python benchmarks/format_ablation.py`

## Result 1 — output/gate quality is a dead wash

```
                 extract   pass_on_correct   catches_injected_bug
textkit  .qn      12/12       100%              1/12
         json     12/12       100%              1/12
         yaml     12/12       100%              1/12
         md       12/12       100%              1/12
cron     .qn       8/8         100%              1/8
         json      8/8         100%              1/8
         yaml      8/8         100%              1/8
         md        8/8         100%              1/8
```

Identical to the digit across all four formats. In Quinny's pipeline the criteria
become plain strings BEFORE the suite is generated, so the format is gone by the
time output is produced. **The demonstrated value — executable verification — is
format-neutral. The syntax is ergonomics, not a source of better results.**

## Result 2 — the one axis that favors structure: catching malformed specs

Author intends 4 criteria; one is fat-fingered:

```
  qn    CAUGHT (QuinnyParseError)   — author is told
  json  CAUGHT (JSONDecodeError)    — author is told
  yaml  SILENT → 3/4  (dropped, no error)   [note: naive regex parser, not a YAML lib]
  md    SILENT → 3/4  (dropped, no error)
```

Strict-parser formats (`.qn`, JSON) catch the mistake; free-text Markdown silently
drops the criterion — which ships a WEAKER GATE with nobody the wiser. This is a
real robustness win of `.qn` over Markdown, but it TIES JSON, not beats it.

## Result 3 — `.qn`'s one unique edge: built-in semantic validation

```
.qn   undefined dependency → CAUGHT: 'A' references unknown name 'Nonexistent'.
.qn   dependency cycle       → CAUGHT: Dependency cycle detected: A -> B -> A.
json  (flat criteria list)   → parses clean; deps aren't modeled → nothing to validate
```

`.qn` models structure (components + deps) and validates it out of the box —
undefined refs, cycles, missing fields — which a flat criteria-list can't even
represent. You could replicate this with JSON + a schema + a custom graph checker;
`.qn` ships it. Still robustness, not output.

## Result 4 — the OVERALL result (does a bug ship?)

The narrow question is "code quality of one artifact." The broader, fairer reading
is: does the *format* change the *overall outcome* — does a real bug ship? It can,
through one channel: if a format silently drops a fat-fingered criterion, its gate
has no test for that behavior, so a bug there passes the gate.

Experiment (`benchmarks/end_to_end.py`): 12 textkit criteria, one authoring slip
that Markdown drops (a sub-bulleted line) but `.qn` preserves. Build the gate from
each, run it against an impl whose `roman()` is broken — the slipped criterion's
behavior.

```
                             OVERALL RESULT over 5 trials
  .qn gate caught the bug:   5/5   (roman test present → fails the broken impl)
  md  gate caught the bug:   0/5   (criterion silently dropped → no test → bug ships)
```

Fully reproducible. The Markdown miss is **structural and deterministic** (the
criterion is dropped by pure parsing, so no roman test can exist); the `.qn` catch
was 5/5 across LLM suite-gen variance (freeze it with emit→`--suite` for a hard
guarantee). So on the broad reading, **`.qn` yields a strictly better overall
result than Markdown when authoring is imperfect** — a shipped bug vs a caught one
— but purely via spec integrity (not losing your criteria), it **ties JSON**, and
it **vanishes on clean authoring** (no dropped criterion → same outcome).

## Verdict

| Axis | In favor of `.qn`? |
|---|---|
| Output / gate quality (code of one artifact) | **No** — dead wash across all four formats |
| Overall result with imperfect authoring | **Yes vs Markdown** (bug ships vs caught, 5/5); **ties JSON** |
| Catching malformed specs | Beats Markdown; ties JSON |
| Semantic validation (deps/cycles) built in | Yes, uniquely — but it's robustness |

Two readings of "does the language improve output":
- **Code quality of one artifact, given the criteria** → **no**, dead wash. The
  language does not make the model write better code.
- **The overall result, with real (imperfect) authoring** → **yes vs Markdown**
  (5/5: a bug ships under Markdown, caught under `.qn`), **tie with JSON**. The win
  is spec integrity — not silently losing your criteria — plus built-in semantic
  validation, and it disappears when authoring is clean.

So the language's value is a **safety net for imperfect humans**, not model
cleverness. Consistent with the rest of the benchmarks: the leverage is `verify`
and a complete, preserved contract — not the syntax itself.
