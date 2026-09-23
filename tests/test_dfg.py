"""Tests for Data Flow Graph (DFG) and def-use analysis."""

from pathlib import Path

from program_graph.analysis.ast import ASTExtractor
from program_graph.analysis.dfg import DFGBuilder
from program_graph.analysis.ingestion import SourceIngestor


def test_dfg_variable_def_use(tmp_path: Path):
    """Verify DFG extraction for variable declarations and references."""
    c_file = tmp_path / "dfg_sample.c"
    c_file.write_text(
        "int compute() {\n"
        "    int x = 42;\n"
        "    int y = x + 10;\n"
        "    return y;\n"
        "}\n"
    )

    target = SourceIngestor().ingest(c_file)
    ast_rep = ASTExtractor().extract(target)

    dfg = DFGBuilder().build(ast_rep.root)

    assert len(dfg.def_sites) >= 2
    assert len(dfg.use_sites) >= 2
    assert len(dfg.edges) >= 2

    symbols_defined = {s.symbol.name for s in dfg.def_sites.values()}
    assert "x" in symbols_defined
    assert "y" in symbols_defined

    symbols_used = {s.symbol.name for s in dfg.use_sites.values()}
    assert "x" in symbols_used
    assert "y" in symbols_used
