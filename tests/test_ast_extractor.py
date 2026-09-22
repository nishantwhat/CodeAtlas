"""Tests for AST extraction from C and C++ sources."""

from pathlib import Path
from program_graph.analysis.ast import ASTExtractor
from program_graph.analysis.ingestion import SourceIngestor


def test_extract_c_ast(tmp_path: Path):
    """Verify AST extraction on a C file containing a function and variable."""
    c_file = tmp_path / "sample.c"
    c_file.write_text(
        "int add(int a, int b) {\n"
        "    int res = a + b;\n"
        "    return res;\n"
        "}\n"
    )

    ingestor = SourceIngestor()
    target = ingestor.ingest(c_file)

    extractor = ASTExtractor()
    ast_rep = extractor.extract(target)

    assert ast_rep.root is not None
    assert ast_rep.root.kind == "TRANSLATION_UNIT"

    func_nodes = [c for c in ast_rep.root.children if c.kind == "FUNCTION_DECL"]
    assert len(func_nodes) == 1
    assert "add" in func_nodes[0].spelling


def test_extract_cpp_ast(tmp_path: Path):
    """Verify AST extraction on a C++ file containing a class and method."""
    cpp_file = tmp_path / "sample.cpp"
    cpp_file.write_text(
        "class Calculator {\n"
        "public:\n"
        "    int multiply(int x, int y) { return x * y; }\n"
        "};\n"
    )

    ingestor = SourceIngestor()
    target = ingestor.ingest(cpp_file)

    extractor = ASTExtractor()
    ast_rep = extractor.extract(target)

    class_nodes = [
        c for c in ast_rep.root.children
        if c.kind in ("CLASS_DECL", "STRUCT_DECL", "CXX_RECORD", "CXX_RECORD_DECL", "RECORD_DECL")
    ]
    assert len(class_nodes) == 1
    assert class_nodes[0].spelling == "Calculator"