"""Tests for AST representation models."""

from pathlib import Path
from program_graph.analysis.ast import (
    ASTNode,
    ASTRepresentation,
    SourceLocationInfo,
    SourceRangeInfo,
)
from program_graph.analysis.ingestion import (
    CompilationContext,
    Language,
    TranslationUnitTarget,
)


def test_ast_node_serialization():
    """Verify serialization of ASTNode into dict structures."""
    loc = SourceLocationInfo(line=1, column=5)
    rng = SourceRangeInfo(
        start=SourceLocationInfo(line=1, column=1),
        end=SourceLocationInfo(line=1, column=10),
    )
    child = ASTNode(
        node_id=2,
        kind="ParmDecl",
        spelling="x",
        type_spelling="int",
        location=loc,
        range=rng,
    )
    parent = ASTNode(
        node_id=1,
        kind="FunctionDecl",
        spelling="foo",
        type_spelling="int (int)",
        location=loc,
        range=rng,
        children=[child],
    )

    data = parent.to_dict()

    assert data["node_id"] == 1
    assert data["kind"] == "FunctionDecl"
    assert len(data["children"]) == 1
    assert data["children"][0]["spelling"] == "x"


def test_ast_representation_container(tmp_path: Path):
    """Verify ASTRepresentation binding with TranslationUnitTarget."""
    dummy_file = tmp_path / "main.c"
    dummy_file.touch()

    target = TranslationUnitTarget(
        source_path=dummy_file,
        language=Language.C,
        compilation_context=CompilationContext(),
    )
    root_node = ASTNode(id=0, kind="TranslationUnit", spelling=str(dummy_file), type_spelling="")

    ast_rep = ASTRepresentation(target=target, root=root_node, diagnostics=[])
    assert ast_rep.target.source_path == dummy_file.resolve()
    assert ast_rep.root.kind == "TranslationUnit"