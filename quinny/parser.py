"""Lark-based parser for Quinny v0.1.

Pipeline: source text -> Lark (with Python-style indenter postlex) -> parse
tree -> QuinnyTransformer -> Project AST (see quinny.nodes).
"""

from __future__ import annotations

from pathlib import Path

from lark import Lark, Transformer, v_args
from lark.exceptions import LarkError
from lark.indenter import Indenter

from quinny.nodes import (
    Component,
    Declaration,
    Field,
    NameField,
    Project,
    ProseField,
    Task,
)


def _split_body(items: tuple) -> tuple[tuple[Field, ...], tuple, tuple]:
    """Separate a task/component body into (fields, subtasks, subcomponents)."""
    fields: list[Field] = []
    subtasks: list[Task] = []
    subcomponents: list[Component] = []
    for item in items:
        if isinstance(item, Task):
            subtasks.append(item)
        elif isinstance(item, Component):
            subcomponents.append(item)
        else:
            fields.append(item)
    return tuple(fields), tuple(subtasks), tuple(subcomponents)


class QuinnyParseError(Exception):
    """Raised for both syntactic and semantic parse failures."""


class _QuinnyIndenter(Indenter):
    NL_type = "_NL"
    OPEN_PAREN_types: list[str] = []
    CLOSE_PAREN_types: list[str] = []
    INDENT_type = "_INDENT"
    DEDENT_type = "_DEDENT"
    tab_len = 4


_GRAMMAR_PATH = Path(__file__).with_name("grammar.lark")


def _build_parser() -> Lark:
    return Lark(
        _GRAMMAR_PATH.read_text(),
        parser="lalr",
        postlex=_QuinnyIndenter(),
        propagate_positions=True,
    )


_PARSER: Lark | None = None


def _parser() -> Lark:
    global _PARSER
    if _PARSER is None:
        _PARSER = _build_parser()
    return _PARSER


@v_args(inline=True)
class _QuinnyTransformer(Transformer):
    # -------- top level --------
    def start(self, project, body):
        return Project(name=project, declarations=tuple(body))

    @v_args(inline=False)
    def body(self, items):
        # `body` collects zero or more decls, interleaved with bare _NLs that
        # the transformer never sees (they carry no children).
        return [i for i in items if i is not None]

    def project_decl(self, name):
        return str(name)

    def decl(self, d):
        return d

    # -------- declarations --------
    def task_decl(self, name, *children):
        fields, subtasks, subcomponents = _split_body(children)
        return Task(
            name=str(name), fields=fields,
            subtasks=subtasks, subcomponents=subcomponents,
        )

    def component_decl(self, name, *children):
        fields, subtasks, subcomponents = _split_body(children)
        return Component(
            name=str(name), fields=fields,
            subtasks=subtasks, subcomponents=subcomponents,
        )

    def field(self, f):
        return f

    # -------- prose fields --------
    def goal_field(self, block):
        return ProseField(kind="goal", lines=block)

    def constraint_field(self, block):
        return ProseField(kind="constraint", lines=block)

    def test_field(self, block):
        return ProseField(kind="test", lines=block)

    def success_field(self, block):
        return ProseField(kind="success", lines=block)

    # -------- name fields --------
    def input_field(self, block):
        return NameField(kind="input", names=block)

    def output_field(self, block):
        return NameField(kind="output", names=block)

    def depends_field(self, block):
        return NameField(kind="depends", names=block)

    def uses_field(self, block):
        return NameField(kind="uses", names=block)

    # -------- blocks --------
    @v_args(inline=False)
    def text_block(self, items):
        return tuple(str(tok).strip() for tok in items if _is_content(tok))

    @v_args(inline=False)
    def name_block(self, items):
        return tuple(str(tok) for tok in items if _is_content(tok))


def _is_content(tok) -> bool:
    """Skip the _NL tokens that Lark still injects between block items."""
    t = getattr(tok, "type", None)
    return t not in {"_NL", "_INDENT", "_DEDENT"}


def parse(source: str) -> Project:
    """Parse a Quinny source string into a Project AST."""
    if not source.endswith("\n"):
        source = source + "\n"
    try:
        tree = _parser().parse(source)
    except LarkError as e:  # syntax
        raise QuinnyParseError(str(e)) from e
    project = _QuinnyTransformer().transform(tree)
    _check_unique_declarations(project)
    return project


def parse_file(path: str | Path) -> Project:
    """Read a plan from disk. Auto-detects format from the file extension
    (.json → JSON) or by sniffing the first non-whitespace char (`{` → JSON,
    anything else → DSL)."""
    text = Path(path).read_text()
    is_json = str(path).endswith(".json")
    if not is_json:
        stripped = text.lstrip()
        is_json = stripped.startswith("{")
    if is_json:
        # Lazy import — keeps parser.py's core Lark dependency chain small.
        from quinny.json_format import json_to_ast
        return json_to_ast(text)
    return parse(text)


def _check_unique_declarations(project: Project) -> None:
    seen: set[str] = set()
    for d in project.all_declarations():
        if d.name in seen:
            raise QuinnyParseError(
                f"Duplicate declaration '{d.name}' in project '{project.name}'."
            )
        seen.add(d.name)
