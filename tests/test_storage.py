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
