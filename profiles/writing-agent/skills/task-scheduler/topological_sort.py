"""
Topological Sort Module
DAG dependency resolution with cycle detection.
"""



class CyclicDependencyError(Exception):
    """Raised when task dependencies contain a cycle."""


def topological_sort(dependencies: dict[str, list[str]]) -> list[str]:
    """
    Perform topological sort on dependency graph.

    Args:
        dependencies: Dict mapping node -> list of prerequisite nodes

    Returns:
        List of nodes in dependency order (prerequisites first)

    Raises:
        CyclicDependencyError if graph contains cycles
    """
    visited = set()
    temp = set()
    result = []

    def visit(node):
        if node in temp:
            raise CyclicDependencyError(f"Cyclic dependency detected at {node}")
        if node not in visited:
            temp.add(node)
            for dep in dependencies.get(node, []):
                visit(dep)
            temp.remove(node)
            visited.add(node)
            result.append(node)

    for node in dependencies:
        if node not in visited:
            visit(node)

    return result


def find_execution_order(task_ids: list[str], dependencies: dict[str, list[str]]) -> list[list[str]]:
    """
    Determine optimal execution order respecting dependencies.

    Returns list of "layers" where tasks in the same layer can run in parallel.
    """
    # Build full graph including all nodes
    all_nodes = set(task_ids)
    for deps in dependencies.values():
        all_nodes.update(deps)

    # Build dependency graph (node -> list of nodes that depend on it)
    dependents = {node: [] for node in all_nodes}
    for task_id, deps in dependencies.items():
        for dep in deps:
            if dep in dependents:
                dependents[dep].append(task_id)

    # Calculate in-degree (number of unsatisfied dependencies)
    in_degree = {}
    for node in all_nodes:
        in_degree[node] = len([d for d in dependencies.get(node, []) if d in all_nodes])

    # Kahn's algorithm for layered scheduling
    layers = []
    remaining = set(all_nodes)

    while remaining:
        # Find nodes with zero in-degree (ready to run)
        layer = [node for node in remaining if in_degree.get(node, 0) == 0 and node in task_ids]

        if not layer:
            # Cycle detected
            raise CyclicDependencyError("No schedulable tasks found - cyclic dependency")

        layers.append(layer)

        # Remove layer nodes and update in-degrees
        for node in layer:
            remaining.remove(node)
            for dependent in dependents.get(node, []):
                if dependent in in_degree:
                    in_degree[dependent] -= 1

    return layers
