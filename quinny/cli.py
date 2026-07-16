"""`quinny` command-line interface.

Subcommands:
    parse <file>       Show the parsed AST as JSON.
    check <file>       Parse + build graph; report the first error, exit non-zero.
    graph <file>       Render the task graph as an ASCII tree.
    plan  <file>       Print execution layers (parallel groups) in order.
    gen   <request>    Translate an English request into Quinny via Claude.
    build <file>       Generate one target-language file per node (Quinny -> code).
"""

from __future__ import annotations

import os
import argparse
import json
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path

from rich.console import Console
from rich.tree import Tree

from quinny.graph import GraphError, TaskGraph, build_graph
from quinny.nodes import Component, Project, Task
from quinny.parser import QuinnyParseError, parse, parse_file


console = Console()


def _dataclass_to_json(obj):
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, tuple):
        return list(obj)
    return obj


def cmd_parse(path: Path) -> int:
    project = parse_file(path)
    console.print_json(
        data=asdict(project), default=lambda o: list(o) if isinstance(o, tuple) else o
    )
    return 0


def cmd_check(path: Path) -> int:
    project = parse_file(path)
    build_graph(project)
    console.print(f"[green]OK[/] {path} — project '{project.name}', "
                  f"{len(project.declarations)} declaration(s).")
    return 0


def cmd_import(path: Path, output: Path | None) -> int:
    from quinny.speckit import spec_to_qn
    notes = Console(stderr=True)
    res = spec_to_qn(path.read_text())
    if output is not None:
        output.write_text(res.qn)
    else:
        sys.stdout.write(res.qn)
    s = res.stats
    where = str(output) if output else "stdout"
    notes.print(f"[green]OK[/] imported {path} → {where}: "
                f"{s['stories']} component(s), {s['tests']} gating test(s), "
                f"{s['constraints']} constraint(s), {s['successes']} success line(s).")
    if res.clarifications:
        notes.print(f"[yellow]{len(res.clarifications)} unresolved "
                    f"[NEEDS CLARIFICATION] marker(s) skipped[/yellow] — resolve "
                    f"them in the spec, then re-import:")
        for c in res.clarifications:
            notes.print(f"  [dim]· {c}[/dim]")
    # Validate the emitted contract actually parses (guards against Spec Kit
    # template drift producing something Quinny can't read).
    try:
        build_graph(parse(res.qn))
        notes.print("[green]validated[/] — contract parses. Next: "
                    "[bold]quinny verify[/bold] it against an implementation.")
    except (QuinnyParseError, GraphError) as e:
        notes.print(f"[red]warning:[/red] emitted contract did not validate: {e}")
        return 1
    return 0


def cmd_graph(path: Path) -> int:
    project = parse_file(path)
    graph = build_graph(project)
    _render_tree(project, graph)
    return 0


def cmd_plan(path: Path) -> int:
    project = parse_file(path)
    graph = build_graph(project)
    layers = graph.execution_layers()
    console.print(f"[bold]Execution plan for '{project.name}'[/bold]")
    for i, layer in enumerate(layers):
        kinds = [_kind_of(project.by_name(n)) for n in layer]
        pretty = ", ".join(
            f"{n} [dim]({k})[/dim]" for n, k in zip(layer, kinds)
        )
        console.print(f"  [cyan]Layer {i}[/cyan]  {pretty}")
    return 0


def _kind_of(decl) -> str:
    if isinstance(decl, Task):
        return "task"
    if isinstance(decl, Component):
        return "component"
    return "?"


def _render_tree(project: Project, graph: TaskGraph) -> None:
    tree = Tree(f"[bold]project[/bold] {project.name}")
    for decl in project.declarations:
        _add_decl(tree, decl)
    console.print(tree)


def _add_decl(parent: Tree, decl) -> None:
    kind = _kind_of(decl)
    label = f"[bold cyan]{kind}[/bold cyan] {decl.name}"
    node = parent.add(label)
    goal = decl.goal
    if goal:
        for line in goal.lines:
            node.add(f"[green]goal[/green] {line}")
    if isinstance(decl, Task) and decl.depends:
        node.add(f"[magenta]depends[/magenta] {', '.join(decl.depends)}")
    if isinstance(decl, Component) and decl.uses:
        node.add(f"[magenta]uses[/magenta] {', '.join(decl.uses)}")
    for sub in decl.subtasks:
        _add_decl(node, sub)
    for sub in decl.subcomponents:
        _add_decl(node, sub)


def cmd_build(path: Path, target: str, out_dir: Path, model: str,
              types_model: str | None, node_model: str | None,
              repair_model: str | None, assemble_model: str | None,
              verify_flag: bool, max_repair: int,
              full_verify: bool, do_assemble: bool,
              only: str | None) -> int:
    from quinny.generator import (
        GeneratorError, generate, load_existing_generation, regenerate_node,
    )
    from quinny.usage import UsageTracker

    project = parse_file(path)
    tracker = UsageTracker()

    # Resolve per-stage models (fall back to --model).
    tm = types_model or model
    nm = node_model or model
    rm = repair_model or model
    am = assemble_model or model

    if only:
        try:
            existing = load_existing_generation(project, out_dir, target=target)
            with console.status(f"[cyan]Regenerating '{only}' with {nm}…[/cyan]"):
                fixed = regenerate_node(
                    project, only, existing, model=nm, tracker=tracker,
                )
        except GeneratorError as e:
            console.print(f"[red]error:[/red] {e}")
            return 1
        (out_dir / fixed.filename).write_text(fixed.source + "\n")
        for i, f in enumerate(existing.files):
            if f.name == only:
                existing.files[i] = fixed
                break
        console.print(
            f"[green]OK[/] regenerated {fixed.filename} "
            f"[dim]<-[/dim] {fixed.kind} {only}."
        )
        result = existing
    else:
        try:
            with console.status(
                f"[cyan]Generating {target} for '{project.name}' "
                f"(types={tm}, nodes={nm})…[/cyan]"
            ):
                result = generate(
                    project, target=target, model=model,
                    types_model=tm, node_model=nm, tracker=tracker,
                )
        except GeneratorError as e:
            console.print(f"[red]error:[/red] {e}")
            return 1

        result.write(out_dir)
        console.print(
            f"[green]OK[/] wrote {len(result.files)} file(s) to {out_dir} "
            f"(target={target})."
        )
        for f in result.files:
            console.print(f"  [dim]•[/dim] {f.filename}  [dim]<-[/dim] {f.kind} {f.name}")

    verify_needed = verify_flag or full_verify
    if verify_needed:
        rc = _run_verify_loop(
            project, result, out_dir, target, rm, max_repair,
            full=full_verify, tracker=tracker,
        )
        if rc != 0:
            _print_usage_report(tracker)
            return rc

    if do_assemble:
        _run_assemble(project, result, out_dir, am, tracker=tracker)

    _print_usage_report(tracker)
    return 0


def _print_usage_report(tracker) -> None:
    if not tracker.calls:
        return
    console.print()
    console.print("[bold]Usage / cost[/bold]")
    for line in tracker.report().splitlines():
        console.print(f"  {line}")


def _run_verify_loop(project, result, out_dir, target, model, max_repair, *,
                     full: bool, tracker=None) -> int:
    from quinny.generator import regenerate_file
    from quinny.verifier import verify

    def _restore(snapshot):
        # Roll the generation back to a previously-seen best version on disk.
        result.files[:] = snapshot
        for f in snapshot:
            (out_dir / f.filename).write_text(f.source + "\n")

    context: dict[str, object] = {f.name: f for f in result.files}
    best_passed = -1
    best_snapshot: list | None = None
    stale = 0  # consecutive repair rounds without progress
    for round_ in range(max_repair + 1):
        vr = verify(result, out_dir, full=full)
        _print_verify_summary(vr, round_)
        if vr.all_passed:
            return 0
        passed = sum(1 for c in vr.checks if c.passed)
        # keep-best + no-progress guard: track the best version seen. A repair
        # round that doesn't increase the passing count isn't helping; tolerate
        # one plateau (a fix sometimes needs a round to reorient) but stop on
        # sustained no-progress — that's thrashing, and it may have broken
        # working nodes. On stop, roll back to the best version so we NEVER
        # leave the user with worse code than an earlier round produced.
        if passed > best_passed:
            best_passed, best_snapshot = passed, list(result.files)
            stale = 0
        else:
            stale += 1
            if stale >= 2:
                console.print(
                    f"[yellow]verifier:[/yellow] repair stalled at round {round_} "
                    f"({passed}/{len(vr.checks)}, best {best_passed}/{len(vr.checks)}); "
                    f"reverting to the best version and stopping."
                )
                _restore(best_snapshot)
                return 1
        if round_ == max_repair:
            if best_snapshot is not None:
                _restore(best_snapshot)  # ensure the best version is on disk
            console.print(
                f"[red]verifier:[/red] {len(vr.failures)} node(s) still failing "
                f"after {max_repair} repair round(s)."
            )
            return 1

        # Repair each failing node in place, in the order they appear in
        # the generation (upstream first — a fix to an upstream node's
        # source lands in the deps_context of downstream repairs).
        by_name = {c.name: c for c in vr.failures}
        for gf in list(result.files):
            failure = by_name.get(gf.name)
            if not failure:
                continue
            console.print(
                f"[yellow]repair[/yellow] round {round_ + 1}: "
                f"{gf.filename} ({failure.stage})"
            )
            fixed = regenerate_file(
                project, gf.name, gf, failure.log,
                generated_context=context, target=target, model=model,
                tracker=tracker,
            )
            # Update in-place: both result.files and context.
            idx = result.files.index(gf)
            result.files[idx] = fixed
            context[fixed.name] = fixed
            (out_dir / fixed.filename).write_text(fixed.source + "\n")

    return 1


def _run_assemble(project, result, out_dir: Path, model: str,
                  tracker=None) -> None:
    from quinny.assemble import AssembleError, assemble

    try:
        with console.status(f"[cyan]Assembling with {model}…[/cyan]"):
            assembly = assemble(project, result, model=model, tracker=tracker)
    except AssembleError as e:
        console.print(f"[red]assemble:[/red] {e}")
        return
    assembly.write(out_dir)
    console.print(
        f"[green]OK[/] wrote main.py, requirements.txt, README.md to {out_dir}."
    )


def _print_verify_summary(vr, round_: int) -> None:
    passed = sum(1 for c in vr.checks if c.passed)
    total = len(vr.checks)
    header = f"[bold]Verify round {round_}[/bold]  {passed}/{total} passed"
    console.print(header)
    for c in vr.checks:
        if c.passed:
            console.print(f"  [green]✓[/green] {c.filename}  [dim]({c.stage})[/dim]")
        else:
            console.print(f"  [red]✗[/red] {c.filename}  [dim]({c.stage})[/dim]")
            for line in c.log.splitlines()[:6]:
                console.print(f"      [dim]{line}[/dim]")


def cmd_gen(request: str, output: Path | None, model: str, max_retries: int) -> int:
    from quinny.planner import PlannerError, plan_from_english
    from quinny.usage import UsageTracker

    tracker = UsageTracker()
    try:
        with console.status(f"[cyan]Asking {model} to draft Quinny…[/cyan]"):
            result = plan_from_english(
                request, model=model, max_retries=max_retries, tracker=tracker,
            )
    except PlannerError as e:
        console.print(f"[red]error:[/red] {e}")
        return 1

    console.print(
        f"[green]OK[/] {result.attempts} attempt(s), "
        f"project '{result.project.name}', "
        f"{len(result.project.declarations)} declaration(s)."
    )
    if output:
        output.write_text(result.source + "\n")
        console.print(f"[dim]Wrote {output}[/dim]")
    else:
        console.print()
        console.print(result.source)
    _print_usage_report(tracker)
    return 0


def cmd_scaffold(idea: str, out_dir: Path, lang: str, model: str) -> int:
    from quinny.scaffold import scaffold
    console.print(f"Scoping the verifiable logic in [italic]“{idea}”[/italic] "
                  f"({lang}, via {model})…\n")
    try:
        s = scaffold(idea, out_dir, lang=lang, model=model)
    except (QuinnyParseError, ValueError) as e:
        console.print(f"[red]error:[/red] {e}")
        return 1
    console.print(f"[bold]{s.project}[/bold] — contract for the money/logic core, "
                  f"{s.criteria} acceptance criteria.\n")
    console.print(f"  contract : [bold]{s.qn_path}[/bold]")
    console.print(f"  stub     : [bold]{s.stub_path}[/bold]\n")
    console.print("Next:")
    console.print(f"  1. Implement [bold]{s.stub_path.name}[/bold] (or ask an agent to).")
    console.print(f"  2. Gate it:  [bold]quinny verify {s.qn_path} {out_dir}"
                  f"{'' if lang=='python' else ' --lang js'}[/bold]")
    console.print(f"  3. Lock it:  add [bold]--emit {s.qn_path.stem}_contract_test"
                  f".{'py' if lang=='python' else 'js'}[/bold] and commit for CI.")
    return 0


def cmd_verify(file: Path, impl: Path, model: str, lang: str = "python",
               emit: Path | None = None, suite: Path | None = None) -> int:
    from quinny.contract import verify, run_saved
    if not impl.is_dir():
        console.print(f"[red]error:[/red] {impl} is not a directory")
        return 2
    if suite is not None:
        console.print(f"Running saved {lang} suite [bold]{suite.name}[/bold] "
                      f"against [bold]{impl}[/bold] (no LLM)…\n")
        results = run_saved(file, impl, suite, lang=lang)
    else:
        console.print(f"Compiling acceptance criteria from [bold]{file.name}[/bold]"
                      f" and verifying [bold]{impl}[/bold] ({lang}, via {model})…\n")
        results = verify(file, impl, model, emit=emit, lang=lang)
    if not results:
        console.print("[yellow]No test/success criteria in this plan.[/yellow]")
        return 0
    from rich.table import Table
    table = Table(show_header=True, header_style="bold")
    table.add_column("#", justify="right")
    table.add_column("kind")
    table.add_column("criterion")
    table.add_column("result")
    mark = {"PASS": "[green]✓ PASS[/green]", "FAIL": "[red]✗ FAIL[/red]",
            "ERROR": "[red]✗ ERROR[/red]", "MISSING": "[yellow]— n/a[/yellow]"}
    # Gate on concrete `test` criteria; `success` lines are usually high-level
    # summaries (unfalsifiable), so they're advisory — shown, but they don't
    # fail the build. This kills false-alarms on vague acceptance statements.
    passed = total = 0
    for r in results:
        gating = r.criterion.kind == "test"
        if gating:
            total += 1
            if r.status == "PASS":
                passed += 1
        text = r.criterion.text
        kind_label = "test" if gating else "[dim]success (advisory)[/dim]"
        result = mark.get(r.status, r.status)
        if not gating:
            result = f"[dim]{result}[/dim]"
        table.add_row(str(r.criterion.index), kind_label,
                      text[:66] + ("…" if len(text) > 66 else ""), result)
    console.print(table)
    color = "green" if passed == total else ("red" if passed == 0 else "yellow")
    console.print(f"\n[{color}]{passed}/{total} gating (test) criteria satisfied[/{color}]"
                  f"  [dim](success lines advisory)[/dim]")
    return 0 if passed == total else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="quinny",
        description="Quinny — an executable specification language: verify "
                    "code against acceptance criteria (v0.1)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    for name, help_text in [
        ("parse", "Parse a .qn file and print the AST as JSON."),
        ("check", "Parse and validate a .qn file."),
        ("graph", "Render the task graph as a tree."),
        ("plan",  "Print parallel execution layers."),
    ]:
        p = sub.add_parser(name, help=help_text)
        p.add_argument("file", type=Path)

    imp = sub.add_parser("import",
                         help="Turn a GitHub Spec Kit spec.md into a .qn "
                              "contract (deterministic — no LLM).")
    imp.add_argument("file", type=Path, help="Path to a Spec Kit spec.md.")
    imp.add_argument("-o", "--output", type=Path, default=None,
                     help="Write the .qn here (default: stdout).")

    scaf = sub.add_parser("scaffold",
                          help="From plain English, draft a contract for the "
                               "verifiable logic + a module stub to implement.")
    scaf.add_argument("idea", help="Plain-English description of what to build.")
    scaf.add_argument("-o", "--out-dir", type=Path, default=Path("."),
                      help="Where to write the contract + stub (default: .).")
    scaf.add_argument("--lang", choices=["python", "js", "ts", "go", "swift"], default="python")
    scaf.add_argument("--model", default=os.environ.get("QUINNY_MODEL", "claude-haiku-4-5"))

    ver = sub.add_parser("verify",
                         help="Compile a plan's test/success criteria into a "
                              "pytest suite and run it against an implementation.")
    ver.add_argument("file", type=Path, help="The .qn plan (the contract).")
    ver.add_argument("impl", type=Path, help="Directory of code to verify.")
    ver.add_argument("--model", default=os.environ.get("QUINNY_MODEL", "claude-haiku-4-5"),
                     help="Model used to compile criteria into tests.")
    ver.add_argument("--lang", choices=["python", "js", "ts", "go", "swift"], default="python",
                     help="Target language of the implementation (python=pytest, "
                          "js=Node's test runner, swift=swiftc compile+run).")
    ver.add_argument("--emit", type=Path, default=None,
                     help="Write the generated pytest suite here (review it, "
                          "commit it, then re-run deterministically in CI).")
    ver.add_argument("--suite", type=Path, default=None,
                     help="Run a previously emitted suite instead of generating "
                          "one (no LLM call).")

    gen = sub.add_parser("gen", help="Translate English into Quinny via Claude.")
    gen.add_argument("request", help="Natural-language description of what to build.")
    gen.add_argument("-o", "--output", type=Path, default=None,
                     help="Write Quinny to this file instead of stdout.")
    gen.add_argument("--model", default=os.environ.get("QUINNY_MODEL", "claude-opus-4-7"),
                     help="Anthropic model to use (default: claude-opus-4-7).")
    gen.add_argument("--max-retries", type=int, default=3,
                     help="Compile-and-retry attempts (default: 3).")

    build = sub.add_parser("build", help="Generate code from a .qn file via Claude.")
    build.add_argument("file", type=Path)
    build.add_argument("--target", choices=["python", "typescript"], default="python")
    build.add_argument("-o", "--out-dir", type=Path, default=Path("out"),
                       help="Directory to write generated files to (default: ./out).")
    build.add_argument("--model", default=os.environ.get("QUINNY_MODEL", "claude-opus-4-7"),
                       help="Default model for every stage (fallback).")
    build.add_argument("--types-model", default=None,
                       help="Override model for the shared-types synthesis "
                            "(design step — usually worth spending on).")
    build.add_argument("--node-model", default=None,
                       help="Override model for per-node code generation "
                            "(usually a cheaper model — small scoped tasks).")
    build.add_argument("--repair-model", default=None,
                       help="Override model for the verify-repair loop.")
    build.add_argument("--assemble-model", default=None,
                       help="Override model for main.py assembly.")
    build.add_argument("--verify", action="store_true",
                       help="Run syntax + import checks after generation and "
                            "repair failing files via Claude.")
    build.add_argument("--full-verify", action="store_true",
                       help="Like --verify but also runs each file "
                            "(executes its `if __name__ == \"__main__\":` "
                            "tests). Implies --verify.")
    build.add_argument("--max-repair", type=int, default=2,
                       help="Max repair rounds when verifying (default: 2).")
    build.add_argument("--assemble", action="store_true",
                       help="After generation, emit main.py, requirements.txt, "
                            "and README.md so the project is runnable "
                            "(`pip install -r requirements.txt && python main.py`).")
    build.add_argument("--only", type=str, default=None, metavar="NODE",
                       help="Regenerate only this one node (name from the .qn); "
                            "everything else is reused from disk.")

    args = parser.parse_args(argv)

    try:
        if args.cmd == "import":
            return cmd_import(args.file, args.output)
        if args.cmd == "scaffold":
            return cmd_scaffold(args.idea, args.out_dir, args.lang, args.model)
        if args.cmd == "verify":
            return cmd_verify(args.file, args.impl, args.model,
                              args.lang, args.emit, args.suite)
        if args.cmd == "gen":
            return cmd_gen(args.request, args.output, args.model, args.max_retries)
        if args.cmd == "build":
            return cmd_build(args.file, args.target, args.out_dir, args.model,
                             args.types_model, args.node_model,
                             args.repair_model, args.assemble_model,
                             args.verify, args.max_repair,
                             args.full_verify, args.assemble, args.only)
        handlers = {
            "parse": cmd_parse,
            "check": cmd_check,
            "graph": cmd_graph,
            "plan":  cmd_plan,
        }
        return handlers[args.cmd](args.file)
    except (QuinnyParseError, GraphError) as e:
        console.print(f"[red]error:[/red] {e}")
        return 1
    except FileNotFoundError as e:
        console.print(f"[red]error:[/red] {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
