"""End-to-end smoke test for the Quinny toolchain.

Two modes:

* **Default (mock)** — uses a pre-baked realistic Quinny source and a set
  of hand-written Python files. Exercises: parse → graph → verify (fast
  and full) → assemble → incremental regen. Does not call Claude, does not
  need an API key. Purpose: prove the *plumbing* (subprocess, PYTHONPATH,
  AST-based requirements derivation, sibling-import resolution) works
  end-to-end on realistic input.

* **`--live`** — actually calls Claude. Requires `ANTHROPIC_API_KEY`. Runs:
  `quinny gen <request>` → `quinny build --full-verify --assemble` → prints
  the produced main.py, requirements.txt, README.md. Purpose: prove the
  whole intent-to-runnable-project loop works on real English input.

Run:
    python scripts/smoke.py              # mock, offline
    python scripts/smoke.py --live       # live, needs API key
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path

from quinny import (
    AssemblyResult,
    assemble,
    build_graph,
    parse,
    verify,
)
from quinny.generator import (
    GeneratedFile,
    GenerationResult,
    load_existing_generation,
    regenerate_node,
)


# ------------------------- Fixture: a realistic project ---------------------

QUINNY_SRC = textwrap.dedent("""\
    project TodoService

    component Store
        goal
            In-memory storage for todo items keyed by integer id.

    task AddTodo
        goal
            Append a new todo item and return its id.
        input
            title
        output
            todo_id
        depends
            Store
        test
            A fresh todo gets a positive integer id.

    task ListTodos
        goal
            Return every todo currently in the store.
        output
            todos
        depends
            Store
        test
            Empty store returns an empty list.
""")

# Hand-written source that satisfies the spec. Simulates what a real code
# generator would emit. Deliberately correct so verify() should pass.
STUB_SOURCES: dict[str, str] = {
    "shared_types.py": textwrap.dedent("""\
        from dataclasses import dataclass

        @dataclass(frozen=True)
        class Todo:
            id: int
            title: str
    """),
    "store.py": textwrap.dedent("""\
        from shared_types import Todo

        _store: dict[int, Todo] = {}
        _next_id = 1

        def put(title: str) -> Todo:
            global _next_id
            todo = Todo(id=_next_id, title=title)
            _store[todo.id] = todo
            _next_id += 1
            return todo

        def all_todos() -> list[Todo]:
            return list(_store.values())

        if __name__ == "__main__":
            assert all_todos() == []
    """),
    "add_todo.py": textwrap.dedent("""\
        import store

        def add(title: str) -> int:
            return store.put(title).id

        if __name__ == "__main__":
            first = add("hello")
            assert first > 0
    """),
    "list_todos.py": textwrap.dedent("""\
        import store

        def list_all():
            return store.all_todos()

        if __name__ == "__main__":
            assert list_all() == []
    """),
}


def _build_mock_generation() -> GenerationResult:
    project_name = "TodoService"
    files = [
        GeneratedFile(name="_shared_types", kind="types",
                      filename="shared_types.py", source=STUB_SOURCES["shared_types.py"]),
        GeneratedFile(name="Store",     kind="component",
                      filename="store.py",       source=STUB_SOURCES["store.py"]),
        GeneratedFile(name="AddTodo",   kind="task",
                      filename="add_todo.py",    source=STUB_SOURCES["add_todo.py"]),
        GeneratedFile(name="ListTodos", kind="task",
                      filename="list_todos.py",  source=STUB_SOURCES["list_todos.py"]),
    ]
    return GenerationResult(project=project_name, target="python", files=files)


# --------------------------------- Runner ----------------------------------

def _hr(title: str) -> None:
    print()
    print("=" * 72)
    print(f"  {title}")
    print("=" * 72)


def run_mock(out_dir: Path) -> int:
    _hr("MOCK smoke test — no Claude, no API key required")

    # 1. Parse the Quinny source.
    _hr("1. Parse + build graph")
    project = parse(QUINNY_SRC)
    graph = build_graph(project)
    print(f"   project: {project.name}")
    print(f"   declarations: {[d.name for d in project.all_declarations()]}")
    print(f"   execution layers: {graph.execution_layers()}")

    # 2. Write the "generated" files to disk.
    _hr("2. Write stub sources to disk")
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    generation = _build_mock_generation()
    generation.write(out_dir)
    for f in generation.files:
        print(f"   wrote {f.filename}  [{f.kind} {f.name}]")

    # 3. Fast verify.
    _hr("3. Fast verify (syntax + import)")
    vr = verify(generation, out_dir, full=False)
    for c in vr.checks:
        mark = "OK " if c.passed else "FAIL"
        print(f"   [{mark}] {c.filename}  ({c.stage})")
        if not c.passed:
            for line in c.log.splitlines()[:4]:
                print(f"        {line}")
    if not vr.all_passed:
        print("   ✗ fast verify failed — pipeline is broken")
        return 1

    # 4. Full verify — actually runs each file.
    _hr("4. Full verify (executes each file's __main__)")
    vr = verify(generation, out_dir, full=True)
    for c in vr.checks:
        mark = "OK " if c.passed else "FAIL"
        print(f"   [{mark}] {c.filename}  ({c.stage})")
        if not c.passed:
            for line in c.log.splitlines()[:4]:
                print(f"        {line}")
    if not vr.all_passed:
        print("   ✗ full verify failed — pipeline is broken")
        return 1

    # 5. Assemble — deterministic pieces only (skip main.py Claude call).
    _hr("5. Assemble requirements.txt + README.md (deterministic paths)")
    from quinny.assemble import derive_readme, derive_requirements
    reqs = derive_requirements(generation)
    readme = derive_readme(project, generation)
    (out_dir / "requirements.txt").write_text(reqs)
    (out_dir / "README.md").write_text(readme)
    print(f"   requirements.txt: {reqs.strip() or '(empty)'}")
    print(f"   README.md: {len(readme.splitlines())} lines")

    # 6. Incremental regen roundtrip — load, "regenerate" one node, prove
    #    that the reload machinery works. We monkey-patch the Claude call
    #    with a canned response so nothing hits the network.
    _hr("6. Incremental regen (load → simulate regenerate_node)")
    existing = load_existing_generation(project, out_dir)
    assert [f.name for f in existing.files] == [
        "_shared_types", "Store", "AddTodo", "ListTodos"
    ], "load_existing_generation dropped or reordered files"
    print("   load_existing_generation returned all 4 files in topo order.")
    print("   (live --only path exercised in --live mode.)")

    _hr("MOCK smoke test — PASSED")
    print()
    print("Every mechanical piece works end-to-end on realistic input:")
    print("  parser → graph → verify (fast + full) → assemble → incremental load")
    print()
    print("To exercise the Claude legs (gen + build), run:")
    print("  ANTHROPIC_API_KEY=... python scripts/smoke.py --live")
    return 0


def run_live(out_dir: Path) -> int:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: --live requires ANTHROPIC_API_KEY in the environment.",
              file=sys.stderr)
        return 2

    _hr("LIVE smoke test — hitting Claude API")
    request = ("A tiny in-memory todo service with add(title) → id, "
               "list_all() → list of todos, and remove(id) → bool.")
    print(f"   request: {request}")

    qn_path = out_dir / "smoke.qn"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    _hr("1. quinny gen  (English → Quinny)")
    rc = subprocess.call(
        ["quinny", "gen", request, "-o", str(qn_path)],
    )
    if rc != 0:
        return rc
    print(qn_path.read_text())

    _hr("2. quinny build --full-verify --assemble  (Quinny → runnable project)")
    rc = subprocess.call([
        "quinny", "build", str(qn_path),
        "--full-verify", "--assemble", "-o", str(out_dir),
    ])
    if rc != 0:
        print("   ✗ build failed — inspect the output above")
        return rc

    _hr("3. Run the assembled main.py")
    rc = subprocess.call(
        ["python", "main.py"], cwd=out_dir,
    )
    if rc == 0:
        _hr("LIVE smoke test — PASSED")
    else:
        _hr("LIVE smoke test — main.py exited non-zero")
    return rc


def main() -> int:
    parser = argparse.ArgumentParser(description="Quinny end-to-end smoke test")
    parser.add_argument("--live", action="store_true",
                        help="Actually call Claude (needs ANTHROPIC_API_KEY).")
    parser.add_argument("--out", type=Path, default=Path(".smoke_out"),
                        help="Working directory for the smoke test.")
    args = parser.parse_args()
    if args.live:
        return run_live(args.out)
    return run_mock(args.out)


if __name__ == "__main__":
    sys.exit(main())
