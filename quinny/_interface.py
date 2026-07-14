"""Extract a compact public interface from a Python module's source.

Downstream generation prompts don't need every implementation detail of the
files a node depends on — they only need to know what symbols exist and how
to call them. Sending the full source scales the per-node prompt to O(N)
of accumulated project code; sending the interface keeps it O(N * signatures)
which is often 5-10x smaller.

If a file has syntax errors (mid-repair) we fall back to the full source so
the model can still see what's broken.
"""

from __future__ import annotations

import ast
from typing import Iterable


def extract_interface(source: str) -> str:
    """Return a short summary of a module's public API.

    Includes:
      - Top-level `NAME = ...` constants (LHS + optional type annotation).
      - Public functions: `def name(params) -> ret` + first docstring line.
      - Public classes: name + public methods with their signatures.

    Skips private symbols (leading underscore) and the bodies of everything.
    Falls back to full source if the AST won't parse.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source     # keep the broken code so the repair loop can see it

    lines: list[str] = []
    _add_module_docstring(tree, lines)

    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            lines.append(ast.unparse(node))
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            _add_assignment(node, lines)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not _is_private(node.name):
                lines.extend(_render_function(node, indent=""))
        elif isinstance(node, ast.ClassDef):
            if not _is_private(node.name):
                lines.extend(_render_class(node))
    return "\n".join(lines).rstrip() + "\n"


def _is_private(name: str) -> bool:
    return name.startswith("_") and not (name.startswith("__") and name.endswith("__"))


def _add_module_docstring(tree: ast.Module, lines: list[str]) -> None:
    ds = ast.get_docstring(tree)
    if ds:
        first_line = ds.splitlines()[0].strip()
        if first_line:
            lines.append(f'"""{first_line}"""')
            lines.append("")


def _add_assignment(node: ast.AST, lines: list[str]) -> None:
    """Keep public module-level constants (types + names, not full values)."""
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        if not _is_private(node.target.id):
            annotation = ast.unparse(node.annotation)
            lines.append(f"{node.target.id}: {annotation}")
    elif isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name) and not _is_private(target.id):
                lines.append(f"{target.id} = ...")


def _render_function(
    fn: ast.FunctionDef | ast.AsyncFunctionDef,
    *,
    indent: str,
) -> Iterable[str]:
    async_prefix = "async " if isinstance(fn, ast.AsyncFunctionDef) else ""
    sig = f"{indent}{async_prefix}def {fn.name}({ast.unparse(fn.args)})"
    if fn.returns is not None:
        sig += f" -> {ast.unparse(fn.returns)}"
    sig += ": ..."
    yield sig
    ds = ast.get_docstring(fn)
    if ds:
        first = ds.splitlines()[0].strip()
        if first:
            yield f'{indent}    """{first}"""'


def _render_class(cls: ast.ClassDef) -> Iterable[str]:
    bases = f"({', '.join(ast.unparse(b) for b in cls.bases)})" if cls.bases else ""
    yield f"class {cls.name}{bases}:"
    ds = ast.get_docstring(cls)
    if ds:
        first = ds.splitlines()[0].strip()
        if first:
            yield f'    """{first}"""'
    body_lines_before = 0
    for node in cls.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not _is_private(node.name) or node.name in {"__init__", "__call__"}:
                for line in _render_function(node, indent="    "):
                    yield line
                    body_lines_before += 1
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if not _is_private(node.target.id):
                annotation = ast.unparse(node.annotation)
                yield f"    {node.target.id}: {annotation}"
                body_lines_before += 1
    if body_lines_before == 0:
        yield "    pass"
