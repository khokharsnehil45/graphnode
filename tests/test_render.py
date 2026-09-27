"""Unit tests for terminal rendering of GraphNode."""

from __future__ import annotations

from graphnode.graph import SystemGraph
from graphnode.render import render_card, render_flow, render_tree


def test_render_tree_empty() -> None:
    """Test tree rendering on empty graph."""
    graph = SystemGraph("empty")
    res = render_tree(graph)
    assert "Graph is empty" in res


def test_render_tree_hierarchy() -> None:
    """Test hierarchical tree rendering."""
    graph = SystemGraph("payments")
    graph.add_node("client", node_type="client")
    graph.add_node("api", node_type="gateway")
    graph.add_node("stripe", node_type="service")
    graph.add_node("db", node_type="database")
    graph.add_node("isolated_doc", node_type="custom")

    graph.connect("client", "api", label="HTTPS")
    graph.connect("api", "stripe", label="REST")
    graph.connect("api", "db", label="SQL")

    tree = render_tree(graph)
    assert "System Graph: payments" in tree
    assert "client" in tree
    assert "api" in tree
    assert "stripe" in tree
    assert "db" in tree
    assert "Standalone / Isolated Nodes" in tree
    assert "isolated_doc" in tree


def test_render_tree_handles_cycle() -> None:
    """Test tree rendering does not infinitely recurse on cycles."""
    graph = SystemGraph("cyclic")
    graph.add_node("n1")
    graph.add_node("n2")
    graph.connect("n1", "n2")
    graph.connect("n2", "n1")

    tree = render_tree(graph)
    assert "cycle" in tree


def test_render_card() -> None:
    """Test architecture card rendering."""
    graph = SystemGraph("microservices")
    graph.add_node("frontend", node_type="client")
    graph.add_node("backend", node_type="service")
    graph.connect("frontend", "backend")

    card = render_card(graph)
    assert "SYSTEM ARCHITECTURE GRAPH" in card
    assert "Graph Name    : microservices" in card
    assert "[frontend]" in card
    assert "[backend]" in card


def test_render_flow() -> None:
    """Test render_flow edge list."""
    graph = SystemGraph("flow_test")
    assert "Graph is empty" in render_flow(graph)

    graph.add_node("a")
    graph.add_node("b")
    assert "No connections exist yet" in render_flow(graph)

    graph.connect("a", "b", label="TCP")
    flow = render_flow(graph)
    assert "a ──(TCP)──▶ b" in flow
