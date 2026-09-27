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
from graphnode.storage import find_graph_file, init_graph, load_graph, save_graph
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
    """Normalize subcommands (e.g. 'add' -> '-add', 'connect' -> '-connect', 'show' -> '-show')."""
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
    }
    for arg in argv:
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

    # Handle -init
    if args.init is not None:
        graph, path = init_graph(file_path=target_file, name=args.init)
        print(f"✨ Initialized new system graph '{graph.name}' at: {path}")
        return 0

    # Load active graph
    try:
        graph, path = load_graph(file_path=target_file)
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
