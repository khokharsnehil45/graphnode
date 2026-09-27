"""Unit tests for SystemGraph core operations and algorithms."""

from __future__ import annotations

import pytest
from graphnode.graph import (
    Edge,
    Node,
    NodeExistsError,
    NodeNotFoundError,
    SystemGraph,
)


def test_node_creation_and_serialization() -> None:
    """Test Node dataclass and dictionary conversion."""
    node = Node(name="api_gateway", node_type="gateway", description="Entry reverse proxy")
    data = node.to_dict()
    assert data["name"] == "api_gateway"
    assert data["type"] == "gateway"
    assert data["description"] == "Entry reverse proxy"

    restored = Node.from_dict(data)
    assert restored.name == node.name
    assert restored.node_type == node.node_type
    assert restored.description == node.description


def test_add_node_validation() -> None:
    """Test validation when adding nodes."""
    graph = SystemGraph("test")
    with pytest.raises(ValueError, match="cannot be empty"):
        graph.add_node("   ")

    node = graph.add_node("auth_service", node_type="service")
    assert node.name == "auth_service"
    assert graph.has_node("auth_service")

    # Duplicate node without overwrite raises NodeExistsError
    with pytest.raises(NodeExistsError):
        graph.add_node("auth_service")

    # Overwrite updates node
    updated = graph.add_node("auth_service", node_type="security", overwrite=True)
    assert updated.node_type == "security"


def test_remove_node_and_edges() -> None:
    """Test removing a node cleans up all incoming and outgoing connections."""
    graph = SystemGraph("test")
    graph.add_node("client", node_type="client")
    graph.add_node("gateway", node_type="gateway")
    graph.add_node("db", node_type="db")

    graph.connect("client", "gateway")
    graph.connect("gateway", "db")

    assert graph.has_edge("client", "gateway")
    assert graph.has_edge("gateway", "db")

    # Remove intermediate node
    assert graph.remove_node("gateway") is True
    assert not graph.has_node("gateway")
    assert not graph.has_edge("client", "gateway")
    assert not graph.has_edge("gateway", "db")

    # Removing nonexistent returns False
    assert graph.remove_node("nonexistent") is False


def test_connect_and_disconnect() -> None:
    """Test connecting nodes with and without labels."""
    graph = SystemGraph("test")
    graph.add_node("web", node_type="frontend")
    graph.add_node("api", node_type="backend")

    edge = graph.connect("web", "api", label="HTTPS")
    assert edge.source == "web"
    assert edge.target == "api"
    assert edge.label == "HTTPS"
    assert graph.has_edge("web", "api")
    assert graph.out_degree("web") == 1
    assert graph.in_degree("api") == 1

    # Connect to missing node without auto_create raises NodeNotFoundError
    with pytest.raises(NodeNotFoundError):
        graph.connect("web", "missing")

    # Connect with auto_create
    edge2 = graph.connect("web", "auto_node", auto_create=True)
    assert edge2.target == "auto_node"
    assert graph.has_node("auto_node")

    # Disconnect
    assert graph.disconnect("web", "api") is True
    assert not graph.has_edge("web", "api")
    assert graph.disconnect("web", "api") is False


def test_roots_leaves_and_isolated() -> None:
    """Test calculation of roots, leaves, and isolated components."""
    graph = SystemGraph("test")
    graph.add_node("root_a")
    graph.add_node("root_b")
    graph.add_node("middle")
    graph.add_node("leaf")
    graph.add_node("isolated")

    graph.connect("root_a", "middle")
    graph.connect("root_b", "middle")
    graph.connect("middle", "leaf")

    assert sorted(graph.get_roots()) == ["isolated", "root_a", "root_b"]
    assert graph.get_leaves() == ["leaf"]
    assert graph.get_isolated() == ["isolated"]


def test_cycle_detection() -> None:
    """Test detecting directed cycles."""
    graph = SystemGraph("test")
    graph.add_node("a")
    graph.add_node("b")
    graph.add_node("c")

    graph.connect("a", "b")
    graph.connect("b", "c")
    assert not graph.has_cycle()

    # Create cycle c -> a
    graph.connect("c", "a")
    assert graph.has_cycle()
    cycles = graph.find_cycles()
    assert len(cycles) > 0


def test_graph_serialization_roundtrip() -> None:
    """Test full serialization and deserialization of a system graph."""
    graph = SystemGraph("ecommerce")
    graph.add_node("ui", node_type="frontend", description="Web portal")
    graph.add_node("catalog", node_type="service", description="Product service")
    graph.add_node("db", node_type="database")

    graph.connect("ui", "catalog", label="REST")
    graph.connect("catalog", "db", label="SQL")

    data = graph.to_dict()
    assert data["name"] == "ecommerce"
    assert len(data["nodes"]) == 3
    assert len(data["edges"]) == 2

    restored = SystemGraph.from_dict(data)
    assert restored.name == "ecommerce"
    assert restored.has_node("ui")
    assert restored.has_edge("ui", "catalog")
    assert restored.get_edge("ui", "catalog").label == "REST"
