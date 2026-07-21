"""Render a run's index.json into a static HTML site with SVG bar charts.

    python -m viz.build results/2026-07-21-2100/ -o viz/out/

Produces:
- `viz/out/index.html` — overall leaderboard + per-category panels.
- `viz/out/m/<slug>.html` — per-model summary (all tasks, pct each).
- `viz/out/d/<slug>--<task>.html` — per (model, task) drilldown:
  generated code on the left, per-criterion PASS/FAIL on the right.
- `viz/out/style.css` — shared stylesheet.

Zero JS, zero build step. Model names on the leaderboard link to their model
page; each row on the model page links to the drilldown for that task.
"""
from __future__ import annotations

import argparse
import html
import json
import pathlib
import re
import sys

# Allow running as `python -m viz.build` from the repo root.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from runner.score import aggregate  # noqa: E402


# ---------- category display order + colors ----------

CATEGORY_ORDER = [
    "business-rules", "state-machines", "parsers", "validators",
    "data-transforms", "date-time", "small-algorithms", "cli-args",
]

CATEGORY_LABELS = {
    "business-rules":   "Business Rules",
    "state-machines":   "State Machines",
    "parsers":          "Parsers",
    "validators":       "Validators",
    "data-transforms":  "Data Transforms",
    "date-time":        "Date &amp; Time",
    "small-algorithms": "Small Algorithms",
    "cli-args":         "CLI Arg Handling",
}

ACCENT = "#2f6df1"
GREY = "#cfd6e3"
GOOD = "#2fa04a"    # pass tick
BAD  = "#d33f39"    # fail cross

BAR_WIDTH = 300
BAR_HEIGHT = 14


# ---------- URL / path helpers ----------

def model_slug(provider: str, model: str) -> str:
    """URL/file-safe slug for a (provider, model) pair.

    Model IDs on OpenRouter contain slashes (e.g. `moonshotai/kimi-k2`);
    provider slugs don't. Collapse any non-alphanum-hyphen to a single dash.
    """
    m = re.sub(r"[^a-z0-9]+", "-", model.lower()).strip("-")
    return f"{provider}--{m}"


def model_label(provider: str, model: str) -> str:
    return f"{provider}:{model}"


# ---------- SVG bar + row helpers ----------

def _bar_svg(pct: float, color: str) -> str:
    filled = round(BAR_WIDTH * pct / 100.0, 1)
    return (
        f'<svg class="bar" width="{BAR_WIDTH}" height="{BAR_HEIGHT}" '
        f'aria-hidden="true">'
        f'<rect x="0" y="0" width="{BAR_WIDTH}" height="{BAR_HEIGHT}" '
        f'rx="3" fill="#eef1f6"/>'
        f'<rect x="0" y="0" width="{filled}" height="{BAR_HEIGHT}" '
        f'rx="3" fill="{color}"/>'
        f'</svg>'
    )


def _row(label_html: str, pct: float, is_winner: bool) -> str:
    color = ACCENT if is_winner else GREY
    return (
        f'<div class="row">'
        f'<div class="mname">{label_html}</div>'
        f'<div class="mbar">{_bar_svg(pct, color)}</div>'
        f'<div class="mpct">{pct:.1f}</div>'
        f'</div>'
    )


def _panel(title: str, ranked: list[tuple[str, float, str]]) -> str:
    """`ranked` is (label_html, pct, is_winner-triggering key). Sorted by pct desc."""
    if not ranked:
        return ""
    top = ranked[0][1]
    rows = "".join(_row(lbl, p, is_winner=(p == top)) for lbl, p, _ in ranked)
    return f'<section class="panel"><h3>{title}</h3><div class="rows">{rows}</div></section>'


# ---------- CSS ----------

CSS = """\
* { box-sizing: border-box; }
body {
  font: 14px/1.4 -apple-system, BlinkMacSystemFont, "SF Pro Text", "Inter",
        system-ui, sans-serif;
  color: #1c2130; background: #f6f7fb;
  margin: 0; padding: 32px 24px 64px;
}
.wrap { max-width: 1100px; margin: 0 auto; }
h1 { font-size: 26px; margin: 0 0 4px; letter-spacing: -0.01em; }
.subtitle { color: #6b7385; margin-bottom: 28px; font-size: 13px; }
.subtitle a { color: #45506b; }
.overall { background: #fff; border: 1px solid #e2e6ef; border-radius: 10px;
           padding: 20px 22px; margin-bottom: 28px; }
.overall h2 { font-size: 15px; margin: 0 0 12px; color: #45506b;
              text-transform: uppercase; letter-spacing: 0.06em; }
.grid { display: grid; grid-template-columns: repeat(auto-fill,
        minmax(360px, 1fr)); gap: 16px; }
.panel { background: #fff; border: 1px solid #e2e6ef; border-radius: 10px;
         padding: 16px 20px; }
.panel h3 { font-size: 13px; margin: 0 0 12px; color: #45506b;
            text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600; }
.rows { display: grid; grid-template-columns: 1fr auto auto; gap: 6px 10px;
        align-items: center; }
.row { display: contents; }
.mname { font-size: 13px; color: #2b3244; overflow: hidden;
         text-overflow: ellipsis; white-space: nowrap; }
.mname a { color: inherit; text-decoration: none; border-bottom: 1px dotted #b6bdd0; }
.mname a:hover { color: #2f6df1; border-color: #2f6df1; }
.mbar { display: flex; align-items: center; }
.bar { display: block; }
.mpct { font-variant-numeric: tabular-nums; font-size: 12px;
        color: #4a5468; min-width: 40px; text-align: right; }
footer { color: #98a1b6; font-size: 12px; margin-top: 40px; text-align: center; }

/* Drilldown page */
.detail { display: grid; grid-template-columns: 1.4fr 1fr; gap: 20px; }
@media (max-width: 900px) { .detail { grid-template-columns: 1fr; } }
.detail pre { background: #0f1420; color: #d6dbe8; font: 12.5px/1.5 ui-monospace,
              "SF Mono", Menlo, Consolas, monospace; padding: 16px 18px;
              border-radius: 10px; overflow: auto; max-height: 640px;
              margin: 0; white-space: pre; }
.crit ul { list-style: none; padding: 0; margin: 0; }
.crit li { padding: 6px 4px; border-bottom: 1px solid #eef1f6;
           font-size: 13px; display: flex; align-items: center; gap: 8px; }
.crit li:last-child { border-bottom: none; }
.tick { color: #2fa04a; font-weight: 700; }
.cross { color: #d33f39; font-weight: 700; }
.err { color: #b57500; font-weight: 700; }
.crumbs { font-size: 12px; color: #6b7385; margin-bottom: 12px; }
.crumbs a { color: #45506b; }
.stat { display: inline-block; background: #eef1f6; padding: 2px 8px;
        border-radius: 999px; margin-right: 6px; font-size: 12px;
        color: #45506b; font-variant-numeric: tabular-nums; }
"""


# ---------- Main index page ----------

def render_index(agg: dict, run_dir: pathlib.Path) -> str:
    overall = sorted(agg.items(), key=lambda kv: -kv[1]["overall_pct"])
    top = overall[0][1]["overall_pct"] if overall else 0
    overall_rows = "".join(
        _row(_link_to_model(m), d["overall_pct"], is_winner=(d["overall_pct"] == top))
        for m, d in overall
    )

    panels = []
    for cat in CATEGORY_ORDER:
        entries = []
        for m, d in agg.items():
            if cat not in d["per_category"]:
                continue
            entries.append((_link_to_model(m), d["per_category"][cat]["pct"], m))
        if not entries:
            continue
        entries.sort(key=lambda t: -t[1])
        panels.append(_panel(CATEGORY_LABELS.get(cat, cat), entries))

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>QuinnyBench — {html.escape(run_dir.name)}</title>
<link rel="stylesheet" href="style.css"></head>
<body><div class="wrap">
<h1>QuinnyBench</h1>
<div class="subtitle">
  Contract-graded coding benchmark · run <code>{html.escape(run_dir.name)}</code>
  · {len(agg)} model(s) scored across {sum(1 for c in CATEGORY_ORDER if any(c in d["per_category"] for d in agg.values()))} categories.
  Click any model name to see per-task breakdown.
</div>
<div class="overall"><h2>Overall</h2><div class="rows">{overall_rows}</div></div>
<div class="grid">{"".join(panels)}</div>
<footer>Generated by <code>python -m viz.build</code>. Grader: Quinny (deterministic).</footer>
</div></body></html>
"""


def _link_to_model(label: str) -> str:
    """`label` is `provider:model` — turn into a link to m/<slug>.html."""
    provider, _, model = label.partition(":")
    slug = model_slug(provider, model)
    return f'<a href="m/{html.escape(slug)}.html">{html.escape(label)}</a>'


# ---------- Per-model page ----------

def render_model_page(label: str, results: list[dict], run_dir: pathlib.Path) -> str:
    """One page per (provider, model) listing every task with its pct + drilldown link."""
    provider, _, model = label.partition(":")
    total_p = sum(r["criteria_passed"] for r in results)
    total_t = sum(r["criteria_total"] for r in results)
    overall = round(100.0 * total_p / total_t, 1) if total_t else 0.0

    # Table of tasks, sorted by category order then task id.
    def _cat_key(r):
        try:
            return (CATEGORY_ORDER.index(r["category"]), r["task"])
        except ValueError:
            return (len(CATEGORY_ORDER), r["task"])

    rows = []
    for r in sorted(results, key=_cat_key):
        pct = 100.0 * r["criteria_passed"] / r["criteria_total"] if r["criteria_total"] else 0.0
        cat = CATEGORY_LABELS.get(r["category"], r["category"])
        slug = model_slug(r["provider"], r["model"])
        drilldown = f'd/{slug}--{r["task"]}.html'
        rows.append(
            f'<div class="row">'
            f'<div class="mname"><a href="../{html.escape(drilldown)}">'
            f'{html.escape(r["task"])} <span class="stat">{cat}</span></a></div>'
            f'<div class="mbar">{_bar_svg(pct, ACCENT if pct >= 90 else GREY)}</div>'
            f'<div class="mpct">{r["criteria_passed"]}/{r["criteria_total"]}</div>'
            f'</div>'
        )

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>{html.escape(label)} — QuinnyBench</title>
<link rel="stylesheet" href="../style.css"></head>
<body><div class="wrap">
<div class="crumbs"><a href="../index.html">← QuinnyBench</a> · run <code>{html.escape(run_dir.name)}</code></div>
<h1>{html.escape(label)}</h1>
<div class="subtitle">
  <span class="stat">overall {overall:.1f}%</span>
  <span class="stat">{total_p}/{total_t} criteria</span>
  <span class="stat">{len(results)} tasks</span>
</div>
<div class="panel"><h3>Per-task results</h3><div class="rows">{"".join(rows)}</div></div>
<footer>Click a task to see the generated code and per-criterion PASS/FAIL.</footer>
</div></body></html>
"""


# ---------- Per (model, task) drilldown ----------

def render_drilldown(r: dict, run_dir: pathlib.Path) -> str:
    label = model_label(r["provider"], r["model"])
    slug = model_slug(r["provider"], r["model"])
    impl_path = run_dir / r["task"] / f'{r["provider"]}--{r["model"]}' / "impl.py"
    code = impl_path.read_text() if impl_path.exists() else \
        "# (impl.py not found — model may have errored or run not generated code)"

    pct = 100.0 * r["criteria_passed"] / r["criteria_total"] if r["criteria_total"] else 0.0

    def _li(name: str, css_class: str, mark: str) -> str:
        return (
            f'<li><span class="{css_class}">{mark}</span>'
            f'<span>{html.escape(name)}</span></li>'
        )

    # Show passed → failed → errored so the eye lands on failures easily.
    lis = []
    for n in r.get("passed", []):  lis.append(_li(n, "tick",  "✓"))
    for n in r.get("failed", []):  lis.append(_li(n, "cross", "✗"))
    for n in r.get("errored", []): lis.append(_li(n, "err",   "!"))

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>{html.escape(r["task"])} · {html.escape(label)} — QuinnyBench</title>
<link rel="stylesheet" href="../style.css"></head>
<body><div class="wrap">
<div class="crumbs">
  <a href="../index.html">← QuinnyBench</a> ·
  <a href="../m/{html.escape(slug)}.html">{html.escape(label)}</a>
</div>
<h1>{html.escape(r["task"])}</h1>
<div class="subtitle">
  <span class="stat">{html.escape(CATEGORY_LABELS.get(r["category"], r["category"]))}</span>
  <span class="stat">{r["criteria_passed"]}/{r["criteria_total"]} passed ({pct:.1f}%)</span>
  <span class="stat">by {html.escape(label)}</span>
</div>
<div class="detail">
  <div><pre>{html.escape(code)}</pre></div>
  <div class="crit panel"><h3>Criteria</h3><ul>{"".join(lis)}</ul></div>
</div>
</div></body></html>
"""


# ---------- CLI ----------

def cli(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run_dir", type=pathlib.Path,
                   help="A results/<timestamp>/ directory containing index.json.")
    p.add_argument("-o", "--out", type=pathlib.Path,
                   default=pathlib.Path(__file__).parent / "out",
                   help="Where to write the rendered site (default: viz/out).")
    args = p.parse_args(argv)

    index = args.run_dir / "index.json"
    if not index.exists():
        print(f"no index.json under {args.run_dir}", file=sys.stderr)
        sys.exit(2)

    raw_results = json.loads(index.read_text())
    graded = [r for r in raw_results if r.get("status") == "graded"]
    agg = aggregate(raw_results)
    if not agg:
        print("no graded results in this run — nothing to render.", file=sys.stderr)
        sys.exit(2)

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "m").mkdir(exist_ok=True)
    (args.out / "d").mkdir(exist_ok=True)

    (args.out / "index.html").write_text(render_index(agg, args.run_dir))
    (args.out / "style.css").write_text(CSS)

    # Group by model → per-model page.
    by_model: dict[str, list[dict]] = {}
    for r in graded:
        by_model.setdefault(model_label(r["provider"], r["model"]), []).append(r)
    for label, rs in by_model.items():
        slug = model_slug(*label.split(":", 1))
        (args.out / "m" / f"{slug}.html").write_text(
            render_model_page(label, rs, args.run_dir))

    # One drilldown per graded (task, model).
    for r in graded:
        slug = model_slug(r["provider"], r["model"])
        (args.out / "d" / f'{slug}--{r["task"]}.html').write_text(
            render_drilldown(r, args.run_dir))

    print(f"wrote {args.out / 'index.html'} + {len(by_model)} model pages "
          f"+ {len(graded)} drilldowns")


if __name__ == "__main__":
    cli()
