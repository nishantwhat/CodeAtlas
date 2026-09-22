"""Tests for compile_commands.json ingestion."""

import json
from pathlib import Path
import pytest
from program_graph.analysis.ingestion import (
    CompilationDatabaseError,
    CompilationDatabaseIngestor,
    Language,
)


def test_valid_compilation_db(tmp_path: Path):
    src_file = tmp_path / "main.c"
    src_file.write_text("int main() { return 0; }")

    db_path = tmp_path / "compile_commands.json"
    db_content = [
        {
            "directory": str(tmp_path),
            "command": f"gcc -Iinclude -Wall -c {src_file.name} -o main.o",
            "file": str(src_file),
        }
    ]
    db_path.write_text(json.dumps(db_content))

    ingestor = CompilationDatabaseIngestor(db_path)
    source = ingestor.ingest(src_file)

    assert source.path == src_file.resolve()
    assert source.language == Language.C
    assert "-Iinclude" in source.compiler_flags
    assert "-Wall" in source.compiler_flags


def test_source_absent_from_compilation_db(tmp_path: Path):
    src_file = tmp_path / "main.c"
    src_file.write_text("int main() { return 0; }")

    other_file = tmp_path / "other.c"
    other_file.write_text("void foo() {}")

    db_path = tmp_path / "compile_commands.json"
    db_content = [
        {
            "directory": str(tmp_path),
            "arguments": ["gcc", "-c", str(other_file)],
            "file": str(other_file),
        }
    ]
    db_path.write_text(json.dumps(db_content))

    ingestor = CompilationDatabaseIngestor(db_path)
    with pytest.raises(CompilationDatabaseError, match="not found in compilation database"):
        ingestor.ingest(src_file)


def test_missing_compilation_db(tmp_path: Path):
    with pytest.raises(CompilationDatabaseError, match="not found"):
        CompilationDatabaseIngestor(tmp_path / "compile_commands.json")


def test_malformed_compilation_db(tmp_path: Path):
    db_path = tmp_path / "compile_commands.json"
    db_path.write_text("{ invalid json }")

    with pytest.raises(CompilationDatabaseError, match="Malformed JSON"):
        CompilationDatabaseIngestor(db_path)