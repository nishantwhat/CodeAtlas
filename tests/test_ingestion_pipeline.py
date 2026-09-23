"""Tests for ingestion pipeline behavior and exception contracts."""

from pathlib import Path

import pytest

from program_graph.analysis.exceptions import (
    CompilationDatabaseError,
    IngestionError,
    ProgramGraphError,
    SourceNotFoundError,
    UnsupportedLanguageError,
)
from program_graph.analysis.ingestion import (
    CompilationDatabaseIngestor,
    Language,
    SourceIngestor,
)


def test_exception_hierarchy_contract():
    """Verify that all custom exceptions inherit from ProgramGraphError."""
    assert issubclass(IngestionError, ProgramGraphError)
    assert issubclass(SourceNotFoundError, IngestionError)
    assert issubclass(UnsupportedLanguageError, IngestionError)
    assert issubclass(CompilationDatabaseError, IngestionError)


def test_standalone_unsupported_language(tmp_path: Path):
    """Verify UnsupportedLanguageError is raised for invalid file extensions."""
    txt_file = tmp_path / "doc.txt"
    txt_file.write_text("not source code")

    ingestor = SourceIngestor()
    with pytest.raises(UnsupportedLanguageError):
        ingestor.ingest(txt_file)


def test_compilation_db_fallback_and_strict_modes(tmp_path: Path):
    """Verify compilation database fallback in non-strict mode vs error in strict mode."""
    c_file = tmp_path / "main.c"
    c_file.write_text("int main() { return 0; }")

    db_path = tmp_path / "compile_commands.json"
    db_path.write_text("[]")

    # Non-strict mode should fall back to Standalone ingestor
    ingestor_lax = CompilationDatabaseIngestor(db_path, strict=False)
    target = ingestor_lax.ingest(c_file)
    assert target.source_path == c_file.resolve()
    assert target.language == Language.C

    # Strict mode should raise CompilationDatabaseError
    ingestor_strict = CompilationDatabaseIngestor(db_path, strict=True)
    with pytest.raises(CompilationDatabaseError, match="not found in compilation database"):
        ingestor_strict.ingest(c_file)