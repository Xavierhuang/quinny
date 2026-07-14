"""Quinny benchmark harness.

Runs a small set of prompts against several per-stage model configurations
and reports raw token counts + verify pass rates. See benchmarks/README.md
for the method.

Usage
-----
    # Warm the plan cache — one Opus call per prompt.
    python scripts/bench.py --warm-plans

    # Full benchmark.
    python scripts/bench.py --runs 3

    # Faster smoke check.
    python scripts/bench.py --runs 1 --configs all-opus opus+haiku

    # Offline dry-run using a stub client (no API calls). Verifies the
    # harness plumbing without spending tokens.
    python scripts/bench.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import statistics
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = ROOT / "benchmarks" / "prompts"
PLANS_DIR   = ROOT / "benchmarks" / "plans"
RESULTS_DIR = ROOT / "benchmarks" / "results"
WORK_DIR    = ROOT / "benchmarks" / ".work"


# Per-stage model routing per config. `planner` is only used with --warm-plans
# (plans are cached and reused across configs).
CONFIGS: dict[str, dict[str, str]] = {
    "all-opus":    {"planner": "claude-opus-4-7",   "types": "claude-opus-4-7",
                    "node":    "claude-opus-4-7",   "repair": "claude-opus-4-7",
                    "assemble":"claude-opus-4-7"},
    "opus+sonnet": {"planner": "claude-opus-4-7",   "types": "claude-opus-4-7",
                    "node":    "claude-sonnet-4-6", "repair": "claude-sonnet-4-6",
                    "assemble":"claude-sonnet-4-6"},
    "opus+haiku":  {"planner": "claude-opus-4-7",   "types": "claude-opus-4-7",
                    "node":    "claude-haiku-4-5",  "repair": "claude-haiku-4-5",
                    "assemble":"claude-sonnet-4-6"},
    "opus+mixed":  {"planner": "claude-opus-4-7",   "types": "claude-opus-4-7",
                    "node":    "claude-sonnet-4-6", "repair": "claude-haiku-4-5",
                    "assemble":"claude-sonnet-4-6"},
    "all-sonnet":  {"planner": "claude-sonnet-4-6", "types": "claude-sonnet-4-6",
                    "node":    "claude-sonnet-4-6", "repair": "claude-sonnet-4-6",
                    "assemble":"claude-sonnet-4-6"},
    # Raw-prompt baselines: no Quinny, no plan, no per-node scaffolding — just
    # ask the model to emit a runnable Python project. Cached plan is ignored.
    "raw-opus":   {"raw": "claude-opus-4-7"},
    "raw-sonnet": {"raw": "claude-sonnet-4-6"},
    "raw-haiku":  {"raw": "claude-haiku-4-5"},
    "raw-kimi":    {"raw": "kimi-k2.7"},
    "quinny-kimi": {"planner": "kimi-k2.7", "types": "kimi-k2.7",
                    "node": "kimi-k2.7", "repair": "kimi-k2.7", "assemble": "kimi-k2.7"},
}


RAW_MAX_REPAIR = 2   # feed-back-errors loop cap for raw-prompt baselines


# ------------------------------- results ----------------------------------

@dataclass
class RunResult:
    prompt: str
    config: str
    run_index: int
    tokens_input:  int
    tokens_output: int
    tokens_total:  int
    files_generated: int
    verify_passed:   int      # nodes that passed fast verify
    full_verified:   int      # nodes whose __main__ ran cleanly
    main_runs: bool           # `python main.py` exit code == 0
    error: str = ""           # populated if the build itself blew up

    @property
    def all_verified(self) -> bool:
        return self.files_generated > 0 and self.full_verified == self.files_generated


@dataclass
class BenchOutput:
    started_at: str
    runs: list[RunResult] = field(default_factory=list)


# ------------------------------- planning ---------------------------------

def _prompt_name(path: Path) -> str:
    return path.stem


def _plan_path(prompt: Path, plan_format: str = "quinny") -> Path:
    ext = "qn.json" if plan_format == "json" else "qn"
    return PLANS_DIR / f"{_prompt_name(prompt)}.{ext}"


def _resolve_plan_path(prompt: Path) -> Path | None:
    """Prefer the JSON plan when both exist; fall back to the DSL. Used by
    `run_one` so a config can pick whichever plan is on disk."""
    for fmt in ("json", "quinny"):
        p = _plan_path(prompt, fmt)
        if p.exists():
            return p
    return None


def warm_plans(
    prompts: list[Path], planner_model: str, plan_format: str = "quinny",
) -> None:
    """Cache one plan per prompt. Reused across configs."""
    from quinny.planner import plan_from_english
    from quinny.usage import UsageTracker

    PLANS_DIR.mkdir(parents=True, exist_ok=True)
    for prompt in prompts:
        target = _plan_path(prompt, plan_format)
        if target.exists():
            print(f"[plan-cache] hit    {target.name}")
            continue
        request = prompt.read_text().strip()
        print(f"[plan-cache] miss   {target.name} — asking {planner_model} "
              f"[format={plan_format}]…")
        tracker = UsageTracker()
        result = plan_from_english(
            request, model=planner_model, tracker=tracker, format=plan_format,
        )
        target.write_text(result.source + "\n")
        print(f"           wrote plan ({sum(1 for _ in result.project.all_declarations())} decls, "
              f"{tracker.by_stage().get('planner', {}).get('input', 0):,} in / "
              f"{tracker.by_stage().get('planner', {}).get('output', 0):,} out tokens)")


# ------------------------------- one run ----------------------------------

def _fresh_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)


def run_one(prompt: Path, config_name: str, run_index: int) -> RunResult:
    """Generate + verify + assemble one config-run. Returns metrics."""
    cfg = CONFIGS[config_name]
    if "raw" in cfg:
        return run_one_raw(prompt, config_name, run_index)

    from quinny.generator import generate
    from quinny.assemble import assemble
    from quinny.parser import parse_file
    from quinny.verifier import verify
    from quinny.usage import UsageTracker

    plan_file = _resolve_plan_path(prompt)
    if plan_file is None:
        return RunResult(
            prompt=_prompt_name(prompt), config=config_name, run_index=run_index,
            tokens_input=0, tokens_output=0, tokens_total=0,
            files_generated=0, verify_passed=0, full_verified=0,
            main_runs=False,
            error=f"no cached plan for {prompt.name} (run --warm-plans first)",
        )

    out_dir = WORK_DIR / config_name / f"{_prompt_name(prompt)}_run{run_index}"
    _fresh_dir(out_dir)

    tracker = UsageTracker()
    project = parse_file(plan_file)
    try:
        generation = generate(
            project, target="python",
            model=cfg["node"],
            types_model=cfg["types"],
            node_model=cfg["node"],
            tracker=tracker,
        )
        generation.write(out_dir)

        vr = verify(generation, out_dir, full=False)
        verify_passed = sum(1 for c in vr.checks if c.passed)

        full_vr = verify(generation, out_dir, full=True)
        full_verified = sum(1 for c in full_vr.checks if c.passed)

        assembly = assemble(project, generation, model=cfg["assemble"], tracker=tracker)
        assembly.write(out_dir)

        main_runs = _run_main(out_dir)
        return RunResult(
            prompt=_prompt_name(prompt), config=config_name, run_index=run_index,
            tokens_input =sum(c.input_tokens  for c in tracker.calls),
            tokens_output=sum(c.output_tokens for c in tracker.calls),
            tokens_total =sum(c.input_tokens + c.output_tokens for c in tracker.calls),
            files_generated=len(generation.files),
            verify_passed=verify_passed,
            full_verified=full_verified,
            main_runs=main_runs,
        )
    except Exception as e:                               # bounded error surface
        return RunResult(
            prompt=_prompt_name(prompt), config=config_name, run_index=run_index,
            tokens_input =sum(c.input_tokens  for c in tracker.calls),
            tokens_output=sum(c.output_tokens for c in tracker.calls),
            tokens_total =sum(c.input_tokens + c.output_tokens for c in tracker.calls),
            files_generated=0, verify_passed=0, full_verified=0,
            main_runs=False,
            error=f"{e.__class__.__name__}: {e}",
        )


_RAW_SYSTEM_PROMPT = """You implement a runnable Python project from a one-sentence \
requirement. Output ONLY code — no prose, no explanations.

Emit each file as a fenced code block whose first line is a `# <filename>.py` \
comment. You choose how to split the project across files. Always include a \
`main.py` with an `if __name__ == "__main__":` block that exercises the \
public API (this is the acceptance test — it MUST exit 0). Python standard \
library only. Every function has type hints."""


_RAW_FILE_RE = None   # compiled lazily inside _parse_raw_files


def _parse_raw_files(text: str) -> dict[str, str]:
    """Extract {filename: source} pairs from a model's raw output."""
    import re
    global _RAW_FILE_RE
    if _RAW_FILE_RE is None:
        _RAW_FILE_RE = re.compile(
            r"```(?:python|py)?\s*\n#\s*([A-Za-z0-9_./-]+\.py)\s*\n(.*?)\n```",
            re.DOTALL,
        )
    files: dict[str, str] = {}
    for m in _RAW_FILE_RE.finditer(text):
        fname = m.group(1).strip().lstrip("./")
        files[fname] = m.group(2)
    return files


def run_one_raw(prompt: Path, config_name: str, run_index: int) -> RunResult:
    """Baseline: plain Claude prompt, no Quinny scaffolding.

    Loop: ask for multi-file Python. Parse files. Run `python main.py`.
    On failure, feed stderr back for up to RAW_MAX_REPAIR rounds.
    """
    from quinny._capabilities import thinking_kwargs
    from quinny.usage import UsageTracker
    import anthropic

    cfg = CONFIGS[config_name]
    model = cfg["raw"]
    out_dir = WORK_DIR / config_name / f"{_prompt_name(prompt)}_run{run_index}"
    _fresh_dir(out_dir)

    tracker = UsageTracker()
    from quinny._capabilities import make_client
    client = make_client()

    request = prompt.read_text().strip()
    messages: list[dict[str, Any]] = [
        {"role": "user", "content":
            f"Requirement:\n{request}\n\n"
            f"Emit the project now. Every file must be in its own "
            f"```python\\n# filename.py\\n...\\n``` block. `main.py` "
            f"must have a __main__ demo that exits 0."},
    ]

    files: dict[str, str] = {}
    main_runs = False
    last_error = ""

    for attempt in range(RAW_MAX_REPAIR + 1):
        try:
            resp = client.messages.create(
                model=model, max_tokens=4096,
                system=_RAW_SYSTEM_PROMPT,
                messages=messages,
                **thinking_kwargs(model),
            )
        except Exception as e:
            return RunResult(
                prompt=_prompt_name(prompt), config=config_name, run_index=run_index,
                tokens_input =sum(c.input_tokens  for c in tracker.calls),
                tokens_output=sum(c.output_tokens for c in tracker.calls),
                tokens_total =sum(c.input_tokens + c.output_tokens for c in tracker.calls),
                files_generated=len(files), verify_passed=0, full_verified=0,
                main_runs=False, error=f"{e.__class__.__name__}: {e}",
            )
        tracker.record("raw" if attempt == 0 else "raw-repair", model, resp)
        raw = "\n".join(
            b.text for b in resp.content if getattr(b, "type", None) == "text"
        )
        parsed = _parse_raw_files(raw)
        if parsed:
            files = parsed        # replace prior state — the model rewrote the world
        elif attempt == 0:
            last_error = "Model returned no `# filename.py` code blocks."
            break

        # Persist files, run main.py.
        _fresh_dir(out_dir)
        for fname, src in files.items():
            path = out_dir / fname
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(src if src.endswith("\n") else src + "\n")

        result = _run_main_capture(out_dir)
        if result.returncode == 0:
            main_runs = True
            last_error = ""
            break

        last_error = (result.stderr or result.stdout or "unknown").strip()
        if attempt == RAW_MAX_REPAIR:
            break

        # Feed the error back to the model for a repair round.
        messages.append({"role": "assistant", "content": raw})
        messages.append({"role": "user", "content":
            f"Your project failed when I ran `python main.py`:\n\n"
            f"```\n{last_error[:2000]}\n```\n\n"
            f"Fix it. Emit the ENTIRE updated project again — every file "
            f"in its own ```python\\n# filename.py\\n...\\n``` block."})

    # Fast-verify each file (syntax only, no import to avoid double-counting
    # errors main.py already surfaced).
    passed = 0
    for fname in files:
        try:
            compile((out_dir / fname).read_text(), fname, "exec")
            passed += 1
        except SyntaxError:
            pass

    return RunResult(
        prompt=_prompt_name(prompt), config=config_name, run_index=run_index,
        tokens_input =sum(c.input_tokens  for c in tracker.calls),
        tokens_output=sum(c.output_tokens for c in tracker.calls),
        tokens_total =sum(c.input_tokens + c.output_tokens for c in tracker.calls),
        files_generated=len(files),
        verify_passed=passed,
        full_verified=len(files) if main_runs else 0,   # main-runs = end-to-end pass
        main_runs=main_runs,
        error="" if main_runs else last_error[:200],
    )


def _run_main_capture(out_dir: Path):
    """Like _run_main but returns the full CompletedProcess so we can feed
    stderr back to the model for the repair loop."""
    main = out_dir / "main.py"
    if not main.exists():
        return subprocess.CompletedProcess([], 1, "", "main.py not found")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(out_dir) + os.pathsep + env.get("PYTHONPATH", "")
    try:
        return subprocess.run(
            [sys.executable, str(main.resolve())],
            cwd=str(out_dir), env=env,
            capture_output=True, text=True, timeout=20,
        )
    except subprocess.TimeoutExpired as e:
        return subprocess.CompletedProcess(
            [], 124, "", f"timeout after 20s: {e.stderr or ''}"
        )


def _run_main(out_dir: Path) -> bool:
    main = out_dir / "main.py"
    if not main.exists():
        return False
    env = os.environ.copy()
    env["PYTHONPATH"] = str(out_dir) + os.pathsep + env.get("PYTHONPATH", "")
    try:
        r = subprocess.run(
            [sys.executable, str(main.resolve())],
            cwd=str(out_dir), env=env,
            capture_output=True, text=True, timeout=20,
        )
        return r.returncode == 0
    except subprocess.TimeoutExpired:
        return False


# ------------------------------- reporting --------------------------------

def print_summary(results: list[RunResult]) -> None:
    prompts = sorted({r.prompt for r in results})
    configs = sorted({r.config for r in results})

    print()
    print("=" * 92)
    print("  BENCHMARK SUMMARY  (mean across runs)")
    print("=" * 92)
    hdr = f"{'prompt':<20} {'config':<14} {'runs':>4} {'in':>10} {'out':>10} {'total':>10} {'verify':>8} {'full':>7} {'main':>5}"
    print(hdr)
    print("-" * len(hdr))
    for p in prompts:
        for c in configs:
            cell = [r for r in results if r.prompt == p and r.config == c]
            if not cell:
                continue
            n = len(cell)
            files = statistics.mean(r.files_generated for r in cell) if cell else 0
            verify = statistics.mean(r.verify_passed for r in cell) / max(files, 1)
            full = statistics.mean(r.full_verified for r in cell) / max(files, 1)
            main = statistics.mean(1 if r.main_runs else 0 for r in cell)
            tin  = statistics.mean(r.tokens_input  for r in cell)
            tout = statistics.mean(r.tokens_output for r in cell)
            tot  = tin + tout
            print(f"{p:<20} {c:<14} {n:>4} "
                  f"{int(tin):>10,} {int(tout):>10,} {int(tot):>10,} "
                  f"{verify:>7.0%} {full:>6.0%} {main:>4.0%}")
        print()
    print("=" * 92)


def write_json(results: list[RunResult]) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = RESULTS_DIR / f"{ts}.json"
    path.write_text(json.dumps({
        "started_at": ts,
        "runs": [asdict(r) for r in results],
    }, indent=2))
    return path


# ------------------------------- driver -----------------------------------

def main() -> int:
    p = argparse.ArgumentParser(description="Quinny model-config benchmark")
    p.add_argument("--warm-plans", action="store_true",
                   help="Only warm the plan cache (planner calls only).")
    p.add_argument("--planner-model", default="claude-opus-4-7",
                   help="Model to use when warming plans (default opus-4-7).")
    p.add_argument("--plan-format", choices=["quinny", "json"], default="quinny",
                   help="Format of cached plans (--warm-plans). Quinny DSL "
                        "or JSON via structured-output. `run_one` auto-detects "
                        "which one exists on disk.")
    p.add_argument("--configs", nargs="+", choices=list(CONFIGS),
                   default=list(CONFIGS),
                   help="Which model configs to benchmark.")
    p.add_argument("--prompts", nargs="+", default=None,
                   help="Which prompt files to run (default: all in benchmarks/prompts).")
    p.add_argument("--runs", type=int, default=3,
                   help="How many times to run each (prompt, config) cell.")
    p.add_argument("--dry-run", action="store_true",
                   help="Skip actual API calls — validate harness plumbing.")
    args = p.parse_args()

    prompts = sorted(PROMPTS_DIR.glob("*.txt"))
    if args.prompts:
        wanted = set(args.prompts)
        prompts = [x for x in prompts if x.name in wanted or x.stem in wanted]
    if not prompts:
        print("No prompts to run.", file=sys.stderr)
        return 2

    if args.dry_run:
        print("[dry-run] configs:", args.configs)
        print("[dry-run] prompts:", [p.name for p in prompts])
        print("[dry-run] runs per cell:", args.runs)
        print("[dry-run] total build attempts:",
              len(args.configs) * len(prompts) * args.runs)
        print("[dry-run] NO API calls will be made.")
        return 0

    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        print("ERROR: ANTHROPIC_API_KEY is not set.", file=sys.stderr)
        return 2

    if args.warm_plans:
        warm_plans(prompts, args.planner_model, args.plan_format)
        return 0

    # Ensure plans exist before running configs.
    missing = [p for p in prompts if _resolve_plan_path(p) is None]
    if missing:
        print("Missing cached plans:", [p.name for p in missing])
        print("Run: python scripts/bench.py --warm-plans")
        return 2

    results: list[RunResult] = []
    total = len(prompts) * len(args.configs) * args.runs
    done = 0
    for prompt in prompts:
        for cfg in args.configs:
            for i in range(args.runs):
                done += 1
                t0 = time.time()
                r = run_one(prompt, cfg, i)
                dt = time.time() - t0
                results.append(r)
                mark = "OK" if r.all_verified and r.main_runs else (
                    "err" if r.error else "partial"
                )
                print(f"[{done}/{total}] {prompt.stem:<20} {cfg:<12} "
                      f"run={i} {dt:>5.1f}s  {mark:<7} "
                      f"tokens={r.tokens_total:>7,}  "
                      f"verify={r.verify_passed}/{r.files_generated}  "
                      f"full={r.full_verified}/{r.files_generated}  "
                      f"main={'✓' if r.main_runs else '✗'}")
                if r.error:
                    print(f"           error: {r.error[:100]}")

    print_summary(results)
    out = write_json(results)
    print(f"\nRaw results: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
