"""End-to-end tests for the Quinny v0.1 parser and graph builder."""

from __future__ import annotations

from pathlib import Path

import pytest

from quinny import (
    GraphError,
    NameField,
    ProseField,
    QuinnyParseError,
    Task,
    build_graph,
    parse,
    parse_file,
)


EXAMPLES = Path(__file__).parent.parent / "examples"


# ---------- syntax ----------


def test_minimal_project_parses():
    src = "project Tiny\n\ntask A\n    goal\n        Do a thing.\n"
    project = parse(src)
    assert project.name == "Tiny"
    assert len(project.declarations) == 1
    a = project.declarations[0]
    assert isinstance(a, Task)
    assert a.name == "A"
    assert a.goal is not None
    assert a.goal.lines == ("Do a thing.",)


def test_prose_field_preserves_multiple_lines():
    src = (
        "project P\n\n"
        "task T\n"
        "    goal\n"
        "        Do X.\n"
        "    constraint\n"
        "        Under 200ms.\n"
        "        No third-party SDKs.\n"
    )
    project = parse(src)
    t = project.declarations[0]
    constraint = next(f for f in t.fields if isinstance(f, ProseField) and f.kind == "constraint")
    assert constraint.lines == ("Under 200ms.", "No third-party SDKs.")


def test_name_field_preserves_multiple_ids():
    src = (
        "project P\n\n"
        "task T\n"
        "    goal\n"
        "        Do X.\n"
        "    input\n"
        "        email\n"
        "        password\n"
    )
    project = parse(src)
    t = project.declarations[0]
    inp = next(f for f in t.fields if isinstance(f, NameField) and f.kind == "input")
    assert inp.names == ("email", "password")


def test_comments_are_ignored():
    src = (
        "# a comment\n"
        "project P\n\n"
        "task T\n"
        "    # explains the goal\n"
        "    goal\n"
        "        Do X.\n"
    )
    project = parse(src)
    assert project.name == "P"


def test_duplicate_declarations_rejected():
    src = (
        "project P\n\n"
        "task T\n    goal\n        A.\n\n"
        "task T\n    goal\n        B.\n"
    )
    with pytest.raises(QuinnyParseError):
        parse(src)


# ---------- graph semantics ----------


def test_graph_requires_goal():
    # Grammar itself requires at least one field, so use a non-goal field.
    src = (
        "project P\n\n"
        "task T\n"
        "    constraint\n"
        "        Something.\n"
    )
    project = parse(src)
    with pytest.raises(GraphError):
        build_graph(project)


def test_graph_rejects_unknown_dependency():
    src = (
        "project P\n\n"
        "task A\n"
        "    goal\n"
        "        Do A.\n"
        "    depends\n"
        "        Ghost\n"
    )
    project = parse(src)
    with pytest.raises(GraphError):
        build_graph(project)


def test_graph_rejects_cycle():
    src = (
        "project P\n\n"
        "task A\n    goal\n        A.\n    depends\n        B\n\n"
        "task B\n    goal\n        B.\n    depends\n        A\n"
    )
    project = parse(src)
    with pytest.raises(GraphError):
        build_graph(project)


def test_execution_layers_are_topological():
    project = parse_file(EXAMPLES / "instagram.qn")
    graph = build_graph(project)
    layers = graph.execution_layers()
    seen: set[str] = set()
    for layer in layers:
        for name in layer:
            decl = project.by_name(name)
            assert decl is not None
            for dep in (*getattr(decl, "depends", ()), *getattr(decl, "uses", ())):
                assert dep in seen, f"{dep} must appear before {name}"
        seen.update(layer)


# ---------- example files ----------


@pytest.mark.parametrize(
    "example",
    ["login.qn", "notify_users.qn", "instagram.qn"],
)
def test_example_files_parse_and_validate(example: str):
    project = parse_file(EXAMPLES / example)
    build_graph(project)
