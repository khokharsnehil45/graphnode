"""Integration and CLI tests for GraphNode."""

from __future__ import annotations

from pathlib import Path
import pytest

from graphnode.cli import run


def test_cli_init_command(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test graphnode -init initializes a new graph."""
    graph_file = tmp_path / ".graphnode.json"
    code = run(["-init", "cloud_app", "-f", str(graph_file)])
    assert code == 0

    assert graph_file.is_file()
    captured = capsys.readouterr()
    assert "Initialized new system graph 'cloud_app'" in captured.out


def test_cli_add_and_connect_flow(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test full workflow: add nodes, connect them, and show tree."""
    graph_file = tmp_path / "app.json"

    # Add frontend
    assert run(["-add", "frontend", "-type", "client", "-f", str(graph_file)]) == 0
    # Add backend
    assert run(["-add", "backend", "-type", "service", "-f", str(graph_file)]) == 0
    # Add postgres
    assert run(["-add", "postgres", "-type", "db", "-f", str(graph_file)]) == 0

    # Connect
    assert run(["-connect", "frontend", "backend", "-label", "REST", "-f", str(graph_file)]) == 0
    assert run(["-connect", "backend", "postgres", "-label", "SQL", "-f", str(graph_file)]) == 0

    # Show tree
    capsys.readouterr()  # Clear stdout
    code_show = run(["-show", "-f", str(graph_file)])
    assert code_show == 0

    captured = capsys.readouterr()
    assert "frontend" in captured.out
    assert "backend" in captured.out
    assert "postgres" in captured.out
    assert "REST" in captured.out


def test_cli_subcommand_syntax(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test subcommands without leading hyphens (e.g. 'add', 'connect', 'show')."""
    graph_file = tmp_path / "subcommands.json"

    assert run(["add", "nodeA", "-f", str(graph_file)]) == 0
    assert run(["add", "nodeB", "-f", str(graph_file)]) == 0
    assert run(["connect", "nodeA", "nodeB", "-f", str(graph_file)]) == 0

    capsys.readouterr()
    assert run(["show", "-f", str(graph_file)]) == 0
    captured = capsys.readouterr()
    assert "nodeA" in captured.out
    assert "nodeB" in captured.out


def test_cli_show_modes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test -show with card and flow formats."""
    graph_file = tmp_path / "modes.json"
    run(["-add", "s1", "s2", "-f", str(graph_file)])
    run(["-connect", "s1", "s2", "-label", "gRPC", "-f", str(graph_file)])

    # Card mode
    capsys.readouterr()
    assert run(["-show", "card", "-f", str(graph_file)]) == 0
    captured_card = capsys.readouterr()
    assert "SYSTEM ARCHITECTURE GRAPH" in captured_card.out
    assert "[s1]" in captured_card.out

    # Flow mode
    assert run(["-show", "flow", "-f", str(graph_file)]) == 0
    captured_flow = capsys.readouterr()
    assert "s1 ──(gRPC)──▶ s2" in captured_flow.out


def test_cli_status_and_list(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test -status and -list commands."""
    graph_file = tmp_path / "stats.json"
    run(["-add", "entry", "exit", "-f", str(graph_file)])
    run(["-connect", "entry", "exit", "-f", str(graph_file)])

    capsys.readouterr()
    assert run(["-status", "-f", str(graph_file)]) == 0
    out_status = capsys.readouterr().out
    assert "Nodes        : 2" in out_status
    assert "Connections  : 1" in out_status

    assert run(["-list", "-f", str(graph_file)]) == 0
    out_list = capsys.readouterr().out
    assert "SYSTEM ARCHITECTURE GRAPH" in out_list


def test_cli_disconnect_and_remove(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test -disconnect and -remove commands."""
    graph_file = tmp_path / "edit.json"
    run(["-add", "n1", "n2", "-f", str(graph_file)])
    run(["-connect", "n1", "n2", "-f", str(graph_file)])

    # Disconnect
    assert run(["-disconnect", "n1", "n2", "-f", str(graph_file)]) == 0
    # Remove
    assert run(["-remove", "n2", "-f", str(graph_file)]) == 0
    # Removing again should fail
    assert run(["-remove", "n2", "-f", str(graph_file)]) == 1


def test_cli_export(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test -export to stdout and to file."""
    graph_file = tmp_path / "export_cli.json"
    run(["-add", "client", "server", "-f", str(graph_file)])
    run(["-connect", "client", "server", "-f", str(graph_file)])

    # Export stdout
    capsys.readouterr()
    assert run(["-export", "mermaid", "-f", str(graph_file)]) == 0
    captured = capsys.readouterr()
    assert "graph TD" in captured.out

    # Export to file
    out_mmd = tmp_path / "arch.mmd"
    assert run(["-export", "mermaid", "-o", str(out_mmd), "-f", str(graph_file)]) == 0
    assert out_mmd.is_file()


def test_cli_clear(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test -clear empties the graph."""
    graph_file = tmp_path / "clear.json"
    run(["-add", "x", "y", "-f", str(graph_file)])
    assert run(["-clear", "-f", str(graph_file)]) == 0

    capsys.readouterr()
    assert run(["-status", "-f", str(graph_file)]) == 0
    captured = capsys.readouterr().out
    assert "Nodes        : 0" in captured


def test_cli_error_cases(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test error handling in CLI."""
    graph_file = tmp_path / "errors.json"

    # Connect without both arguments
    code1 = run(["-connect", "single_node", "-f", str(graph_file)])
    assert code1 == 1

    # Connect nonexistent nodes
    code2 = run(["-connect", "missing1", "missing2", "-f", str(graph_file)])
    assert code2 == 1
    assert "Source node 'missing1' does not exist" in capsys.readouterr().err


def test_cli_named_graph_commands(capsys: pytest.CaptureFixture[str]) -> None:
    """Test -create, -use, -graphs, -delete-graph and targeting via CLI."""
    # 1. Create graph1
    assert run(["-create", "graph1"]) == 0
    captured = capsys.readouterr()
    assert "Created new graph 'graph1'" in captured.out
    assert "graph1" in captured.out

    # 2. Add nodes to graph1 via -g
    assert run(["-g", "graph1", "-add", "node1", "node2"]) == 0
    assert run(["-g", "graph1", "-connect", "node1", "node2"]) == 0

    # 3. Show graph1 via -g
    capsys.readouterr()
    assert run(["-g", "graph1", "-show"]) == 0
    out_show = capsys.readouterr().out
    assert "node1" in out_show
    assert "node2" in out_show

    # 4. List graphs
    assert run(["-graphs"]) == 0
    out_graphs = capsys.readouterr().out
    assert "GRAPHNODE REGISTRY" in out_graphs
    assert "graph1" in out_graphs

    # 5. Create graph2 and switch
    assert run(["create", "graph2"]) == 0
    assert run(["use", "graph1"]) == 0
    captured_use = capsys.readouterr().out
    assert "Active graph set to 'graph1'" in captured_use

    # 6. Delete graph
    assert run(["-delete-graph", "graph2"]) == 0
    captured_del = capsys.readouterr().out
    assert "Deleted graph 'graph2'" in captured_del

    # Deleting nonexistent
    assert run(["-delete-graph", "nonexistent"]) == 1


def test_cli_positional_graph_routing(capsys: pytest.CaptureFixture[str]) -> None:
    """Test routing when graph name is first argument (e.g. 'graphnode graph1 -add node1')."""
    run(["-create", "clusterA"])
    capsys.readouterr()

    # Route via first positional argument
    assert run(["clusterA", "-add", "master", "worker1"]) == 0
    assert run(["clusterA", "-connect", "master", "worker1"]) == 0

    capsys.readouterr()
    assert run(["clusterA", "-show"]) == 0
    captured = capsys.readouterr().out
    assert "master" in captured
    assert "worker1" in captured

