import heapq


def topo_sort(deps):
    if not isinstance(deps, dict):
        raise TypeError("deps must be a dict")
    # Collect every node (keys + values in the dep lists). Implicit leaves have
    # no key and default to no dependencies.
    graph = {k: list(v) for k, v in deps.items()}
    for v in deps.values():
        for d in v:
            graph.setdefault(d, [])

    # In-degree = how many nodes depend on this node? Actually for Kahn we need
    # the opposite: in-degree = number of unresolved dependencies of this node.
    indeg = {n: 0 for n in graph}
    for n, ds in graph.items():
        indeg[n] = len(ds)
    # Reverse adjacency: for each dep d, who depends on it?
    dependents = {n: [] for n in graph}
    for n, ds in graph.items():
        for d in ds:
            dependents[d].append(n)

    ready = [n for n, deg in indeg.items() if deg == 0]
    heapq.heapify(ready)   # alphabetical tie-break
    out = []
    while ready:
        n = heapq.heappop(ready)
        out.append(n)
        for m in dependents[n]:
            indeg[m] -= 1
            if indeg[m] == 0:
                heapq.heappush(ready, m)
    if len(out) != len(graph):
        raise ValueError("cycle detected")
    return out
