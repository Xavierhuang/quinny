"""AST node types for Quinny v0.1.

Every declaration in a Quinny source file becomes one of these dataclasses.
Nodes are immutable value objects; the parser produces them and the rest of
the compiler (graph builder, planner, code generator) consumes them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


FieldKind = Literal[
    "goal",
    "constraint",
    "test",
    "success",
    "input",
    "output",
    "depends",
    "uses",
]

PROSE_KINDS: frozenset[FieldKind] = frozenset(
    {"goal", "constraint", "test", "success"}
)
NAME_KINDS: frozenset[FieldKind] = frozenset(
    {"input", "output", "depends", "uses"}
)


@dataclass(frozen=True)
class ProseField:
    """A field whose block is free-text lines: goal / constraint / test / success."""

    kind: FieldKind
    lines: tuple[str, ...]


@dataclass(frozen=True)
class NameField:
    """A field whose block is identifiers: input / output / depends / uses."""

    kind: FieldKind
    names: tuple[str, ...]


Field = ProseField | NameField


@dataclass(frozen=True)
class Task:
    name: str
    fields: tuple[Field, ...]
    # Nested subtasks / subcomponents — hierarchical decomposition. A subtask
    # is a child scope only for the human reader; in the flattened task
    # graph it appears as a peer of every other declaration.
    subtasks: tuple["Task", ...] = ()
    subcomponents: tuple["Component", ...] = ()

    @property
    def goal(self) -> ProseField | None:
        return _find_prose(self.fields, "goal")

    @property
    def depends(self) -> tuple[str, ...]:
        f = _find_name(self.fields, "depends")
        return f.names if f else ()


@dataclass(frozen=True)
class Component:
    name: str
    fields: tuple[Field, ...]
    subtasks: tuple[Task, ...] = ()
    subcomponents: tuple["Component", ...] = ()

    @property
    def goal(self) -> ProseField | None:
        return _find_prose(self.fields, "goal")

    @property
    def uses(self) -> tuple[str, ...]:
        f = _find_name(self.fields, "uses")
        return f.names if f else ()

    @property
    def depends(self) -> tuple[str, ...]:
        f = _find_name(self.fields, "depends")
        return f.names if f else ()


Declaration = Task | Component


def flatten(decl: Declaration) -> list[Declaration]:
    """Depth-first walk of a declaration and every nested subtask/subcomponent."""
    out: list[Declaration] = [decl]
    for sub in decl.subtasks:
        out.extend(flatten(sub))
    for sub in decl.subcomponents:
        out.extend(flatten(sub))
    return out


def parent_of(project: "Project", name: str) -> Declaration | None:
    """Return the nearest ancestor of `name`, or None if `name` is top-level."""
    def _walk(decl: Declaration) -> Declaration | None:
        for sub in (*decl.subtasks, *decl.subcomponents):
            if sub.name == name:
                return decl
            hit = _walk(sub)
            if hit is not None:
                return hit
        return None
    for top in project.declarations:
        if top.name == name:
            return None
        found = _walk(top)
        if found is not None:
            return found
    return None


@dataclass(frozen=True)
class Project:
    name: str
    declarations: tuple[Declaration, ...] = field(default_factory=tuple)

    def by_name(self, name: str) -> Declaration | None:
        for d in self.all_declarations():
            if d.name == name:
                return d
        return None

    def all_declarations(self) -> list[Declaration]:
        """Every declaration, flattened depth-first over nested subtasks."""
        out: list[Declaration] = []
        for d in self.declarations:
            out.extend(flatten(d))
        return out


def _find_prose(fields: tuple[Field, ...], kind: FieldKind) -> ProseField | None:
    for f in fields:
        if isinstance(f, ProseField) and f.kind == kind:
            return f
    return None


def _find_name(fields: tuple[Field, ...], kind: FieldKind) -> NameField | None:
    for f in fields:
        if isinstance(f, NameField) and f.kind == kind:
            return f
    return None
