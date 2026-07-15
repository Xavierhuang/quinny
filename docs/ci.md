# Running `quinny verify` in CI

The reliable way to gate a repo on an acceptance contract is the
**emit → review → run** flow. You generate the test suite once (with an LLM),
read it, commit it, and from then on CI runs it deterministically with **no model
and no API key**.

## 1. Generate and commit the contract suite (once, locally)

```bash
quinny verify spec.qn ./src --emit contract_test.py
# open contract_test.py, sanity-check the generated tests, then:
git add spec.qn contract_test.py && git commit -m "Add acceptance contract"
```

`contract_test.py` is now a normal, reviewed pytest file. It's the enforceable
form of `spec.qn`'s `test` criteria.

## 2. Add the GitHub Action

`.github/workflows/contract.yml`:

```yaml
name: Acceptance contract
on: [push, pull_request]

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install quinny
        run: pip install quinny
      - name: Verify the implementation against the contract
        # --suite re-runs the committed suite: deterministic, NO LLM, NO secret.
        run: quinny verify spec.qn ./src --suite contract_test.py
```

`quinny verify` exits non-zero if any gating (`test`) criterion fails, so the job
goes red exactly when the implementation drifts from the spec — whether a human,
Claude Code, or Cursor wrote the drift.

## 3. Re-generate only when the spec changes

When you edit `spec.qn`, regenerate and re-review:

```bash
quinny verify spec.qn ./src --emit contract_test.py
git add spec.qn contract_test.py && git commit -m "Update contract"
```

Everyday CI never calls a model — it just runs the committed suite. You pay for
the LLM once per spec change, not once per push.

## Notes

- Concrete `test` lines gate the build; `success` summaries are advisory.
- Reliability of the generated gate is measured in
  [`benchmarks/verify_usability.py`](../benchmarks/verify_usability.py):
  0 false-passes, 0 false-fails, 100% accuracy against known-defect implementations.
