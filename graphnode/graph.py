"""Core graph data structures and graph algorithms for GraphNode."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


class GraphError(Exception):
    """Base exception for graph operations."""


class NodeNotFoundError(GraphError):
    """Raised when a referenced node does not exist in the graph."""


class NodeExistsError(GraphError):
    """Raised when attempting to create a node that already exists."""


class EdgeNotFoundError(GraphError):
    """Raised when a referenced edge does not exist."""


@dataclass
class Node:
    """A node representing a component or service in the system graph."""

    name: str
    node_type: str = "service"
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize node to a dictionary."""
        return {
            "name": self.name,
            "type": self.node_type,
            "description": self.description,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Node:
        """Create a Node instance from a dictionary."""
        return cls(
            name=data["name"],
            node_type=data.get("type", "service"),
            description=data.get("description", ""),
            metadata=data.get("metadata", {}),
            created_at=data.get(
                "created_at", datetime.now(timezone.utc).isoformat()
            ),
        )


@dataclass
class Edge:
    """A directed connection between two nodes."""

    source: str
    target: str
    label: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize edge to a dictionary."""
        return {
            "source": self.source,
            "target": self.target,
            "label": self.label,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Edge:
        """Create an Edge instance from a dictionary."""
        return cls(
            source=data["source"],
            target=data["target"],
            label=data.get("label", ""),
            metadata=data.get("metadata", {}),
        )


class SystemGraph:
    """Directed graph representing system architecture, dependencies, and flow."""

    def __init__(self, name: str = "default") -> None:
        self.name = name
        self.nodes: dict[str, Node] = {}
        # adjacency list: source -> dict of target -> Edge
        self.adj: dict[str, dict[str, Edge]] = {}
        # reverse adjacency list: target -> set of sources
        self.rev_adj: dict[str, set[str]] = {}

    def add_node(
        self,
        name: str,
        node_type: str = "service",
        description: str = "",
        metadata: dict[str, Any] | None = None,
        overwrite: bool = False,
    ) -> Node:
        """Add a new node to the system graph.

        Args:
            name: Name or identifier of the node.
            node_type: Type classification (e.g. service, db, queue, gateway).
            description: Optional descriptive text.
            metadata: Optional dictionary of extra attributes.
            overwrite: If True, updates existing node instead of raising an error.

        Returns:
            The created or updated Node object.

        Raises:
            ValueError: If the node name is empty.
            NodeExistsError: If node already exists and overwrite is False.
        """
        clean_name = str(name).strip()
        if not clean_name:
            raise ValueError("Node name cannot be empty.")

        if clean_name in self.nodes and not overwrite:
            raise NodeExistsError(f"Node '{clean_name}' already exists in the graph.")

        node = Node(
            name=clean_name,
            node_type=str(node_type).strip() or "service",
            description=str(description).strip(),
            metadata=metadata or {},
        )
        self.nodes[clean_name] = node
        if clean_name not in self.adj:
            self.adj[clean_name] = {}
        if clean_name not in self.rev_adj:
            self.rev_adj[clean_name] = set()

        return node

    def remove_node(self, name: str) -> bool:
        """Remove a node and all connecting edges from the graph.

        Args:
            name: Node name to remove.

        Returns:
            True if removed, False if node didn't exist.
        """
        clean_name = str(name).strip()
        if clean_name not in self.nodes:
            return False

        # Remove outgoing edges
        outgoing = list(self.adj.get(clean_name, {}).keys())
        for target in outgoing:
            self.disconnect(clean_name, target)

        # Remove incoming edges
        incoming = list(self.rev_adj.get(clean_name, set()))
        for source in incoming:
            self.disconnect(source, clean_name)

        self.nodes.pop(clean_name, None)
        self.adj.pop(clean_name, None)
        self.rev_adj.pop(clean_name, None)
        return True

    def has_node(self, name: str) -> bool:
        """Check if a node exists."""
        return str(name).strip() in self.nodes

    def get_node(self, name: str) -> Node | None:
        """Retrieve a node by name."""
        return self.nodes.get(str(name).strip())

    def connect(
        self,
        source: str,
        target: str,
        label: str = "",
        auto_create: bool = False,
    ) -> Edge:
        """Connect source node to target node with a directed edge.

        Args:
            source: Name of source node.
            target: Name of target node.
            label: Optional edge relationship label (e.g. 'HTTP', 'gRPC', 'reads').
            auto_create: If True, creates missing nodes automatically.

        Returns:
            The created Edge object.

        Raises:
            NodeNotFoundError: If source or target node is missing and auto_create is False.
        """
        src = str(source).strip()
        dst = str(target).strip()

        if src not in self.nodes:
            if auto_create:
                self.add_node(src)
            else:
                raise NodeNotFoundError(f"Source node '{src}' does not exist.")

        if dst not in self.nodes:
            if auto_create:
                self.add_node(dst)
            else:
                raise NodeNotFoundError(f"Target node '{dst}' does not exist.")

        edge = Edge(source=src, target=dst, label=str(label).strip())
        self.adj[src][dst] = edge
        self.rev_adj[dst].add(src)
        return edge

    def disconnect(self, source: str, target: str) -> bool:
        """Remove directed connection between source and target nodes."""
        src = str(source).strip()
        dst = str(target).strip()

        if src in self.adj and dst in self.adj[src]:
            del self.adj[src][dst]
            if dst in self.rev_adj:
                self.rev_adj[dst].discard(src)
            return True
        return False

    def has_edge(self, source: str, target: str) -> bool:
        """Check if an edge exists between source and target."""
        src = str(source).strip()
        dst = str(target).strip()
        return src in self.adj and dst in self.adj[src]

    def get_edge(self, source: str, target: str) -> Edge | None:
        """Get Edge between source and target, if it exists."""
        src = str(source).strip()
        dst = str(target).strip()
        return self.adj.get(src, {}).get(dst)

    def out_degree(self, name: str) -> int:
        """Count outgoing connections from a node."""
        clean = str(name).strip()
        return len(self.adj.get(clean, {}))

    def in_degree(self, name: str) -> int:
        """Count incoming connections to a node."""
        clean = str(name).strip()
        return len(self.rev_adj.get(clean, set()))

    def get_roots(self) -> list[str]:
        """Get nodes with in-degree 0 (entry points / roots), sorted alphabetically."""
        roots = [n for n in self.nodes if self.in_degree(n) == 0]
        # If all nodes have incoming edges (e.g. cycle), pick nodes with highest out-degree
        if not roots and self.nodes:
            sorted_by_out = sorted(
                self.nodes.keys(),
                key=lambda n: (self.out_degree(n), -self.in_degree(n)),
                reverse=True,
            )
            return [sorted_by_out[0]]
        return sorted(roots)

    def get_leaves(self) -> list[str]:
        """Get nodes with out-degree 0 (sinks / databases / terminal workers)."""
        return sorted([n for n in self.nodes if self.out_degree(n) == 0 and self.in_degree(n) > 0])

    def get_isolated(self) -> list[str]:
        """Get nodes with no incoming or outgoing connections."""
        return sorted([n for n in self.nodes if self.in_degree(n) == 0 and self.out_degree(n) == 0])

    def get_all_edges(self) -> list[Edge]:
        """Return list of all edges sorted by source and target."""
        edges: list[Edge] = []
        for src in sorted(self.adj.keys()):
            for dst in sorted(self.adj[src].keys()):
                edges.append(self.adj[src][dst])
        return edges

    def find_cycles(self) -> list[list[str]]:
        """Detect simple directed cycles in the graph using DFS."""
        visited: dict[str, int] = {}  # 0: unvisited, 1: visiting, 2: visited
        cycles: list[list[str]] = []
        path: list[str] = []

        def dfs(node: str) -> None:
            visited[node] = 1
            path.append(node)

            for neighbor in sorted(self.adj.get(node, {}).keys()):
                state = visited.get(neighbor, 0)
                if state == 1:
                    cycle_start = path.index(neighbor)
                    cycles.append(path[cycle_start:] + [neighbor])
                elif state == 0:
                    dfs(neighbor)

            path.pop()
            visited[node] = 2

        for node in sorted(self.nodes.keys()):
            if visited.get(node, 0) == 0:
                dfs(node)

        return cycles

    def has_cycle(self) -> bool:
        """Check if the graph contains any cycle."""
        return len(self.find_cycles()) > 0

    def clear(self) -> None:
        """Clear all nodes and edges from the graph."""
        self.nodes.clear()
        self.adj.clear()
        self.rev_adj.clear()

    def to_dict(self) -> dict[str, Any]:
        """Serialize entire graph to JSON-compatible dictionary."""
        return {
            "name": self.name,
            "nodes": [node.to_dict() for node in self.nodes.values()],
            "edges": [edge.to_dict() for edge in self.get_all_edges()],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SystemGraph:
        """Construct SystemGraph from serialized dictionary."""
        graph = cls(name=data.get("name", "default"))
        for node_data in data.get("nodes", []):
            node = Node.from_dict(node_data)
            graph.nodes[node.name] = node
            graph.adj[node.name] = {}
            graph.rev_adj[node.name] = set()

        for edge_data in data.get("edges", []):
            edge = Edge.from_dict(edge_data)
            if edge.source in graph.nodes and edge.target in graph.nodes:
                graph.adj[edge.source][edge.target] = edge
                graph.rev_adj[edge.target].add(edge.source)

        return graph
