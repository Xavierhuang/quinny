# Add-your-library harness

**Point Quinny's verify gate at a library YOU pick.** No self-authored
fixtures, no synthetic bug shapes — just a real, published package and
whatever documented behavior you want to gate.

The harness (`benchmarks/verify_real_oss.py`) auto-discovers every
subdirectory here that has a `manifest.py` and runs it. Adding your
library is 5 files and no code changes to the harness itself.

## Why contribute

Every existing `verify_*` benchmark exercises code the Quinny author
wrote — a critic can reasonably say "of course the gate catches bugs
you knew to write." Fixtures under `real_oss/` close that gap. Each new
library that lands here is one more independent data point for
"the gate works on code we didn't touch."

If you find a genuine gap (a defect verify misses, or a false-FAIL on
correct code), that's the most useful contribution of all — please
open an issue with the fixture.

## The 5-step recipe

Say you want to add [`sortedcontainers`](https://github.com/grantjenks/python-sortedcontainers).

**1. Make the fixture directory**

```
benchmarks/fixtures/real_oss/sortedcontainers/
```

**2. Write `spec.qn`** — the acceptance criteria for the library's
documented API. One `test` block per criterion, each on ONE line. See
`cachetools/spec.qn` for the pattern:

```qn
project SortedContainersContract

component SortedList
    goal
        Documented behavior of sortedcontainers.SortedList exposed
        via a thin wrapper module.

task ListBehavior
    goal
        Insert, index, and membership guarantees.
    depends
        SortedList
    test
        With s=make_list(): add(s, 3); add(s, 1); add(s, 2); at(s, 0) equals 1.
    ...
```

**3. Write `pristine_wrapper.py`** — a thin module that exposes the
functions the spec talks about, forwarding to the real library. This
should be all-PASS by construction. Example:

```python
from sortedcontainers import SortedList
def make_list():        return SortedList()
def add(s, v):          s.add(v)
def at(s, i):           return s[i]
def contains(s, v):     return v in s
```

**4. Write `mutated_wrapper.py`** — SAME wrapper, but with ONE narrowly-
injected bug that breaks EXACTLY ONE criterion in your spec. Keep the
mutation surgical (see `cachetools/mutated_wrapper.py` for what
"surgical" looks like — it uses the same library, just calls a subtly-
wrong method). A too-broad mutation breaks multiple criteria and
loses the "surgical FAIL" story.

**5. Write `manifest.py`** — declares variants + ground truth:

```python
LIBRARY = "sortedcontainers"
DESCRIPTION = "sorted list/dict/set collections"
IMPORT_CHECK = "sortedcontainers"

VARIANTS = {
    "pristine": "pristine_wrapper.py",
    "mutated_wrong_insert_order": "mutated_wrapper.py",
}

# Which criterion indices should PASS per variant?
GROUND_TRUTH = {
    "pristine":                    {i: True for i in range(1, 7)},
    "mutated_wrong_insert_order":  {1: False, 2: True, 3: True,
                                    4: True,  5: True, 6: True},
}
```

## Running it

```sh
# One-time: install the library
pip install sortedcontainers

# Emit the pytest suite (~1 API call)
QUINNY_MODEL=claude-haiku-4-5 python benchmarks/verify_real_oss.py \
    --library sortedcontainers --emit

# Review benchmarks/fixtures/real_oss/sortedcontainers/suite.py
# Commit it. Now it runs offline forever:
python benchmarks/verify_real_oss.py --library sortedcontainers \
    --suite benchmarks/fixtures/real_oss/sortedcontainers/suite.py

# Or run every library at once:
python benchmarks/verify_real_oss.py
```

## What "success" looks like

For each library you add:

```
=== sortedcontainers ===
variant                      criteria row   truth          verdict
------------------------------------------------------------------------------
pristine                     PPPPPP         PPPPPP         OK
mutated_wrong_insert_order   FPPPPP         FPPPPP         OK
------------------------------------------------------------------------------
False-PASS (missed a real-library defect): 0
False-FAIL (cried wolf on real code):      0
```

Two things this proves at once:
- **No false-FAIL on real shipping code** — the gate doesn't cry wolf.
- **Surgical FAIL on the mutation** — exactly the criterion your
  mutation targets fails, nothing else.

If either of those fails on your library, that's a real finding.
Please open an issue.

## Currently included

- **cachetools** — LRU + TTL caches. 8/8 PASS pristine; surgical FAIL
  on an LRU-recency mutation. See `cachetools/`.

## Ideas for good candidates

- `sortedcontainers` (sorted list/dict/set)
- `tinydb` (JSON-backed document store — transactional semantics)
- `python-jsonschema` (schema validation)
- `python-diff-match-patch` (Google's diff library)
- `arrow` or `pendulum` (date/time arithmetic)
- `parsy` / `lark` (parser combinator / grammar)
- any library whose documented API has behavior you can pin down in
  one line per criterion
