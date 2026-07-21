"""QuinnyBench runner.

    python -m runner.run --provider anthropic --model claude-opus-4-7 --mode code-from-md

Three prompt/grading tracks:

  code-from-md   Send prompt.md to the model. Grade the returned `impl.py`
                 with the task's frozen pytest suite. This is HumanEval-style.

  code-from-qn   Send `contract.qn` (verbatim, wrapped) to the model. Grade
                 the returned `impl.py` with the same pytest suite. Measures
                 whether reading a Quinny contract helps a model produce
                 spec-compliant code.

  qn-from-md     Send `prompt.md` with an "author a Quinny contract" wrapper.
                 Grade the returned `contract.qn` STRUCTURALLY (parses,
                 has a task, has criteria, module + entity constraints).

Only track code-from-* runs `impl.py`; qn-from-md grades an authored contract.
The grader is deterministic (pytest / static checks) — no LLM in the
verification path.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

from .providers import get as get_provider

ROOT = pathlib.Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT / "tasks"
RESULTS_DIR = ROOT / "results"

MODES = ("code-from-md", "code-from-qn", "qn-from-md")
MODE_TAG = {"code-from-md": "md", "code-from-qn": "qn", "qn-from-md": "auth"}


# ---------- prompt building ----------

def build_prompt(mode: str, task_dir: pathlib.Path) -> str:
    """Return the full text sent to the model for this (mode, task)."""
    if mode == "code-from-md":
        return (task_dir / "prompt.md").read_text()

    if mode == "code-from-qn":
        contract = (task_dir / "contract.qn").read_text().rstrip() + "\n"
        return (
            "Below is a Quinny contract (a `.qn` file) formalizing the acceptance "
            "criteria for a Python module you must implement.\n\n"
            "Read every constraint under `constraint`, every case under `test`, and "
            "the `success` criterion. Then write the code.\n\n"
            "Respond with ONLY the contents of `impl.py`, in a single fenced Python "
            "code block. No explanation.\n\n"
            "```qn\n" + contract + "```\n"
        )

    if mode == "qn-from-md":
        md = (task_dir / "prompt.md").read_text()
        # Strip the final "Respond with only the contents of impl.py…" instruction
        # so our new instruction doesn't conflict with it.
        md = re.sub(
            r"\n*Respond with \*\*only\*\* the contents.*?No explanation\.\s*$",
            "", md, flags=re.DOTALL,
        )
        return (
            md.rstrip() + "\n\n---\n\n"
            "Instead of writing code, author a **Quinny contract** — the `.qn` file "
            "that formalizes the acceptance criteria above. Include:\n"
            "  - a `task <Name>` block with a `goal` line;\n"
            "  - `constraint` lines that pin the module filename and the exported "
            "function or class name (mirroring the interface above);\n"
            "  - a `test` block enumerating every concrete case;\n"
            "  - a `success` criterion.\n\n"
            "Respond with ONLY the contract file's contents, in a single fenced code "
            "block (any language tag or none). No explanation.\n"
        )

    raise ValueError(f"unknown mode: {mode}")


# ---------- output extraction ----------

_CODE_FENCE = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.DOTALL)
_ANY_FENCE = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)


def extract_output(reply: str, mode: str) -> str:
    """Pull the first relevant fenced block from the model reply.

    For code modes, prefer a Python-tagged fence; fall back to any fence, then
    the raw reply. For qn-from-md, any fence works (models rarely use a `qn`
    tag), or the raw reply if unfenced.
    """
    if mode in ("code-from-md", "code-from-qn"):
        m = _CODE_FENCE.search(reply) or _ANY_FENCE.search(reply)
    else:
        m = _ANY_FENCE.search(reply)
    return (m.group(1) if m else reply).strip() + "\n"


# ---------- pytest driver (code modes) ----------

def run_pytest(suite_path: pathlib.Path, impl_dir: pathlib.Path) -> dict:
    env = os.environ.copy()
    env["QUINNYBENCH_IMPL_DIR"] = str(impl_dir)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", str(suite_path), "-v",
         "--tb=line", "--no-header", "-p", "no:cacheprovider"],
        capture_output=True, text=True, env=env, timeout=60,
    )
    return parse_pytest_output(proc.stdout + "\n" + proc.stderr)


_RESULT_LINE = re.compile(
    r"^(?:\S+::)?(test_\w+)\s+(PASSED|FAILED|ERROR|SKIPPED)", re.MULTILINE)


def parse_pytest_output(out: str) -> dict:
    passed, failed, errored, skipped = [], [], [], []
    for m in _RESULT_LINE.finditer(out):
        name, status = m.group(1), m.group(2)
        bucket = {"PASSED": passed, "FAILED": failed,
                  "ERROR": errored, "SKIPPED": skipped}[status]
        bucket.append(name)
    return {"passed": passed, "failed": failed, "errored": errored,
            "skipped": skipped, "raw_stdout": out}


# ---------- authoring grader (qn-from-md) ----------

_QUINNY_BIN = shutil.which("quinny") or "quinny"

_TASK_RE = re.compile(r"^task\s+\w+", re.MULTILINE)
_MODULE_RE = re.compile(r"Module is\s+(\S+)")
_FN_RE = re.compile(r"Function name is\s+(\S+)")
_CLS_RE = re.compile(r"Class name is\s+(\S+)")


def _count_test_criteria(qn: str) -> int:
    """Count indented lines under any `test` block.

    A `test` header is the exact word `test` (indented under a `task`). Its
    criteria are the more-deeply-indented lines that follow, up to the next
    same-or-less-indented line.
    """
    count = 0
    in_test = False
    test_indent = -1
    for ln in qn.splitlines():
        stripped = ln.strip()
        if not stripped:
            continue
        indent = len(ln) - len(ln.lstrip())
        if in_test:
            if indent > test_indent:
                count += 1
                continue
            in_test = False
        if stripped == "test":
            in_test = True
            test_indent = indent
    return count


def grade_qn_contract(qn_path: pathlib.Path, meta: dict) -> dict:
    """Score an authored .qn contract against 5 mechanical criteria."""
    qn = qn_path.read_text() if qn_path.exists() else ""
    module = meta["entrypoint"].split("::")[0]     # "impl.py"
    entity = meta["entrypoint"].split("::")[1]     # function or class name

    checks = []

    # 1. quinny check parses it.
    try:
        proc = subprocess.run([_QUINNY_BIN, "check", str(qn_path)],
                              capture_output=True, timeout=30)
        parses = proc.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        parses = False
    checks.append(("test_quinny_check_accepts", parses))

    # 2. Contains a task block.
    checks.append(("test_has_task_block", bool(_TASK_RE.search(qn))))

    # 3. At least 3 test criteria.
    checks.append(("test_has_multiple_test_criteria", _count_test_criteria(qn) >= 3))

    # 4. Module constraint present + matches.
    m = _MODULE_RE.search(qn)
    checks.append(("test_module_constraint_matches",
                   m is not None and m.group(1).rstrip(".") == module))

    # 5. Function OR class name constraint present + matches.
    fn = _FN_RE.search(qn)
    cls = _CLS_RE.search(qn)
    matches_entity = (fn and fn.group(1).rstrip(".") == entity) or \
                     (cls and cls.group(1).rstrip(".") == entity)
    checks.append(("test_entity_name_constraint_matches", bool(matches_entity)))

    return {
        "passed":  [n for n, ok in checks if ok],
        "failed":  [n for n, ok in checks if not ok],
        "errored": [],
    }


# ---------- one (task × model × mode) execution ----------

def run_one(task_id: str, provider_name: str, model: str, mode: str,
            run_dir: pathlib.Path) -> dict:
    task_dir = TASKS_DIR / task_id
    meta = json.loads((task_dir / "meta.json").read_text())

    provider = get_provider(provider_name)
    if not provider.is_available():
        return {"task": task_id, "provider": provider_name, "model": model,
                "mode": mode, "status": "skipped",
                "reason": f"{provider_name} not configured"}

    # Dir includes mode tag so tracks don't clobber each other on disk.
    tag = MODE_TAG[mode]
    out_dir = run_dir / task_id / f"{provider_name}--{model}--{tag}"
    out_dir.mkdir(parents=True, exist_ok=True)

    prompt = build_prompt(mode, task_dir)
    resp = provider.complete(prompt, model=model)
    (out_dir / "reply.txt").write_text(resp.text)
    body = extract_output(resp.text, mode)

    if mode in ("code-from-md", "code-from-qn"):
        (out_dir / "impl.py").write_text(body)
        grade = run_pytest(task_dir / "suite.py", out_dir)
    else:  # qn-from-md
        qn_path = out_dir / "contract.qn"
        qn_path.write_text(body)
        grade = grade_qn_contract(qn_path, meta)

    total = len(grade["passed"]) + len(grade["failed"]) + len(grade["errored"])
    result = {
        "task": task_id,
        "category": meta["category"],
        "provider": provider_name,
        "model": model,
        "mode": mode,
        "status": "graded",
        "input_tokens": resp.input_tokens,
        "output_tokens": resp.output_tokens,
        "criteria_total": total,
        "criteria_passed": len(grade["passed"]),
        "criteria_failed": len(grade["failed"]),
        "criteria_errored": len(grade["errored"]),
        "passed": grade["passed"],
        "failed": grade["failed"],
        "errored": grade["errored"],
    }
    (out_dir / "result.json").write_text(json.dumps(result, indent=2))
    return result


# ---------- CLI ----------

def cli(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--task", action="append",
                   help="Task id (repeatable). Omit to run every task.")
    p.add_argument("--provider", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--mode", choices=MODES, default="code-from-md",
                   help="Which track to run (default: code-from-md).")
    p.add_argument("--run-dir", default=None,
                   help="Where to write results. Defaults to results/<UTC-timestamp>/.")
    args = p.parse_args(argv)

    task_ids = args.task or sorted(d.name for d in TASKS_DIR.iterdir() if d.is_dir())
    run_dir = pathlib.Path(args.run_dir) if args.run_dir else \
        RESULTS_DIR / dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)

    all_results = []
    for tid in task_ids:
        print(f"→ {tid}  {args.provider}:{args.model} [{args.mode}]", flush=True)
        try:
            res = run_one(tid, args.provider, args.model, args.mode, run_dir)
        except Exception as e:
            res = {"task": tid, "provider": args.provider, "model": args.model,
                   "mode": args.mode, "status": "errored",
                   "reason": f"{type(e).__name__}: {e}"}
        all_results.append(res)
        if res.get("status") == "graded":
            print(f"   {res['criteria_passed']}/{res['criteria_total']} passed",
                  flush=True)
        else:
            print(f"   {res['status']}: {res.get('reason','')}", flush=True)

    # Merge with existing index.json in this run dir (append, dedupe by
    # (task, provider, model, mode)) so multiple --mode runs into the same
    # --run-dir accumulate rather than clobber.
    index_path = run_dir / "index.json"
    prior = []
    if index_path.exists():
        prior = json.loads(index_path.read_text())
    seen = {(r["task"], r.get("provider"), r.get("model"), r.get("mode"))
            for r in all_results}
    keep = [r for r in prior
            if (r["task"], r.get("provider"), r.get("model"), r.get("mode")) not in seen]
    index_path.write_text(json.dumps(keep + all_results, indent=2))
    print(f"\nresults → {run_dir}")


if __name__ == "__main__":
    cli()
