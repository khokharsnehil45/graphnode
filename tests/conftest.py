"""Global test fixtures and path isolation for GraphNode."""

from __future__ import annotations

from pathlib import Path
import pytest


@pytest.fixture(autouse=True)
def isolate_graphnode_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate configuration, graphs registry, and binary directory for every test."""
    test_config = tmp_path / "config"
    test_graphs = test_config / "graphs"
    test_active = test_config / "active_graph"
    test_bin = tmp_path / "bin"

    test_graphs.mkdir(parents=True, exist_ok=True)
    test_bin.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr("graphnode.storage.CONFIG_DIR", test_config)
    monkeypatch.setattr("graphnode.storage.GRAPHS_DIR", test_graphs)
    monkeypatch.setattr("graphnode.storage.ACTIVE_GRAPH_FILE", test_active)
    monkeypatch.setattr("graphnode.storage.BIN_DIR", test_bin)
