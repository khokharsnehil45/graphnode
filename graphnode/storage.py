"""Storage and project-level persistence for GraphNode."""

from __future__ import annotations

import json
from pathlib import Path

from graphnode.graph import SystemGraph

DEFAULT_GRAPH_FILENAME = ".graphnode.json"
CONFIG_DIR = Path.home() / ".config" / "graphnode"
GRAPHS_DIR = CONFIG_DIR / "graphs"
ACTIVE_GRAPH_FILE = CONFIG_DIR / "active_graph"
BIN_DIR = Path.home() / ".local" / "bin"

RESERVED_NAMES = {
    "node",
    "graphnode",
    "gnode",
    "python",
    "python3",
    "bash",
    "sh",
    "zsh",
    "git",
    "ls",
    "cd",
    "rm",
    "cp",
    "mv",
    "cat",
    "grep",
    "find",
    "sudo",
    "apt",
}


def get_graphs_dir() -> Path:
    """Return and ensure directory for named graphs."""
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    return GRAPHS_DIR


def get_active_graph_name() -> str | None:
    """Return currently active named graph, if configured."""
    if ACTIVE_GRAPH_FILE.is_file():
        name = ACTIVE_GRAPH_FILE.read_text(encoding="utf-8").strip()
        if name:
            return name
    return None


def set_active_graph_name(name: str) -> None:
    """Set the active named graph."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    ACTIVE_GRAPH_FILE.write_text(name.strip() + "\n", encoding="utf-8")


def list_named_graphs() -> dict[str, Path]:
    """List all registered named graphs."""
    gdir = get_graphs_dir()
    graphs: dict[str, Path] = {}
    for p in sorted(gdir.glob("*.json")):
        graphs[p.stem] = p
    return graphs


def install_graph_binary(name: str) -> Path:
    """Create an executable runner script in ~/.local/bin/<name>."""
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    bin_path = BIN_DIR / name
    script_content = f"""#!/bin/sh
exec graphnode -g "{name}" "$@"
"""
    bin_path.write_text(script_content, encoding="utf-8")
    bin_path.chmod(0o755)
    return bin_path


def uninstall_graph_binary(name: str) -> bool:
    """Remove runner script from ~/.local/bin/<name>."""
    bin_path = BIN_DIR / name
    if bin_path.is_file():
        bin_path.unlink()
        return True
    return False


def create_named_graph(name: str) -> tuple[SystemGraph, Path, Path]:
    """Create a new named graph and register its CLI shortcut command in ~/.local/bin.

    Args:
        name: Name of the graph (also becomes the command name).

    Returns:
        Tuple of (SystemGraph, graph file Path, runner script Path).
    """
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("Graph name cannot be empty.")
    if clean_name.lower() in RESERVED_NAMES:
        raise ValueError(f"'{clean_name}' is a reserved system command name.")

    gdir = get_graphs_dir()
    graph_file = gdir / f"{clean_name}.json"

    if graph_file.is_file():
        graph, _ = load_graph(graph_file)
    else:
        graph = SystemGraph(name=clean_name)
        save_graph(graph, graph_file)

    set_active_graph_name(clean_name)
    bin_path = install_graph_binary(clean_name)
    return graph, graph_file, bin_path


def delete_named_graph(name: str) -> bool:
    """Delete a named graph and remove its executable shortcut."""
    clean_name = name.strip()
    gdir = get_graphs_dir()
    graph_file = gdir / f"{clean_name}.json"
    deleted = False
    if graph_file.is_file():
        graph_file.unlink()
        deleted = True

    uninstall_graph_binary(clean_name)

    if get_active_graph_name() == clean_name:
        if ACTIVE_GRAPH_FILE.is_file():
            ACTIVE_GRAPH_FILE.unlink()

    return deleted


def find_graph_file(start_path: Path | str | None = None) -> Path:
    """Locate the active graph storage file.

    Searches current working directory and traverses upwards toward root,
    similar to how git locates .git repositories. Defaults to .graphnode.json
    in the current working directory if not found.

    Args:
        start_path: Optional starting directory path.

    Returns:
        Resolved Path to the graph storage file.
    """
    curr = Path(start_path).resolve() if start_path else Path.cwd().resolve()

    # Search upwards
    for parent in [curr, *curr.parents]:
        candidate = parent / DEFAULT_GRAPH_FILENAME
        if candidate.is_file():
            return candidate

    return curr / DEFAULT_GRAPH_FILENAME


def resolve_graph_target(
    graph_name: str | None = None,
    file_path: Path | str | None = None,
) -> tuple[SystemGraph, Path]:
    """Resolve and load the target graph based on name, file, or active context.

    Resolution order:
    1. Explicit file_path if provided.
    2. Named graph if graph_name provided (from ~/.config/graphnode/graphs/<name>.json).
    3. Project .graphnode.json if present in cwd or ancestor.
    4. Active named graph if set in user profile.
    5. Local .graphnode.json in current directory.
    """
    if file_path:
        return load_graph(file_path)

    if graph_name:
        name_clean = graph_name.strip()
        # Check if direct file
        as_file = Path(name_clean)
        if as_file.is_file():
            return load_graph(as_file)

        # Check named graph in registry
        gdir = get_graphs_dir()
        target_file = gdir / f"{name_clean}.json"
        if not target_file.is_file():
            # Initialize it
            graph = SystemGraph(name=name_clean)
            save_graph(graph, target_file)
            return graph, target_file
        return load_graph(target_file)

    # Check project-level file
    curr = Path.cwd().resolve()
    for parent in [curr, *curr.parents]:
        candidate = parent / DEFAULT_GRAPH_FILENAME
        if candidate.is_file():
            return load_graph(candidate)

    # Check active named graph
    active = get_active_graph_name()
    if active:
        target_named = get_graphs_dir() / f"{active}.json"
        if target_named.is_file():
            return load_graph(target_named)

    # Default to current directory .graphnode.json
    return load_graph(curr / DEFAULT_GRAPH_FILENAME)


def load_graph(file_path: Path | str | None = None) -> tuple[SystemGraph, Path]:
    """Load system graph from disk or initialize an empty graph if not found.

    Args:
        file_path: Optional path to specific graph file.

    Returns:
        A tuple of (SystemGraph instance, resolved Path).
    """
    target = Path(file_path).resolve() if file_path else find_graph_file()

    if not target.is_file():
        return SystemGraph(name=target.parent.name or "system"), target

    try:
        content = target.read_text(encoding="utf-8")
        if not content.strip():
            return SystemGraph(name=target.parent.name or "system"), target
        data = json.loads(content)
        return SystemGraph.from_dict(data), target
    except (json.JSONDecodeError, OSError) as exc:
        raise OSError(f"Failed to read graph file at '{target}': {exc}") from exc


def save_graph(graph: SystemGraph, file_path: Path | str | None = None) -> Path:
    """Save system graph to disk.

    Args:
        graph: SystemGraph to persist.
        file_path: Optional destination path.

    Returns:
        The written Path.
    """
    target = Path(file_path).resolve() if file_path else find_graph_file()
    target.parent.mkdir(parents=True, exist_ok=True)

    data = graph.to_dict()
    target.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target


def init_graph(file_path: Path | str | None = None, name: str = "system") -> tuple[SystemGraph, Path]:
    """Initialize a new graph in the specified directory.

    Args:
        file_path: Optional target file path.
        name: Name for the new graph.

    Returns:
        Tuple of (SystemGraph, written Path).
    """
    target = Path(file_path).resolve() if file_path else Path.cwd() / DEFAULT_GRAPH_FILENAME
    graph = SystemGraph(name=name)
    save_graph(graph, target)
    return graph, target

