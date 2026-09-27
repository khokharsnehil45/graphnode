"""Storage and project-level persistence for GraphNode."""

from __future__ import annotations

import json
from pathlib import Path

from graphnode.graph import SystemGraph

DEFAULT_GRAPH_FILENAME = ".graphnode.json"


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
