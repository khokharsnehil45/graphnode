"""Terminal visualization and rendering for GraphNode system trees and graphs."""

from __future__ import annotations

from typing import Sequence
from graphnode.graph import SystemGraph

# Type badges/icons for standard architecture components
TYPE_ICONS: dict[str, str] = {
    "gateway": "🌐",
    "service": "⚙️ ",
    "api": "🔌",
    "db": "💾",
    "database": "💾",
    "queue": "📬",
    "cache": "⚡",
    "client": "💻",
    "worker": "🔨",
    "frontend": "🖥️ ",
    "backend": "⚙️ ",
    "broker": "📨",
    "storage": "📦",
    "custom": "🔹",
}


def get_node_label(graph: SystemGraph, node_name: str) -> str:
    """Format a node name with its component type badge."""
    node = graph.get_node(node_name)
    if not node:
        return f"[{node_name}]"
    icon = TYPE_ICONS.get(node.node_type.lower(), "🔹")
    return f"{icon} [{node.name}] ({node.node_type})"


def render_tree(graph: SystemGraph) -> str:
    """Render the graph as an ASCII/Unicode hierarchy tree starting from root entry points.

    Handles cycles safely by tracking visited ancestors in the current traversal path.

    Args:
        graph: The SystemGraph to render.

    Returns:
        Formatted multi-line tree string.
    """
    if not graph.nodes:
        return "Graph is empty. Add nodes with 'graphnode -add <name>'."

    lines: list[str] = []
    roots = graph.get_roots()
    isolated = set(graph.get_isolated())

    # Connected roots (roots that have outgoing edges)
    connected_roots = [r for r in roots if r not in isolated]

    lines.append(f"📦 System Graph: {graph.name}")
    lines.append(f"   Nodes: {len(graph.nodes)} | Connections: {len(graph.get_all_edges())}")
    lines.append("───────────────────────────────────────────────────────")

    visited_globally: set[str] = set()

    def walk_tree(
        node_name: str,
        prefix: str = "",
        is_last: bool = True,
        path: set[str] | None = None,
    ) -> None:
        current_path = set(path) if path else set()
        visited_globally.add(node_name)

        connector = "└── " if is_last else "├── "
        node_repr = get_node_label(graph, node_name)

        if node_name in current_path:
            lines.append(f"{prefix}{connector}{node_repr} 🔄 (cycle detected)")
            return

        lines.append(f"{prefix}{connector}{node_repr}")
        current_path.add(node_name)

        child_prefix = prefix + ("    " if is_last else "│   ")
        children = sorted(graph.adj.get(node_name, {}).keys())

        for idx, child in enumerate(children):
            child_is_last = idx == len(children) - 1
            edge = graph.adj[node_name][child]
            label_tag = f" ──({edge.label})──▶ " if edge.label else " ──▶ "

            if child in current_path:
                lines.append(
                    f"{child_prefix}{'└── ' if child_is_last else '├── '}{label_tag}{get_node_label(graph, child)} 🔄 (cycle)"
                )
                continue

            # Print edge label on tree link if present
            c_conn = "└── " if child_is_last else "├── "
            child_repr = get_node_label(graph, child)
            if edge.label:
                lines.append(f"{child_prefix}{c_conn}──({edge.label})──▶ {child_repr}")
                new_prefix = child_prefix + ("    " if child_is_last else "│   ")
                grand_children = sorted(graph.adj.get(child, {}).keys())
                for g_idx, g_child in enumerate(grand_children):
                    walk_tree(
                        g_child,
                        prefix=new_prefix,
                        is_last=(g_idx == len(grand_children) - 1),
                        path=current_path | {child},
                    )
            else:
                walk_tree(
                    child,
                    prefix=child_prefix,
                    is_last=child_is_last,
                    path=current_path,
                )

    # Render from all connected roots
    if connected_roots:
        for idx, root in enumerate(connected_roots):
            walk_tree(root, is_last=(idx == len(connected_roots) - 1 and not isolated))
    elif not isolated:
        # If every node is in a cycle with no clear root
        arbitrary_root = sorted(graph.nodes.keys())[0]
        walk_tree(arbitrary_root, is_last=True)

    # Any remaining unvisited connected nodes (e.g. disconnected components)
    remaining_connected = sorted(
        [n for n in graph.nodes if n not in visited_globally and n not in isolated]
    )
    for rem in remaining_connected:
        if rem not in visited_globally:
            walk_tree(rem, prefix="", is_last=True)

    # Isolated nodes
    if isolated:
        lines.append("")
        lines.append("🔹 Standalone / Isolated Nodes:")
        for iso in sorted(isolated):
            lines.append(f"   • {get_node_label(graph, iso)}")

    return "\n".join(lines)


def render_card(graph: SystemGraph, width: int = 65) -> str:
    """Render comprehensive system architecture card framed in pipes (|) and == dividers.

    Args:
        graph: The SystemGraph to render.
        width: Character width for card formatting.

    Returns:
        Formatted card string.
    """
    div = "=" * width
    inner_width = width - 4
    subdiv = "|" + "-" * (width - 2) + "|"

    roots = graph.get_roots()
    leaves = graph.get_leaves()
    cycles = graph.find_cycles()

    header_lines = [
        div,
        f"|{'SYSTEM ARCHITECTURE GRAPH'.center(width - 2)}|",
        div,
        f"| {f'Graph Name    : {graph.name}'.ljust(inner_width)} |",
        f"| {f'Total Nodes   : {len(graph.nodes)}'.ljust(inner_width)} |",
        f"| {f'Total Edges   : {len(graph.get_all_edges())}'.ljust(inner_width)} |",
        f"| {f'Entry Points  : {', '.join(roots) if roots else 'None'}'.ljust(inner_width)} |",
        f"| {f'Sinks/Leaves  : {', '.join(leaves) if leaves else 'None'}'.ljust(inner_width)} |",
        f"| {f'Cycles Found  : {len(cycles)}'.ljust(inner_width)} |",
        div,
    ]

    body_lines: list[str] = []

    if not graph.nodes:
        body_lines.append(f"| {'Graph is empty.'.ljust(inner_width)} |")
    else:
        for node_name in sorted(graph.nodes.keys()):
            node = graph.nodes[node_name]
            outgoing = graph.adj.get(node_name, {})
            incoming = graph.rev_adj.get(node_name, set())

            body_lines.append(f"| {f'[{node.name}]  ({node.node_type})'.ljust(inner_width)} |")
            if node.description:
                body_lines.append(f"| {f'  Desc: {node.description}'.ljust(inner_width)} |")

            # Outgoing connections
            if outgoing:
                conn_strs = [
                    f"{dst} [{edge.label}]" if edge.label else dst
                    for dst, edge in sorted(outgoing.items())
                ]
                body_lines.append(f"| {f'  ──▶ Outgoing ({len(outgoing)}) : {', '.join(conn_strs)}'.ljust(inner_width)} |")
            else:
                body_lines.append(f"| {f'  ──▶ Outgoing : (None - Leaf)'.ljust(inner_width)} |")

            # Incoming connections
            if incoming:
                body_lines.append(f"| {f'  ◀── Incoming ({len(incoming)}) : {', '.join(sorted(incoming))}'.ljust(inner_width)} |")

            body_lines.append(subdiv)

    # Trim last subdiv if present
    if body_lines and body_lines[-1] == subdiv:
        body_lines[-1] = div
    else:
        body_lines.append(div)

    return "\n".join(header_lines + body_lines)


def render_flow(graph: SystemGraph) -> str:
    """Render a flat list of direct connections in arrow format."""
    edges = graph.get_all_edges()
    if not edges:
        if not graph.nodes:
            return "Graph is empty."
        return "No connections exist yet. Use 'graphnode -connect <node1> <node2>'."

    lines: list[str] = [f"Connections in {graph.name}:"]
    for edge in edges:
        label_part = f" ──({edge.label})──▶ " if edge.label else " ──▶ "
        lines.append(f"  {edge.source}{label_part}{edge.target}")

    return "\n".join(lines)
