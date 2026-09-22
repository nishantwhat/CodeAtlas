"""Tests for AST search and traversal utilities."""

from pathlib import Path
from program_graph.analysis.ast import (
    ASTExtractor,
    find_nodes_by_kind,
    walk_ast,
)
from program_graph.analysis.ingestion import SourceIngestor


def test_walk_ast_and_search(tmp_path: Path):
    """Verify walk_ast generator and find_nodes_by_kind helper."""
    c_file = tmp_path / "vars.c"
    c_file.write_text(
        "void test() {\n"
        "    int x = 10;\n"
        "    int y = 20;\n"
        "}\n"
    )

    target = SourceIngestor().ingest(c_file)
    ast_rep = ASTExtractor().extract(target)

    all_nodes = list(walk_ast(ast_rep.root))
    assert len(all_nodes) > 1

    var_decls = find_nodes_by_kind(ast_rep.root, "VAR_DECL")
    assert len(var_decls) == 2
    spellings = [v.spelling for v in var_decls]
    assert "x" in spellings
    assert "y" in spellings