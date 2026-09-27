"""Command-line interface for GraphNode."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from graphnode.export import (
    export_dot,
    export_graph_to_file,
    export_markdown,
    export_mermaid,
)
from graphnode.graph import GraphError, NodeExistsError, NodeNotFoundError
from graphnode.render import render_card, render_flow, render_tree
from graphnode.storage import (
    create_named_graph,
    delete_named_graph,
    find_graph_file,
    get_active_graph_name,
    init_graph,
    list_named_graphs,
    load_graph,
    resolve_graph_target,
    save_graph,
    set_active_graph_name,
)
from graphnode.version import __version__


def create_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser supporting both flag-style and positional subcommands."""
    parser = argparse.ArgumentParser(
        prog="graphnode",
        description="GraphNode: Command-line system architecture graph and dependency tree builder.",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    # Core actions (supporting flag style like -add, -connect, -show)
    action_group = parser.add_argument_group("Commands")

    action_group.add_argument(
        "-create",
        metavar="GRAPH_NAME",
        help="Create a new named graph and register its CLI shortcut command.",
    )
    action_group.add_argument(
        "-use",
        metavar="GRAPH_NAME",
        help="Switch active graph in the global registry.",
    )
    action_group.add_argument(
        "-graphs",
        action="store_true",
        help="List all registered named graphs and metrics.",
    )
    action_group.add_argument(
        "-delete-graph",
        metavar="GRAPH_NAME",
        help="Delete a named graph and remove its CLI shortcut command.",
    )
    action_group.add_argument(
        "-add",
        "-a",
        "--add",
        nargs="+",
        metavar="NODE_NAME",
        help="Add one or more nodes to the system graph (e.g. -add api_gateway auth_service).",
    )
    action_group.add_argument(
        "-connect",
        "-c",
        "--connect",
        nargs="+",
        metavar=("FROM", "TO"),
        help="Connect two nodes with a directed edge (e.g. -connect api_gateway auth_service).",
    )
    action_group.add_argument(
        "-disconnect",
        nargs=2,
        metavar=("FROM", "TO"),
        help="Remove connection between two nodes.",
    )
    action_group.add_argument(
        "-remove",
        "-rm",
        "--remove",
        metavar="NODE_NAME",
        help="Remove a node and its connections from the graph.",
    )
    action_group.add_argument(
        "-show",
        "-s",
        "--show",
        nargs="?",
        const="tree",
        choices=["tree", "card", "flow"],
        help="Visualize the system tree or architecture in the terminal (default: tree).",
    )
    action_group.add_argument(
        "-list",
        "-l",
        "--list",
        action="store_true",
        help="List all components, types, and connectivity summary.",
    )
    action_group.add_argument(
        "-status",
        action="store_true",
        help="Display graph metrics (total nodes, edges, entry points, cycles).",
    )
    action_group.add_argument(
        "-export",
        nargs="?",
        const="mermaid",
        choices=["mermaid", "dot", "markdown", "json"],
        help="Export graph to Mermaid, Graphviz DOT, Markdown, or JSON.",
    )
    action_group.add_argument(
        "-init",
        nargs="?",
        const="system",
        metavar="GRAPH_NAME",
        help="Initialize a new .graphnode.json file in the current directory.",
    )
    action_group.add_argument(
        "-clear",
        action="store_true",
        help="Clear all nodes and edges from the current graph.",
    )

    # Modifiers & options
    option_group = parser.add_argument_group("Options")
    option_group.add_argument(
        "-g",
        "--graph",
        metavar="GRAPH_NAME",
        help="Target a specific named graph or graph file.",
    )
    option_group.add_argument(
        "-type",
        "-t",
        "--type",
        default="service",
        help="Component type for -add (e.g. service, db, queue, gateway, cache, client).",
    )
    option_group.add_argument(
        "-label",
        help="Relationship or protocol label for -connect (e.g. HTTP, gRPC, queries, pub/sub).",
    )
    option_group.add_argument(
        "-desc",
        "--desc",
        default="",
        help="Optional description for the node.",
    )
    option_group.add_argument(
        "-o",
        "--output",
        metavar="FILE_PATH",
        help="Output destination path for -export.",
    )
    option_group.add_argument(
        "-f",
        "--file",
        metavar="FILE_PATH",
        help="Target a specific .json graph file instead of default project file.",
    )
    option_group.add_argument(
        "--force",
        action="store_true",
        help="Force operation without prompt (e.g. for -clear or overwriting nodes).",
    )
    option_group.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"graphnode {__version__}",
    )

    return parser


def normalize_argv(argv: Sequence[str]) -> list[str]:
    """Normalize subcommands and route named graph shortcuts."""
    normalized: list[str] = []
    subcommand_map = {
        "add": "-add",
        "connect": "-connect",
        "disconnect": "-disconnect",
        "remove": "-remove",
        "rm": "-remove",
        "show": "-show",
        "list": "-list",
        "ls": "-list",
        "status": "-status",
        "export": "-export",
        "init": "-init",
        "clear": "-clear",
        "create": "-create",
        "use": "-use",
        "graphs": "-graphs",
        "delete-graph": "-delete-graph",
    }

    # If first argument is a registered graph name (e.g. graphnode graph1 -add node1)
    named = list_named_graphs()
    if argv and argv[0] in named:
        normalized.extend(["-g", argv[0]])
        remaining = argv[1:]
    else:
        remaining = argv

    for arg in remaining:
        if arg in subcommand_map:
            normalized.append(subcommand_map[arg])
        else:
            normalized.append(arg)
    return normalized


def run(argv: Sequence[str] | None = None) -> int:
    """Execute the GraphNode CLI dispatcher."""
    raw_args = list(argv) if argv is not None else sys.argv[1:]

    # If no arguments provided, show brief help or current graph
    if not raw_args:
        parser = create_parser()
        parser.print_help()
        return 0

    normalized_args = normalize_argv(raw_args)
    parser = create_parser()
    args = parser.parse_args(normalized_args)

    target_file = Path(args.file).resolve() if args.file else None

    # Handle -create
    if args.create:
        try:
            graph, gfile, bin_path = create_named_graph(args.create)
            print(f"✨ Created new graph '{graph.name}'")
            print(f"📦 Graph storage : {gfile}")
            if bin_path:
                print(f"🚀 CLI command   : {bin_path.name}")
            print(f"Active graph set to '{graph.name}'.")
            print(f"\nYou can now run directly:")
            print(f"  {args.create} -add <node_name>")
            print(f"  {args.create} -connect <node1> <node2>")
            print(f"  {args.create} -show")
            return 0
        except ValueError as exc:
            sys.stderr.write(f"Error: {exc}\n")
            return 1

    # Handle -use
    if args.use:
        named_graphs = list_named_graphs()
        if args.use not in named_graphs:
            sys.stderr.write(f"Error: Graph '{args.use}' does not exist. Use '-create {args.use}' first.\n")
            return 1
        set_active_graph_name(args.use)
        print(f"Active graph set to '{args.use}'.")
        return 0

    # Handle -graphs
    if args.graphs:
        named_graphs = list_named_graphs()
        active = get_active_graph_name()
        width = 65
        div = "=" * width
        inner_width = width - 4
        lines = [
            div,
            f"|{'GRAPHNODE REGISTRY'.center(width - 2)}|",
            div,
        ]
        if not named_graphs:
            lines.append(f"| {'No named graphs registered yet. Use -create <name>'.ljust(inner_width)} |")
        else:
            for gname, gpath in named_graphs.items():
                is_active = (gname == active)
                star = " (active)" if is_active else ""
                try:
                    g, _ = load_graph(gpath)
                    info = f"{len(g.nodes)} nodes, {len(g.get_all_edges())} connections"
                except Exception:
                    info = "unknown"
                entry = f"• {gname}{star} : {info}"
                lines.append(f"| {entry.ljust(inner_width)} |")
        lines.append(div)
        print("\n".join(lines))
        return 0

    # Handle -delete-graph
    if args.delete_graph:
        if delete_named_graph(args.delete_graph):
            print(f"Deleted graph '{args.delete_graph}' and removed CLI shortcut command.")
            return 0
        else:
            sys.stderr.write(f"Error: Graph '{args.delete_graph}' not found.\n")
            return 1

    # Handle -init
    if args.init is not None:
        graph, path = init_graph(file_path=target_file, name=args.init)
        print(f"✨ Initialized new system graph '{graph.name}' at: {path}")
        return 0

    # Resolve and load active graph
    try:
        graph, path = resolve_graph_target(graph_name=args.graph, file_path=target_file)
    except Exception as exc:
        sys.stderr.write(f"Error: {exc}\n")
        return 1

    changed = False

    # Handle -clear
    if args.clear:
        graph.clear()
        save_graph(graph, path)
        print(f"🧹 Cleared all nodes and edges from graph '{graph.name}' ({path}).")
        return 0

    # Handle -add
    if args.add:
        added_count = 0
        for name in args.add:
            try:
                graph.add_node(
                    name=name,
                    node_type=args.type,
                    description=args.desc,
                    overwrite=args.force,
                )
                added_count += 1
                icon = "🔹"
                print(f"Added node: [{name}] (type: {args.type})")
            except NodeExistsError as exc:
                print(f"Notice: {exc} (use --force to overwrite)")
            except ValueError as exc:
                sys.stderr.write(f"Error: {exc}\n")
                return 1

        if added_count > 0:
            changed = True

    # Handle -connect
    if args.connect:
        if len(args.connect) < 2:
            sys.stderr.write("Error: -connect requires at least 2 arguments: <FROM> <TO>\n")
            return 1
        src = args.connect[0]
        targets = args.connect[1:]
        label = args.label or ""

        for dst in targets:
            try:
                graph.connect(src, dst, label=label, auto_create=False)
                lbl_str = f" via ({label})" if label else ""
                print(f"Connected: [{src}] ──▶ [{dst}]{lbl_str}")
                changed = True
            except NodeNotFoundError as exc:
                sys.stderr.write(f"Error: {exc}\n")
                return 1

    # Handle -disconnect
    if args.disconnect:
        src, dst = args.disconnect
        if graph.disconnect(src, dst):
            print(f"Disconnected: [{src}] ──X── [{dst}]")
            changed = True
        else:
            print(f"Notice: No connection existed between [{src}] and [{dst}].")

    # Handle -remove
    if args.remove:
        if graph.remove_node(args.remove):
            print(f"Removed node: [{args.remove}] and its incident connections.")
            changed = True
        else:
            sys.stderr.write(f"Error: Node '{args.remove}' not found.\n")
            return 1

    # Persist changes if any mutation occurred
    if changed:
        save_graph(graph, path)

    # Handle -show
    if args.show:
        mode = args.show.lower() if isinstance(args.show, str) else "tree"
        if mode == "card":
            print(render_card(graph))
        elif mode == "flow":
            print(render_flow(graph))
        else:
            print(render_tree(graph))
        return 0

    # Handle -list
    if args.list:
        print(render_card(graph))
        return 0

    # Handle -status
    if args.status:
        roots = graph.get_roots()
        leaves = graph.get_leaves()
        isolated = graph.get_isolated()
        cycles = graph.find_cycles()
        print(f"Graph: {graph.name} ({path})")
        print(f"• Nodes        : {len(graph.nodes)}")
        print(f"• Connections  : {len(graph.get_all_edges())}")
        print(f"• Entry Points : {', '.join(roots) if roots else 'None'}")
        print(f"• Sinks/Leaves : {', '.join(leaves) if leaves else 'None'}")
        print(f"• Isolated     : {', '.join(isolated) if isolated else 'None'}")
        print(f"• Cycles       : {len(cycles)}")
        return 0

    # Handle -export
    if args.export:
        fmt = args.export.lower()
        if args.output:
            out_file = export_graph_to_file(graph, fmt, args.output)
            print(f"Exported graph to {fmt.upper()} at: {out_file}")
        else:
            if fmt == "dot":
                print(export_dot(graph))
            elif fmt == "markdown":
                print(export_markdown(graph))
            else:
                print(export_mermaid(graph))
        return 0

    return 0


def main() -> None:
    """Entry point for the console script."""
    sys.exit(run())


if __name__ == "__main__":
    main()
