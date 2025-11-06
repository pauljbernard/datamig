#!/usr/bin/env python3
"""
Schema Analyzer

Analyzes database schemas, builds dependency graphs, and performs topological sorting
for determining extraction order.

Input: JSON from stdin with schema information
Output: JSON to stdout with dependency graph and extraction order
"""

import json
import sys
from collections import defaultdict, deque
from typing import Dict, List, Set, Tuple

def build_dependency_graph(schema: Dict) -> Dict[str, List[str]]:
    """
    Build a directed dependency graph from foreign key relationships.

    Args:
        schema: Schema dictionary with tables and foreign keys

    Returns:
        Dictionary mapping parent_table -> [child_tables]
    """
    graph = defaultdict(list)

    for store_name, store_data in schema.get('data_stores', {}).items():
        if store_data.get('type') != 'postgresql':
            continue

        for table in store_data.get('tables', []):
            table_name = f"{store_name}.{table['schema']}.{table['name']}"

            # Add table as node (even if no FKs)
            if table_name not in graph:
                graph[table_name] = []

            # Add edges for foreign keys (child -> parent)
            for fk in table.get('foreign_keys', []):
                parent_table = f"{store_name}.{fk['foreign_table_schema']}.{fk['foreign_table_name']}"
                # Parent must be extracted before child
                graph[parent_table].append(table_name)

    return dict(graph)


def find_cycles(graph: Dict[str, List[str]]) -> List[List[str]]:
    """
    Detect circular dependencies in the dependency graph using DFS.

    Args:
        graph: Dependency graph

    Returns:
        List of cycles, where each cycle is a list of tables
    """
    visited = set()
    rec_stack = set()
    cycles = []

    def dfs(node: str, path: List[str]):
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                dfs(neighbor, path.copy())
            elif neighbor in rec_stack:
                # Found a cycle
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:] + [neighbor]
                cycles.append(cycle)

        rec_stack.remove(node)

    for node in graph:
        if node not in visited:
            dfs(node, [])

    return cycles


def topological_sort(graph: Dict[str, List[str]]) -> Tuple[List[str], bool]:
    """
    Perform topological sort using Kahn's algorithm.

    Args:
        graph: Dependency graph (parent -> children)

    Returns:
        Tuple of (sorted_order, has_cycle)
        - sorted_order: Topologically sorted list of tables
        - has_cycle: True if graph contains cycles
    """
    # Calculate in-degree for each node
    in_degree = {node: 0 for node in graph}

    # Count all nodes that appear as children
    all_nodes = set(graph.keys())
    for children in graph.values():
        for child in children:
            all_nodes.add(child)
            if child not in in_degree:
                in_degree[child] = 0

    # Count in-degrees
    for node in graph:
        for child in graph[node]:
            in_degree[child] += 1

    # Queue of nodes with no dependencies
    queue = deque([node for node in in_degree if in_degree[node] == 0])
    result = []

    while queue:
        node = queue.popleft()
        result.append(node)

        # Reduce in-degree of child nodes
        for child in graph.get(node, []):
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)

    # Check if all nodes were processed (no cycle) or if cycle exists
    has_cycle = len(result) != len(all_nodes)

    return result, has_cycle


def suggest_break_point(cycle: List[str], graph: Dict[str, List[str]]) -> Dict:
    """
    Suggest an optimal break point for a circular dependency.

    Strategy: Break at the FK with least impact (fewest downstream dependencies)

    Args:
        cycle: List of tables in the cycle
        graph: Full dependency graph

    Returns:
        Dictionary with break point suggestion
    """
    # Count dependencies for each table in cycle
    dep_counts = {}
    for table in cycle[:-1]:  # Exclude duplicate last element
        dep_count = len(graph.get(table, []))
        dep_counts[table] = dep_count

    # Suggest breaking at table with fewest dependencies
    break_table = min(dep_counts, key=dep_counts.get)
    next_idx = cycle.index(break_table) + 1
    if next_idx >= len(cycle) - 1:
        next_idx = 0
    break_to = cycle[next_idx]

    return {
        'break_from': break_table,
        'break_to': break_to,
        'strategy': f"Extract {break_to} first without validating FK from {break_table}",
        'impact': f"Affects {dep_counts[break_table]} downstream tables"
    }


def generate_dot_graph(graph: Dict[str, List[str]], output_file: str):
    """
    Generate GraphViz DOT file for visualization.

    Args:
        graph: Dependency graph
        output_file: Path to output .dot file
    """
    with open(output_file, 'w') as f:
        f.write("digraph dependencies {\n")
        f.write("  rankdir=LR;\n")
        f.write("  node [shape=box];\n\n")

        # Write edges
        for parent, children in graph.items():
            parent_label = parent.split('.')[-1]  # Just table name
            for child in children:
                child_label = child.split('.')[-1]
                f.write(f'  "{parent_label}" -> "{child_label}";\n')

        f.write("}\n")


def main():
    try:
        # Read input from stdin
        input_data = json.load(sys.stdin)

        # Build dependency graph
        graph = build_dependency_graph(input_data)

        # Find circular dependencies
        cycles = find_cycles(graph)

        # Perform topological sort
        extraction_order, has_cycle = topological_sort(graph)

        # Generate break point suggestions for cycles
        cycle_info = []
        for cycle in cycles:
            break_point = suggest_break_point(cycle, graph)
            cycle_info.append({
                'tables': cycle,
                'break_point': break_point
            })

        # Organize extraction order by store
        extraction_by_store = defaultdict(list)
        for table in extraction_order:
            parts = table.split('.')
            if len(parts) >= 2:
                store = parts[0]
                table_name = '.'.join(parts[1:])
                extraction_by_store[store].append(table_name)

        # Build output
        result = {
            'success': True,
            'dependency_graph': graph,
            'extraction_order': extraction_order,
            'extraction_by_store': dict(extraction_by_store),
            'circular_dependencies': cycle_info,
            'has_cycles': has_cycle,
            'total_tables': len(extraction_order),
            'total_relationships': sum(len(children) for children in graph.values())
        }

        # Write output to stdout
        json.dump(result, sys.stdout, indent=2)
        sys.exit(0)

    except Exception as e:
        error_result = {
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }
        json.dump(error_result, sys.stdout, indent=2)
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
