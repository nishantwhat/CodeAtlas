"""End-to-end Phase 1 integration test validating Ingestion -> AST -> CFG -> DFG -> UPR pipeline."""

import json
from pathlib import Path

from program_graph.analysis.ast import ASTExtractor
from program_graph.analysis.ingestion import CompilationDatabaseIngestor
from program_graph.analysis.upr import UnifiedProgramRepresentation, build_upr


def test_phase1_full_pipeline_integration(tmp_path: Path):
    """Integration test verifying complete Phase 1 pipeline on a multi-function C++ benchmark fixture."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    cpp_file = src_dir / "pipeline.cpp"
    cpp_file.write_text(
        "#include <iostream>\n"
        "int process(int item) {\n"
        "    if (item > 0) {\n"
        "        return item * 2;\n"
        "    }\n"
        "    return 0;\n"
        "}\n"
        "int main() {\n"
        "    int val = 10;\n"
        "    int result = process(val);\n"
        "    return result;\n"
        "}\n"
    )

    db_path = tmp_path / "compile_commands.json"
    db_content = [
        {
            "directory": str(tmp_path),
            "command": f"g++ -std=c++17 -c {cpp_file}",
            "file": str(cpp_file),
        }
    ]
    db_path.write_text(json.dumps(db_content))

    # 1. Ingestion
    ingestor = CompilationDatabaseIngestor(db_path)
    target = ingestor.ingest(cpp_file)
    assert target.source_path == cpp_file.resolve()

    # 2. AST Extraction
    ast_rep = ASTExtractor().extract(target)
    assert ast_rep.root.kind == "TRANSLATION_UNIT"

    # 3. UPR Assembly (includes CFG, DFG, Call Sites)
    upr = build_upr(target, ast_rep)

    assert "process" in upr.cfgs
    assert "main" in upr.cfgs
    assert len(upr.dfg.def_sites) > 0
    assert len(upr.dfg.use_sites) > 0
    assert len(upr.call_sites) >= 1

    # 4. JSON Serialization & Deserialization Phase Gate Validation
    json_output = upr.to_json()
    upr_reloaded = UnifiedProgramRepresentation.from_json(json_output)

    assert upr_reloaded.target.source_path == target.source_path
    assert len(upr_reloaded.cfgs) == len(upr.cfgs)
    assert len(upr_reloaded.call_sites) == len(upr.call_sites)
