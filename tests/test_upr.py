"""Tests for Unified Program Representation (UPR) and serialization."""

from pathlib import Path

from program_graph.analysis.ast import ASTExtractor
from program_graph.analysis.ingestion import SourceIngestor
from program_graph.analysis.upr import UnifiedProgramRepresentation, build_upr


def test_upr_construction_and_call_sites(tmp_path: Path):
    """Verify UPR assembly including call site relationships."""
    cpp_file = tmp_path / "upr_sample.cpp"
    cpp_file.write_text(
        "int helper(int val) { return val * 2; }\n"
        "int caller() {\n"
        "    int res = helper(5);\n"
        "    return res;\n"
        "}\n"
    )

    target = SourceIngestor().ingest(cpp_file)
    ast_rep = ASTExtractor().extract(target)

    upr = build_upr(target, ast_rep)

    assert upr.target.source_path == cpp_file.resolve()
    assert "caller" in upr.cfgs
    assert "helper" in upr.cfgs

    assert len(upr.call_sites) >= 1
    call = upr.call_sites[0]
    assert call.caller_function == "caller"
    assert "helper" in call.callee_function


def test_upr_json_serialization_round_trip(tmp_path: Path):
    """Verify UPR serialization to JSON string and clean deserialization back."""
    c_file = tmp_path / "serial.c"
    c_file.write_text("int main() { int x = 0; return x; }")

    target = SourceIngestor().ingest(c_file)
    ast_rep = ASTExtractor().extract(target)

    upr_orig = build_upr(target, ast_rep)
    json_str = upr_orig.to_json()

    assert isinstance(json_str, str)
    assert len(json_str) > 0

    upr_restored = UnifiedProgramRepresentation.from_json(json_str)
    assert upr_restored.target.source_path == upr_orig.target.source_path
    assert upr_restored.ast.root.kind == upr_orig.ast.root.kind
    assert len(upr_restored.cfgs) == len(upr_orig.cfgs)
