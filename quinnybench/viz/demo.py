"""Fabricate a demo run so the site can be previewed without spending API calls.

    python -m viz.demo

Writes `results/demo/index.json` with plausible per-model scores across every
task, for all three tracks (md, qn, auth). Also drops fabricated per-(model,task)
artifacts (impl.py or contract.qn) so drilldown pages have something to render.

Clearly labeled — NEVER commit this as a real benchmark result. Numbers, code,
and pass/fail assignments are ALL fake; the seed is fixed for stability.
"""
from __future__ import annotations

import json
import pathlib
import random
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from runner.run import TASKS_DIR, RESULTS_DIR, MODE_TAG  # noqa: E402

DEMO_MODELS = [
    # (provider, model, base skill 0.0-1.0)
    ("anthropic",  "claude-opus-4-7",      0.95),
    ("anthropic",  "claude-sonnet-4-6",    0.90),
    ("openai",     "gpt-4o",               0.82),
    ("openai",     "o3",                   0.88),
    ("google",     "gemini-2.5-pro",       0.85),
    ("xai",        "grok-4",               0.78),
    ("deepseek",   "deepseek-chat",        0.72),
    ("openrouter", "moonshotai/kimi-k2",   0.80),
]

# Per-track skill adjustment — reflects the hypothesis being tested:
# reading a Quinny contract *helps* (small boost), authoring one is harder
# (small penalty). Weaker models widen the gap.
TRACK_BIAS = {
    "code-from-md":  0.0,
    "code-from-qn": +0.05,
    "qn-from-md":   -0.15,
}

_DEMO_CODE_BANNER = (
    "# ────────────────────────────────────────────────────────────────\n"
    "# DEMO — this file was NOT produced by a real model call.\n"
    "# viz/demo.py copies the reference so the drilldown page has\n"
    "# something to render. Real runner/run.py output replaces this.\n"
    "# ────────────────────────────────────────────────────────────────\n\n"
)

_DEMO_QN_BANNER = (
    "# DEMO — this .qn file was NOT authored by a real model call.\n"
    "# It's a copy of the reference contract, staged so the drilldown\n"
    "# page has content. Real runner/run.py output replaces this.\n"
)


def _test_names(suite_path: pathlib.Path) -> list[str]:
    return re.findall(r"^def (test_\w+)", suite_path.read_text(), re.MULTILINE)


AUTH_TESTS = [
    "test_quinny_check_accepts",
    "test_has_task_block",
    "test_has_multiple_test_criteria",
    "test_module_constraint_matches",
    "test_entity_name_constraint_matches",
]


def _fake_result(task_id, category, tests, provider, model, mode, skill, rng):
    p = max(0.0, min(1.0, skill + rng.uniform(-0.10, 0.05) + TRACK_BIAS[mode]))
    passed, failed = [], []
    for t in tests:
        (passed if rng.random() < p else failed).append(t)
    return {
        "task": task_id,
        "category": category,
        "provider": provider,
        "model": model,
        "mode": mode,
        "status": "graded",
        "criteria_total": len(tests),
        "criteria_passed": len(passed),
        "criteria_failed": len(failed),
        "criteria_errored": 0,
        "passed": passed, "failed": failed, "errored": [],
    }


def main():
    tasks = []
    for tdir in sorted(TASKS_DIR.iterdir()):
        meta = json.loads((tdir / "meta.json").read_text())
        code_tests = _test_names(tdir / "suite.py")
        ref_code = (tdir / "reference" / "impl.py").read_text()
        ref_qn = (tdir / "contract.qn").read_text()
        tasks.append((meta["id"], meta["category"], code_tests, ref_code, ref_qn))

    rng = random.Random(42)
    out = RESULTS_DIR / "demo"
    out.mkdir(parents=True, exist_ok=True)

    results = []
    for provider, model, skill in DEMO_MODELS:
        model_rng = random.Random(hash((provider, model)) & 0xFFFFFFFF)
        model_skill = max(0.4, min(0.99, skill + model_rng.uniform(-0.03, 0.03)))
        for task_id, cat, code_tests, ref_code, ref_qn in tasks:
            for mode in ("code-from-md", "code-from-qn", "qn-from-md"):
                tests = AUTH_TESTS if mode == "qn-from-md" else code_tests
                r = _fake_result(task_id, cat, tests, provider, model, mode,
                                 model_skill, rng)
                results.append(r)

                tag = MODE_TAG[mode]
                d = out / task_id / f"{provider}--{model}--{tag}"
                d.mkdir(parents=True, exist_ok=True)
                if mode == "qn-from-md":
                    (d / "contract.qn").write_text(_DEMO_QN_BANNER + ref_qn)
                else:
                    (d / "impl.py").write_text(_DEMO_CODE_BANNER + ref_code)

    (out / "index.json").write_text(json.dumps(results, indent=2))
    print(f"demo run → {out / 'index.json'}")
    print(f"  {len(DEMO_MODELS)} models × {len(tasks)} tasks × 3 tracks = "
          f"{len(results)} rows")
    print("Numbers, code, and pass/fail are ALL FABRICATED for preview.")


if __name__ == "__main__":
    main()
