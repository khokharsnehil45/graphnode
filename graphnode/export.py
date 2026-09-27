"""Export utilities for GraphNode (Mermaid, Graphviz DOT, Markdown, JSON)."""

from __future__ import annotations

import json
from pathlib import Path
from graphnode.graph import SystemGraph


def export_mermaid(graph: SystemGraph, direction: str = "TD") -> str:
    """Export the system graph to a Mermaid flowchart definition.

    Args:
        graph: SystemGraph to export.
        direction: Flowchart orientation ('TD', 'LR', etc.).

    Returns:
        Mermaid markdown code block.
    """
    lines: list[str] = [f"graph {direction}"]

    # Define nodes with styling/shapes based on type
    for node_name in sorted(graph.nodes.keys()):
        node = graph.nodes[node_name]
        ntype = node.node_type.lower()
        if ntype in ("db", "database"):
            # Cylinder shape in Mermaid: [(name)]
            lines.append(f'    {node_name}[("{node.name} <br/> <i>{node.node_type}</i>")]')
        elif ntype in ("queue", "broker"):
            # Queue/subroutine shape
            lines.append(f'    {node_name}[["{node.name} <br/> <i>{node.node_type}</i>"]]')
        elif ntype in ("gateway", "api"):
            # Hexagon or rounded
            lines.append(f'    {node_name}{{"{node.name} <br/> <i>{node.node_type}</i>"}}')
        else:
            # Rounded rectangle
            lines.append(f'    {node_name}["{node.name} <br/> <i>{node.node_type}</i>"]')

    # Define connections
    edges = graph.get_all_edges()
    for edge in edges:
        if edge.label:
            lines.append(f'    {edge.source} -->|"{edge.label}"| {edge.target}')
        else:
            lines.append(f"    {edge.source} --> {edge.target}")

    return "\n".join(lines)


def export_dot(graph: SystemGraph) -> str:
    """Export the system graph to Graphviz DOT format.

    Args:
        graph: SystemGraph to export.

    Returns:
        DOT formatted string.
    """
    lines: list[str] = [
        f'digraph "{graph.name}" {{',
        "    rankdir=LR;",
        '    node [shape=box, style="rounded,filled", fillcolor="#f0f4f8", fontname="Helvetica"];',
        '    edge [fontname="Helvetica", fontsize=10];',
    ]

    for node_name in sorted(graph.nodes.keys()):
        node = graph.nodes[node_name]
        label = f"{node.name}\\n({node.node_type})"
        lines.append(f'    "{node_name}" [label="{label}"];')

    for edge in graph.get_all_edges():
        if edge.label:
            lines.append(f'    "{edge.source}" -> "{edge.target}" [label="{edge.label}"];')
        else:
            lines.append(f'    "{edge.source}" -> "{edge.target}";')

    lines.append("}")
    return "\n".join(lines)


def export_markdown(graph: SystemGraph) -> str:
    """Export the system graph as a comprehensive Markdown report."""
    mermaid_block = export_mermaid(graph)
    edges = graph.get_all_edges()

    lines: list[str] = [
        f"# System Architecture: {graph.name}",
        "",
        "## Architecture Diagram",
        "",
        "```mermaid",
        mermaid_block,
        "```",
        "",
        "## Components",
        "",
        "| Name | Type | Description | In-Degree | Out-Degree |",
        "| :--- | :--- | :--- | :---: | :---: |",
    ]

    for name in sorted(graph.nodes.keys()):
        node = graph.nodes[name]
        desc = node.description or "-"
        lines.append(
            f"| `{node.name}` | `{node.node_type}` | {desc} | {graph.in_degree(name)} | {graph.out_degree(name)} |"
        )

    lines.extend([
        "",
        "## Connections",
        "",
        "| Source | Protocol / Relation | Target |",
        "| :--- | :--- | :--- |",
    ])

    for edge in edges:
        lbl = edge.label or "connects to"
        lines.append(f"| `{edge.source}` | `{lbl}` | `{edge.target}` |")

    return "\n".join(lines)


def export_graph_to_file(graph: SystemGraph, fmt: str, output_path: str | Path) -> Path:
    """Export graph to a specific format and save to disk."""
    out = Path(output_path).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    fmt_lower = fmt.lower().strip()

    if fmt_lower in ("mermaid", "mmd"):
        content = export_mermaid(graph)
    elif fmt_lower in ("dot", "gv"):
        content = export_dot(graph)
    elif fmt_lower in ("markdown", "md"):
        content = export_markdown(graph)
    elif fmt_lower in ("json",):
        content = json.dumps(graph.to_dict(), indent=2)
    else:
        raise ValueError(f"Unsupported export format '{fmt}'. Choose from: mermaid, dot, markdown, json.")

    out.write_text(content + "\n", encoding="utf-8")
    return out
