"""End-to-end AST extraction pipeline tests."""

import json
from pathlib import Path

from program_graph.analysis.ast import ASTExtractor, find_nodes_by_kind
from program_graph.analysis.ingestion import CompilationDatabaseIngestor


def test_end_to_end_ingestion_and_ast_extraction(tmp_path: Path):
    """Verify full ingestion and AST extraction pipeline with compilation database."""
    cpp_file = tmp_path / "src" / "engine.cpp"
    cpp_file.parent.mkdir(parents=True)
    cpp_file.write_text(
        "namespace Engine {\n"
        "    int compute(int val) { return val * 2; }\n"
        "}\n"
    )

    db_path = tmp_path / "compile_commands.json"
    db_data = [
        {
            "directory": str(tmp_path),
            "command": f"g++ -std=c++17 -c {cpp_file}",
            "file": str(cpp_file),
        }
    ]
    db_path.write_text(json.dumps(db_data))

    ingestor = CompilationDatabaseIngestor(db_path)
    target = ingestor.ingest(cpp_file)

    extractor = ASTExtractor()
    ast_rep = extractor.extract(target)

    assert ast_rep.target.source_path == cpp_file.resolve()
    namespaces = find_nodes_by_kind(ast_rep.root, "NAMESPACE")
    assert len(namespaces) == 1
    assert namespaces[0].spelling == "Engine"