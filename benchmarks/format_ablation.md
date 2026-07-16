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

## Verdict

| Axis | In favor of `.qn`? |
|---|---|
| Output / gate quality | **No** — dead wash across all four formats |
| Catching malformed specs | Beats Markdown; ties JSON |
| Semantic validation (deps/cycles) built in | Yes, uniquely — but it's robustness |

The reviewer's question — does the *language* improve *output*? — answer: **no.**
Where `.qn` legitimately wins is catching bad specs before they ship a broken
gate, with validation included. A narrow ergonomic/safety win, not a results win.
Consistent with the rest of the benchmarks: the value is `verify`, not the syntax.
