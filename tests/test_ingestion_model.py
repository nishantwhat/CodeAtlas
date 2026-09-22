"""Unit tests for source ingestion models."""

from pathlib import Path
import pytest
from program_graph.analysis.ingestion import Language, SourceFile


def test_source_file_model_initialization(tmp_path: Path):
    test_file = tmp_path / "main.c"
    test_file.touch()

    source = SourceFile(
        path=test_file,
        language=Language.C,
        compiler_flags=["-Iinclude", "-Wall"],
    )

    assert source.path == test_file.resolve()
    assert source.language == Language.C
    assert source.compiler_flags == ["-Iinclude", "-Wall"]
    assert source.exists is True


def test_source_file_non_existent(tmp_path: Path):
    missing_file = tmp_path / "missing.cpp"
    source = SourceFile(
        path=missing_file,
        language=Language.CPP,
    )

    assert source.exists is False