"""Task graph construction and validation.

The graph is the compiler's core intermediate representation. Every planner,
code generator, and verifier consumes this instead of the parse tree.
"""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx

from quinny.nodes import Component, Declaration, Project, Task


class GraphError(Exception):
    """Raised for semantic errors: unresolved refs, missing goals, cycles."""


@dataclass(frozen=True)
class TaskGraph:
    """A validated DAG of tasks and components for one project."""

    project: str
    dag: nx.DiGraph  # nodes are declaration names; data['decl'] is the Declaration

    def declaration(self, name: str) -> Declaration:
        return self.dag.nodes[name]["decl"]

    def roots(self) -> list[str]:
        return [n for n in self.dag.nodes if self.dag.in_degree(n) == 0]

    def leaves(self) -> list[str]:
        return [n for n in self.dag.nodes if self.dag.out_degree(n) == 0]

    def topo_order(self) -> list[str]:
        return list(nx.topological_sort(self.dag))

    def execution_layers(self) -> list[list[str]]:
        """Group nodes into layers that can run in parallel."""
        return [sorted(layer) for layer in nx.topological_generations(self.dag)]


def build_graph(project: Project) -> TaskGraph:
    """Validate the project and build its task graph.

    Nested subtasks are flattened into a single global DAG. Nesting is
    purely a human-readable grouping; every declaration is a peer for the
    purposes of dependency resolution and code generation.

    Additionally, every subtask/subcomponent gets an implicit edge from its
    parent so the parent scaffolds first — matches the reader's intuition
    that "Login can't ship before Auth is defined."
    """

    _check_goals(project)

    all_decls = project.all_declarations()

    dag: nx.DiGraph = nx.DiGraph()
    for decl in all_decls:
        dag.add_node(decl.name, decl=decl)

    known: set[str] = {d.name for d in all_decls}

    # Explicit edges from `depends` / `uses` fields.
    for decl in all_decls:
        for target in _edges_from(decl):
            if target not in known:
                raise GraphError(
                    f"'{decl.name}' references unknown name '{target}'."
                )
            if target == decl.name:
                raise GraphError(f"'{decl.name}' cannot depend on itself.")
            dag.add_edge(target, decl.name)

    # Implicit edges: parent -> subtask/subcomponent.
    for decl in all_decls:
        for sub in (*decl.subtasks, *decl.subcomponents):
            dag.add_edge(decl.name, sub.name)

    try:
        cycle = nx.find_cycle(dag, orientation="original")
    except nx.NetworkXNoCycle:
        cycle = None
    if cycle:
        chain = " -> ".join(edge[0] for edge in cycle) + " -> " + cycle[-1][1]
        raise GraphError(f"Dependency cycle detected: {chain}.")

    return TaskGraph(project=project.name, dag=dag)


def _check_goals(project: Project) -> None:
    for d in project.all_declarations():
        if d.goal is None:
            kind = "task" if isinstance(d, Task) else "component"
            raise GraphError(f"{kind} '{d.name}' is missing a 'goal' field.")


def _edges_from(decl: Declaration) -> list[str]:
    edges: list[str] = []
    if isinstance(decl, Task):
        edges.extend(decl.depends)
    elif isinstance(decl, Component):
        edges.extend(decl.uses)
        edges.extend(decl.depends)
    return edges
