"""Rescore a saved run against the current suites — no API calls.

    python -m runner.rescore results/2026-07-21-1830/

Walks every `<task>/<provider--model--tag>/` under the given run dir.
For code tracks (`md`, `qn`) re-runs the current pytest suite against the
saved `impl.py`. For the authoring track (`auth`) re-runs the structural
grader against the saved `contract.qn`. Legacy dirs without a `--tag` suffix
(pre-3-track runs) are treated as `md`.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

from .run import run_pytest, grade_qn_contract, TASKS_DIR

_TAG_TO_MODE = {"md": "code-from-md", "qn": "code-from-qn", "auth": "qn-from-md"}


def _split_dir_name(name: str) -> tuple[str, str, str]:
    """`provider--model--tag` → (provider, model, tag).

    Legacy: `provider--model` (no tag) → tag defaults to 'md'.
    """
    parts = name.rsplit("--", 1)
    if len(parts) == 2 and parts[1] in _TAG_TO_MODE:
        head, tag = parts
    else:
        head, tag = name, "md"
    provider, _, model = head.partition("--")
    return provider, model, tag


def rescore_run(run_dir: pathlib.Path) -> list[dict]:
    results = []
    for task_dir in sorted(p for p in run_dir.iterdir() if p.is_dir()):
        task_id = task_dir.name
        meta_path = TASKS_DIR / task_id / "meta.json"
        if not meta_path.exists():
            print(f"skip {task_id}: task no longer exists in tasks/", file=sys.stderr)
            continue
        meta = json.loads(meta_path.read_text())
        suite = TASKS_DIR / task_id / "suite.py"

        for pm_dir in sorted(p for p in task_dir.iterdir() if p.is_dir()):
            provider, model, tag = _split_dir_name(pm_dir.name)
            mode = _TAG_TO_MODE.get(tag, "code-from-md")

            if mode in ("code-from-md", "code-from-qn"):
                if not (pm_dir / "impl.py").exists() or not suite.exists():
                    continue
                grade = run_pytest(suite, pm_dir)
            else:  # qn-from-md
                if not (pm_dir / "contract.qn").exists():
                    continue
                grade = grade_qn_contract(pm_dir / "contract.qn", meta)

            total = len(grade["passed"]) + len(grade["failed"]) + len(grade["errored"])
            res = {
                "task": task_id,
                "category": meta.get("category", "uncategorized"),
                "provider": provider,
                "model": model,
                "mode": mode,
                "status": "graded",
                "criteria_total": total,
                "criteria_passed": len(grade["passed"]),
                "criteria_failed": len(grade["failed"]),
                "criteria_errored": len(grade["errored"]),
                "passed": grade["passed"],
                "failed": grade["failed"],
                "errored": grade["errored"],
            }
            (pm_dir / "result.json").write_text(json.dumps(res, indent=2))
            results.append(res)
            print(f"{task_id} {provider}:{model} [{tag}]  "
                  f"{res['criteria_passed']}/{res['criteria_total']}")

    (run_dir / "index.json").write_text(json.dumps(results, indent=2))
    return results


def cli(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run_dir", type=pathlib.Path)
    args = p.parse_args(argv)
    rescore_run(args.run_dir)


if __name__ == "__main__":
    cli()
