"""Tests for Control Flow Graph (CFG) extraction."""

from pathlib import Path

from program_graph.analysis.ast import ASTExtractor
from program_graph.analysis.cfg import CFGEdgeType, CFGNodeKind, build_cfgs_for_ast
from program_graph.analysis.ingestion import SourceIngestor


def test_cfg_simple_function(tmp_path: Path):
    """Verify CFG construction for a linear C function."""
    c_file = tmp_path / "simple.c"
    c_file.write_text(
        "int simple() {\n"
        "    int a = 5;\n"
        "    int b = 10;\n"
        "    return a + b;\n"
        "}\n"
    )

    target = SourceIngestor().ingest(c_file)
    ast_rep = ASTExtractor().extract(target)

    cfgs = build_cfgs_for_ast(ast_rep.root)
    assert "simple" in cfgs

    cfg = cfgs["simple"]
    assert cfg.function_name == "simple"
    assert cfg.entry_node_id in cfg.nodes
    assert cfg.exit_node_id in cfg.nodes
    assert len(cfg.nodes) >= 3


def test_cfg_if_branching(tmp_path: Path):
    """Verify CFG construction for conditional if-else statements."""
    c_file = tmp_path / "branch.c"
    c_file.write_text(
        "int max_val(int x, int y) {\n"
        "    if (x > y) {\n"
        "        return x;\n"
        "    } else {\n"
        "        return y;\n"
        "    }\n"
        "}\n"
    )

    target = SourceIngestor().ingest(c_file)
    ast_rep = ASTExtractor().extract(target)

    cfgs = build_cfgs_for_ast(ast_rep.root)
    assert "max_val" in cfgs

    cfg = cfgs["max_val"]
    cond_nodes = [n for n in cfg.nodes.values() if n.kind == CFGNodeKind.CONDITION]
    assert len(cond_nodes) == 1

    true_edges = [e for e in cfg.edges if e.edge_type == CFGEdgeType.TRUE_BRANCH]
    false_edges = [e for e in cfg.edges if e.edge_type == CFGEdgeType.FALSE_BRANCH]
    assert len(true_edges) == 1
    assert len(false_edges) == 1


def test_cfg_while_loop(tmp_path: Path):
    """Verify CFG construction for while loops with back-edges."""
    c_file = tmp_path / "loop.c"
    c_file.write_text(
        "int count_loop(int n) {\n"
        "    int i = 0;\n"
        "    while (i < n) {\n"
        "        i++;\n"
        "    }\n"
        "    return i;\n"
        "}\n"
    )

    target = SourceIngestor().ingest(c_file)
    ast_rep = ASTExtractor().extract(target)

    cfgs = build_cfgs_for_ast(ast_rep.root)
    assert "count_loop" in cfgs

    cfg = cfgs["count_loop"]
    loop_headers = [n for n in cfg.nodes.values() if n.kind == CFGNodeKind.LOOP_HEADER]
    assert len(loop_headers) == 1

    back_edges = [e for e in cfg.edges if e.edge_type == CFGEdgeType.LOOP_BACK]
    assert len(back_edges) == 1
