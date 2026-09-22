"""Tests for standalone source file ingestion."""

from pathlib import Path
import pytest
from program_graph.analysis.ingestion import IngestionError, Language, StandaloneIngestor


def test_ingest_valid_c_file(tmp_path: Path):
    c_file = tmp_path / "hello.c"
    c_file.write_text('#include <stdio.h>\nint main() { printf("Hello"); return 0; }')

    ingestor = StandaloneIngestor()
    source = ingestor.ingest(c_file, default_flags=["-Wall"])

    assert source.path == c_file.resolve()
    assert source.language == Language.C
    assert source.compiler_flags == ["-Wall"]


def test_ingest_valid_cpp_file(tmp_path: Path):
    cpp_file = tmp_path / "hello.cpp"
    cpp_file.write_text('#include <iostream>\nint main() { std::cout << "Hello"; return 0; }')

    ingestor = StandaloneIngestor()
    source = ingestor.ingest(cpp_file)

    assert source.path == cpp_file.resolve()
    assert source.language == Language.CPP


def test_ingest_missing_file(tmp_path: Path):
    ingestor = StandaloneIngestor()
    with pytest.raises(IngestionError, match="does not exist"):
        ingestor.ingest(tmp_path / "nonexistent.c")


def test_ingest_unsupported_extension(tmp_path: Path):
    txt_file = tmp_path / "notes.txt"
    txt_file.write_text("just text")

    ingestor = StandaloneIngestor()
    with pytest.raises(IngestionError, match="Unsupported file extension"):
        ingestor.ingest(txt_file)


def test_ingest_directory_fails(tmp_path: Path):
    ingestor = StandaloneIngestor()
    with pytest.raises(IngestionError, match="not a regular file"):
        ingestor.ingest(tmp_path)