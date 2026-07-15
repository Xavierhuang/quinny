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
HOLDOUT_DIR = ROOT / "benchmarks" / "tests_holdout"


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
    # Fair-shot arm: a hand-authored, detailed multi-component plan (<name>.good.qn)
    # executed by Kimi. Isolates EXECUTION quality from Kimi's weak planning.
    "quinny-kimi-good": {"planner": "kimi-k2.7", "types": "kimi-k2.7",
                    "node": "kimi-k2.7", "repair": "kimi-k2.7", "assemble": "kimi-k2.7",
                    "plan_suffix": "good"},
    # Haiku arms (via OAuth SDK — a genuinely weaker model, ideal for the scale
    # test where a raw one-shot is likely to fail).
    "quinny-haiku": {"planner": "claude-haiku-4-5", "types": "claude-haiku-4-5",
                    "node": "claude-haiku-4-5", "repair": "claude-haiku-4-5",
                    "assemble": "claude-haiku-4-5"},
    "quinny-haiku-good": {"planner": "claude-haiku-4-5", "types": "claude-haiku-4-5",
                    "node": "claude-haiku-4-5", "repair": "claude-haiku-4-5",
                    "assemble": "claude-haiku-4-5", "plan_suffix": "good"},
    # Frontier baseline via the authenticated `claude` CLI (real Opus, subscription
    # auth). `via:cli` routes to run_one_raw_cli instead of the Python SDK.
    "raw-opus-cli": {"raw": "opus", "via": "cli"},
}


RAW_MAX_REPAIR = 2      # feed-back-errors loop cap for raw-prompt baselines
RAW_MAX_TOKENS = 16000  # output cap for SDK raw baselines (complex projects need room;
                        # 8k truncated Kimi's mini_kv on some runs)


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
    test_passed: int = 0      # held-out acceptance tests that passed
    test_total:  int = 0      # held-out acceptance tests total (0 = no suite)
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


def _plan_path(prompt: Path, plan_format: str = "quinny",
               suffix: str | None = None) -> Path:
    ext = "qn.json" if plan_format == "json" else "qn"
    stem = _prompt_name(prompt) + (f".{suffix}" if suffix else "")
    return PLANS_DIR / f"{stem}.{ext}"


def _resolve_plan_path(prompt: Path, suffix: str | None = None) -> Path | None:
    """Prefer the JSON plan when both exist; fall back to the DSL. `suffix`
    selects a variant plan file (e.g. `<name>.good.qn`) so different configs
    can execute different plans of the same prompt."""
    for fmt in ("json", "quinny"):
        p = _plan_path(prompt, fmt, suffix)
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
    if cfg.get("via") == "cli":
        return run_one_raw_cli(prompt, config_name, run_index)
    if "raw" in cfg:
        return run_one_raw(prompt, config_name, run_index)

    from quinny.generator import generate
    from quinny.assemble import assemble
    from quinny.parser import parse_file
    from quinny.verifier import verify
    from quinny.usage import UsageTracker

    plan_file = _resolve_plan_path(prompt, cfg.get("plan_suffix"))
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
        test_passed, test_total = grade_holdout(out_dir, _prompt_name(prompt))
        return RunResult(
            prompt=_prompt_name(prompt), config=config_name, run_index=run_index,
            tokens_input =sum(c.input_tokens  for c in tracker.calls),
            tokens_output=sum(c.output_tokens for c in tracker.calls),
            tokens_total =sum(c.input_tokens + c.output_tokens for c in tracker.calls),
            files_generated=len(generation.files),
            verify_passed=verify_passed,
            full_verified=full_verified,
            main_runs=main_runs,
            test_passed=test_passed, test_total=test_total,
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
            # Stream so a long completion keeps bytes flowing — the LingModel
            # proxy sits behind Cloudflare, which 524s a single non-streaming
            # response that takes >~100s (hit on complex tasks).
            with client.messages.stream(
                model=model, max_tokens=RAW_MAX_TOKENS,
                system=_RAW_SYSTEM_PROMPT,
                messages=messages,
                **thinking_kwargs(model),
            ) as stream:
                for _ in stream.text_stream:
                    pass
                resp = stream.get_final_message()
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

    test_passed, test_total = grade_holdout(out_dir, _prompt_name(prompt))
    return RunResult(
        prompt=_prompt_name(prompt), config=config_name, run_index=run_index,
        tokens_input =sum(c.input_tokens  for c in tracker.calls),
        tokens_output=sum(c.output_tokens for c in tracker.calls),
        tokens_total =sum(c.input_tokens + c.output_tokens for c in tracker.calls),
        files_generated=len(files),
        verify_passed=passed,
        full_verified=len(files) if main_runs else 0,   # main-runs = end-to-end pass
        main_runs=main_runs,
        test_passed=test_passed, test_total=test_total,
        error="" if main_runs else last_error[:200],
    )


def _project_source(files: dict[str, str]) -> str:
    """Render the current project as `# filename.py` code blocks — used to give
    the stateless `claude -p` repair call the code it needs to fix."""
    out = []
    for fname, src in files.items():
        out.append(f"```python\n# {fname}\n{src.rstrip()}\n```")
    return "\n\n".join(out)


def run_one_raw_cli(prompt: Path, config_name: str, run_index: int) -> RunResult:
    """Frontier baseline via the authenticated `claude` CLI (real Opus). Runs in
    an isolated temp cwd so no repo CLAUDE.md/.mcp.json leaks in. Single-shot
    generation + a stateless repair loop (the failing code is re-sent each round)."""
    import tempfile
    cfg = CONFIGS[config_name]
    model = cfg["raw"]
    out_dir = WORK_DIR / config_name / f"{_prompt_name(prompt)}_run{run_index}"
    _fresh_dir(out_dir)

    request = prompt.read_text().strip()
    base = (
        f"{_RAW_SYSTEM_PROMPT}\n\nRequirement:\n{request}\n\n"
        "Emit the ENTIRE project now — every file in its own "
        "```python\\n# filename.py\\n...\\n``` block. Output ONLY code blocks: "
        "no prose, and do NOT use any tools or create files, just print them."
    )

    tokens_in = tokens_out = 0
    files: dict[str, str] = {}
    main_runs = False
    last_error = ""
    cwd = tempfile.mkdtemp(prefix="qcli_")

    repairs = 0            # main.py repair rounds used
    gen_retries = 0        # extra regen tries when the model returns no code
    MAX_GEN_RETRIES = 2
    while True:
        if not files:
            msg = base                      # (re)generate from scratch
        else:
            msg = (
                f"{_RAW_SYSTEM_PROMPT}\n\nRequirement:\n{request}\n\n"
                f"This project failed when I ran `python main.py`:\n\n"
                f"```\n{last_error[:2000]}\n```\n\nHere is the current project:\n\n"
                f"{_project_source(files)}\n\nFix it. Emit the ENTIRE updated "
                "project again — every file in its own ```python\\n# filename.py"
                "\\n...\\n``` block. Only code blocks, no prose, no tools."
            )
        # `--tools ""` disables all tools so Opus PRINTS the project as fenced
        # `# filename.py` blocks instead of writing files agentically (verified).
        cmd = ["claude", "-p", msg, "--model", model,
               "--output-format", "json", "--max-turns", "1", "--tools", ""]
        try:
            proc = subprocess.run(cmd, cwd=cwd, capture_output=True,
                                  text=True, timeout=360)
            data = json.loads(proc.stdout or "{}")
        except Exception as e:
            # e.g. a rate-limited hang hitting the timeout — stop and record it
            # rather than burning more timeouts.
            last_error = f"{e.__class__.__name__}: {str(e)[:120]}"
            break
        usage = data.get("usage", {}) or {}
        tokens_in += (usage.get("input_tokens", 0)
                      + usage.get("cache_read_input_tokens", 0)
                      + usage.get("cache_creation_input_tokens", 0))
        tokens_out += usage.get("output_tokens", 0)

        parsed = _parse_raw_files(data.get("result", "") or "")
        if parsed:
            files = parsed
        elif not files:
            # No code blocks yet — Opus intermittently returns prose even with
            # --tools ""; retry generation a couple times before giving up.
            gen_retries += 1
            if gen_retries <= MAX_GEN_RETRIES:
                continue
            last_error = "Model returned no code blocks after retries."
            break

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
        repairs += 1
        if repairs > RAW_MAX_REPAIR:
            break

    passed = 0
    for fname in files:
        try:
            compile((out_dir / fname).read_text(), fname, "exec")
            passed += 1
        except SyntaxError:
            pass

    test_passed, test_total = grade_holdout(out_dir, _prompt_name(prompt))
    return RunResult(
        prompt=_prompt_name(prompt), config=config_name, run_index=run_index,
        tokens_input=tokens_in, tokens_output=tokens_out,
        tokens_total=tokens_in + tokens_out,
        files_generated=len(files),
        verify_passed=passed,
        full_verified=len(files) if main_runs else 0,
        main_runs=main_runs,
        test_passed=test_passed, test_total=test_total,
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


# --------------------------- held-out grading -----------------------------

def _holdout_test_file(prompt_name: str) -> Path | None:
    f = HOLDOUT_DIR / f"{prompt_name}_test.py"
    return f if f.exists() else None


# Pinned public entry point per task: (module_file, [required symbols]).
_ENTRYPOINTS: dict[str, tuple[str, list[str]]] = {
    "mini_kv":    ("mini_kv.py",    ["MiniKV"]),
    "mini_sheet": ("mini_sheet.py", ["Sheet", "CycleError"]),
    "minilang":   ("minilang.py",   ["evaluate"]),
}


def _ensure_entrypoint(out_dir: Path, prompt_name: str) -> None:
    """Normalize file layout so grading measures CODE, not where a tool happened
    to put it. If the pinned module (e.g. mini_kv.py) doesn't actually define/
    import the required symbols — missing, empty, or a stub — synthesize a
    re-export shim pointing at whatever module(s) do define them (including
    main.py, where Quinny's assembler sometimes inlines the class). No-op when
    the pinned file already provides the symbols (the raw arms emit them
    directly), so it never helps one config over another unfairly.
    """
    import re
    spec = _ENTRYPOINTS.get(prompt_name)
    if spec is None:
        return
    fname, symbols = spec
    pinned = out_dir / fname

    def defines(text: str, sym: str) -> bool:
        return bool(re.search(rf"^\s*(class|def)\s+{re.escape(sym)}\b", text, re.M))

    def provides(text: str, sym: str) -> bool:
        # defines it, imports it, or binds it (covers `X = ...` and re-exports).
        return (defines(text, sym)
                or bool(re.search(rf"^\s*(from|import)\b.*\b{re.escape(sym)}\b", text, re.M))
                or bool(re.search(rf"^\s*{re.escape(sym)}\s*=", text, re.M)))

    if pinned.exists():
        try:
            if all(provides(pinned.read_text(), s) for s in symbols):
                return
        except Exception:
            pass

    # Prefer a real module that defines the symbol; fall back to main.py.
    candidates = [p for p in sorted(out_dir.glob("*.py")) if p.name != fname]
    order = ([p for p in candidates if p.name != "main.py"]
             + [p for p in candidates if p.name == "main.py"])
    lines = []
    for sym in symbols:
        for py in order:
            try:
                if defines(py.read_text(), sym):
                    lines.append(f"from {py.stem} import {sym}")
                    break
            except Exception:
                continue
    if len(lines) == len(symbols):
        pinned.write_text("\n".join(lines) + "\n")


def grade_holdout(out_dir: Path, prompt_name: str) -> tuple[int, int]:
    """Run the hidden acceptance suite (never shown to the generator) against
    the produced project. Returns (passed, total). total==0 means the prompt
    has no held-out suite. A project that won't import scores 0/total."""
    import re
    tf = _holdout_test_file(prompt_name)
    if tf is None:
        return (0, 0)
    _ensure_entrypoint(out_dir, prompt_name)
    total = len(re.findall(r"^\s*def test_", tf.read_text(), re.M))
    env = os.environ.copy()
    env["PYTHONPATH"] = str(out_dir) + os.pathsep + env.get("PYTHONPATH", "")
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pytest", str(tf), "-q", "--tb=no",
             "-o", "addopts=", "-p", "no:cacheprovider"],
            cwd=str(out_dir), env=env, capture_output=True, text=True, timeout=60,
        )
    except subprocess.TimeoutExpired:
        return (0, total)
    out = r.stdout + r.stderr
    m = re.search(r"(\d+) passed", out)
    return (int(m.group(1)) if m else 0, total)


# ------------------------------- reporting --------------------------------

def print_summary(results: list[RunResult]) -> None:
    prompts = sorted({r.prompt for r in results})
    configs = sorted({r.config for r in results})

    print()
    print("=" * 92)
    print("  BENCHMARK SUMMARY  (mean across runs)")
    print("=" * 92)
    hdr = (f"{'prompt':<14} {'config':<14} {'runs':>4} {'out_tok':>9} "
           f"{'main':>5} {'TESTS':>7} {'pass/tot':>9}")
    print(hdr)
    print("  (TESTS = held-out acceptance-suite pass rate — the real quality signal)")
    print("-" * len(hdr))
    for p in prompts:
        for c in configs:
            cell = [r for r in results if r.prompt == p and r.config == c]
            if not cell:
                continue
            n = len(cell)
            main = statistics.mean(1 if r.main_runs else 0 for r in cell)
            tout = statistics.mean(r.tokens_output for r in cell)
            graded = [r for r in cell if r.test_total > 0]
            if graded:
                tp = statistics.mean(r.test_passed for r in graded)
                tt = statistics.mean(r.test_total  for r in graded)
                tests = tp / tt if tt else 0.0
                tcell = f"{tp:.1f}/{tt:.0f}"
                tpct = f"{tests:>6.0%}"
            else:
                tpct, tcell = "     —", "   —"
            print(f"{p:<14} {c:<14} {n:>4} {int(tout):>9,} "
                  f"{main:>4.0%} {tpct:>7} {tcell:>9}")
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

    # Ensure plans exist — but only for configs that actually consume one (Quinny
    # arms), using each config's plan_suffix. Raw arms need no plan.
    plan_cfgs = [CONFIGS[c] for c in args.configs
                 if not ("raw" in CONFIGS[c] or CONFIGS[c].get("via"))]
    missing = []
    for p in prompts:
        for cfg in plan_cfgs:
            if _resolve_plan_path(p, cfg.get("plan_suffix")) is None:
                missing.append(f"{p.stem}"
                               + (f".{cfg['plan_suffix']}" if cfg.get("plan_suffix") else ""))
    if missing:
        print("Missing cached plans:", sorted(set(missing)))
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
