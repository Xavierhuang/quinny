"""Does the .qn LANGUAGE improve output vs md / json / yaml?

Isolates the FORMAT as the only variable. For each task we take the SAME
acceptance criteria and author them four ways (.qn / JSON / YAML / Markdown),
then run the IDENTICAL compile→gate pipeline on each and measure:

  1. extraction fidelity — does parsing the format back recover every criterion?
  2. gate quality — build a suite from the recovered criteria (with that
     format's raw text as the spec context) and run it against a known-correct
     and a known-broken impl. A better format = fewer false-fails on the correct
     impl and more catches on the broken one.

Hypothesis (stated up front, reported either way): in Quinny's pipeline the
criteria become plain strings BEFORE suite generation, so gate quality should be
a wash across formats; the only place a language can win is extraction fidelity
(structured formats beat free-text markdown on messy input).
"""
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from quinny.parser import parse_file  # noqa: E402
from quinny.contract import (  # noqa: E402
    Criterion, extract_criteria, build_suite, run_suite,
)

MODEL = os.environ.get("QUINNY_MODEL", "claude-haiku-4-5")
REPEATS = int(os.environ.get("QUINNY_REPEATS", "2"))
SCRATCH = Path(os.environ["QUINNY_REF_DIR"])  # dir holding <task>.py references

# task -> (module filename, a one-line bug to inject for the "broken" variant:
#          (needle, replacement) applied to the reference source).
TASKS = {
    "textkit": ("textkit.py",
                ("def ordinal(n):", "def ordinal(n):\n    return f'{n}th'  # BUG\ndef _dead_ordinal(n):")),
    "cron":    ("cron.py",
                ("return dt.day in self.dom or _cron_dow(dt) in self.dow",
                 "return dt.day in self.dom  # BUG: dropped the OR-rule")),
}


# ---------------------------------------------------------------- format render
def to_qn(name, crits):
    body = "".join(f"    test\n        {c}\n" for c in crits)
    return f"project {name}\n\ncomponent C\n    goal\n        {name}.\n{body}"


def to_json(name, crits):
    return json.dumps({"project": name, "criteria": crits}, indent=2)


def to_yaml(name, crits):
    lines = [f"project: {name}", "criteria:"]
    for c in crits:
        lines.append(f"  - '{c.replace(chr(39), chr(39) * 2)}'")  # '' escapes a quote
    return "\n".join(lines) + "\n"


def to_md(name, crits):
    body = "\n".join(f"{i}. {c}" for i, c in enumerate(crits, 1))
    return f"# {name}\n\n## Acceptance Criteria\n\n{body}\n"


# ---------------------------------------------------------------- format parse
def from_qn(text):
    fd, p = tempfile.mkstemp(suffix=".qn")
    os.close(fd)
    Path(p).write_text(text)
    crits = [c.text for c in extract_criteria(parse_file(p)) if c.kind == "test"]
    Path(p).unlink(missing_ok=True)
    return crits


def from_json(text):
    return list(json.loads(text).get("criteria", []))


def from_yaml(text):
    out = []
    for line in text.splitlines():
        m = re.match(r"\s*-\s*'(.*)'\s*$", line)
        if m:
            out.append(m.group(1).replace(chr(39) * 2, chr(39)))
    return out


def from_md(text):
    return [m.group(1).strip()
            for m in re.finditer(r"^\s*\d+\.\s+(.+)$", text, re.MULTILINE)]


FORMATS = {
    "qn":   (to_qn, from_qn),
    "json": (to_json, from_json),
    "yaml": (to_yaml, from_yaml),
    "md":   (to_md, from_md),
}


# ---------------------------------------------------------------- run one cell
def _impl_dir(task, broken):
    mod, (needle, repl) = TASKS[task]
    d = Path(tempfile.mkdtemp(prefix=f"abl_{task}_"))
    src = (SCRATCH / mod).read_text()
    if broken:
        assert needle in src, f"needle not found for {task}"
        src = src.replace(needle, repl, 1)
    (d / mod).write_text(src)
    (d / "main.py").write_text(f"import {mod[:-3]}\n")
    return d


def _score(results):
    tests = [r for r in results if r.criterion.kind == "test"]
    if not tests:
        return 0.0
    return sum(1 for r in tests if r.status == "PASS") / len(tests)


def run():
    print(f"format ablation · model={MODEL} · repeats={REPEATS}\n")
    for task in TASKS:
        proj = parse_file(ROOT / "benchmarks" / "plans" / f"{task}.good.qn")
        crits = [c.text for c in extract_criteria(proj) if c.kind == "test"]
        n = len(crits)
        good = _impl_dir(task, broken=False)
        bad = _impl_dir(task, broken=True)
        print(f"== {task} ==  ({n} criteria)")
        print(f"{'format':6} {'extract':8} {'pass_on_correct':16} {'fail_on_broken':14}")
        for fmt, (render, parse) in FORMATS.items():
            text = render(task.capitalize(), crits)
            recovered = parse(text)
            extract = f"{len(recovered)}/{n}" + ("" if recovered == crits else " ✗DIFF")
            pc, fb = [], []
            for _ in range(REPEATS):
                cobjs = [Criterion(i + 1, "C", "test", c)
                         for i, c in enumerate(recovered)]
                suite = build_suite(text, good, cobjs, MODEL)
                pc.append(_score(run_suite(good, suite, cobjs)))
                fb.append(1.0 - _score(run_suite(bad, suite, cobjs)))
            print(f"{fmt:6} {extract:8} "
                  f"{100*sum(pc)/len(pc):6.0f}%           "
                  f"{100*sum(fb)/len(fb):6.0f}%", flush=True)
        shutil.rmtree(good, ignore_errors=True)
        shutil.rmtree(bad, ignore_errors=True)
        print()


if __name__ == "__main__":
    run()
