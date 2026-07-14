"""Quinny — a task-oriented intent language for AI coding agents."""

from quinny.nodes import (
    Project,
    Task,
    Component,
    Field,
    ProseField,
    NameField,
)
from quinny.parser import parse, parse_file, QuinnyParseError
from quinny.graph import TaskGraph, build_graph, GraphError
from quinny.verifier import NodeCheck, VerifyResult, verify, verify_python_file
from quinny.assemble import (
    AssembleError,
    AssemblyResult,
    assemble,
    derive_requirements,
    derive_readme,
)
from quinny.usage import UsageTracker, UsageCall

__all__ = [
    "Project",
    "Task",
    "Component",
    "Field",
    "ProseField",
    "NameField",
    "parse",
    "parse_file",
    "QuinnyParseError",
    "TaskGraph",
    "build_graph",
    "GraphError",
    "NodeCheck",
    "VerifyResult",
    "verify",
    "verify_python_file",
    "AssembleError",
    "AssemblyResult",
    "assemble",
    "derive_requirements",
    "derive_readme",
    "UsageTracker",
    "UsageCall",
]

__version__ = "0.1.0"
