"""Unit tests for GraphNode persistence and storage."""

from __future__ import annotations

from pathlib import Path
import pytest

from graphnode.graph import SystemGraph
from graphnode.storage import (
    DEFAULT_GRAPH_FILENAME,
    find_graph_file,
    init_graph,
    load_graph,
    save_graph,
)


def test_find_graph_file_in_directory(tmp_path: Path) -> None:
    """Test locating graph file in current directory."""
    expected = tmp_path / DEFAULT_GRAPH_FILENAME
    expected.touch()

    found = find_graph_file(tmp_path)
    assert found == expected


def test_find_graph_file_traversal(tmp_path: Path) -> None:
    """Test traversing upwards to locate parent graph file."""
    parent_file = tmp_path / DEFAULT_GRAPH_FILENAME
    parent_file.touch()

    nested = tmp_path / "sub" / "deep"
    nested.mkdir(parents=True)

    found = find_graph_file(nested)
    assert found == parent_file


def test_save_and_load_graph(tmp_path: Path) -> None:
    """Test saving and loading graph from disk."""
    file_path = tmp_path / "custom_graph.json"
    graph = SystemGraph("cloud_infra")
    graph.add_node("k8s_cluster", node_type="infrastructure")
    graph.add_node("ingress", node_type="gateway")
    graph.connect("ingress", "k8s_cluster", label="traffic")

    saved = save_graph(graph, file_path)
    assert saved == file_path
    assert file_path.is_file()

    loaded, path = load_graph(file_path)
    assert path == file_path
    assert loaded.name == "cloud_infra"
    assert loaded.has_node("k8s_cluster")
    assert loaded.has_edge("ingress", "k8s_cluster")


def test_init_graph(tmp_path: Path) -> None:
    """Test initializing a new graph."""
    target = tmp_path / DEFAULT_GRAPH_FILENAME
    graph, path = init_graph(target, name="analytics")
    assert path == target
    assert target.is_file()
    assert graph.name == "analytics"


def test_corrupt_graph_file_error(tmp_path: Path) -> None:
    """Test error handling when graph JSON is corrupted."""
    bad_file = tmp_path / "corrupt.json"
    bad_file.write_text("invalid json content")

    with pytest.raises(OSError, match="Failed to read graph file"):
        load_graph(bad_file)


def test_named_graph_lifecycle() -> None:
    """Test creating, listing, resolving, and deleting named graphs."""
    from graphnode.storage import (
        create_named_graph,
        delete_named_graph,
        get_active_graph_name,
        list_named_graphs,
        resolve_graph_target,
        set_active_graph_name,
    )

    # Creation
    graph, gfile, bin_path = create_named_graph("graph1")
    assert graph.name == "graph1"
    assert gfile.is_file()
    assert bin_path.is_file()
    assert bin_path.stat().st_mode & 0o111  # Executable

    # Active tracking
    assert get_active_graph_name() == "graph1"

    # Listing
    named = list_named_graphs()
    assert "graph1" in named

    # Resolution
    resolved_g, resolved_p = resolve_graph_target(graph_name="graph1")
    assert resolved_g.name == "graph1"
    assert resolved_p == gfile

    # Switch active
    create_named_graph("graph2")
    assert get_active_graph_name() == "graph2"
    set_active_graph_name("graph1")
    assert get_active_graph_name() == "graph1"

    # Reserved name check
    with pytest.raises(ValueError, match="reserved"):
        create_named_graph("node")

    # Deletion
    assert delete_named_graph("graph1") is True
    assert not gfile.is_file()
    assert not bin_path.is_file()
    assert "graph1" not in list_named_graphs()

