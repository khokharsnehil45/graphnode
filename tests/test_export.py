"""Unit tests for GraphNode export utilities."""

from __future__ import annotations

from pathlib import Path
from graphnode.graph import SystemGraph
from graphnode.export import (
    export_dot,
    export_graph_to_file,
    export_markdown,
    export_mermaid,
)


def test_export_mermaid() -> None:
    """Test exporting to Mermaid format."""
    graph = SystemGraph("pipeline")
    graph.add_node("producer", node_type="service")
    graph.add_node("kafka", node_type="queue")
    graph.add_node("consumer", node_type="worker")

    graph.connect("producer", "kafka", label="publish")
    graph.connect("kafka", "consumer", label="poll")

    mermaid = export_mermaid(graph)
    assert "graph TD" in mermaid
    assert "producer" in mermaid
    assert "kafka" in mermaid
    assert 'producer -->|"publish"| kafka' in mermaid
    assert 'kafka -->|"poll"| consumer' in mermaid


def test_export_dot() -> None:
    """Test exporting to Graphviz DOT format."""
    graph = SystemGraph("net")
    graph.add_node("router", node_type="gateway")
    graph.add_node("server", node_type="service")
    graph.connect("router", "server")

    dot = export_dot(graph)
    assert 'digraph "net"' in dot
    assert '"router" -> "server";' in dot


def test_export_markdown() -> None:
    """Test exporting markdown documentation report."""
    graph = SystemGraph("store")
    graph.add_node("app", node_type="service", description="Store API")
    graph.add_node("db", node_type="database")
    graph.connect("app", "db", label="read/write")

    md = export_markdown(graph)
    assert "# System Architecture: store" in md
    assert "```mermaid" in md
    assert "| `app` | `service` | Store API |" in md
    assert "| `app` | `read/write` | `db` |" in md


def test_export_graph_to_file(tmp_path: Path) -> None:
    """Test writing exports to disk."""
    graph = SystemGraph("export_test")
    graph.add_node("n1")
    graph.add_node("n2")
    graph.connect("n1", "n2")

    target_mmd = tmp_path / "graph.mmd"
    written = export_graph_to_file(graph, "mermaid", target_mmd)
    assert written.is_file()
    assert "graph TD" in written.read_text()

    target_json = tmp_path / "graph.json"
    written_json = export_graph_to_file(graph, "json", target_json)
    assert written_json.is_file()
    assert '"nodes"' in written_json.read_text()
