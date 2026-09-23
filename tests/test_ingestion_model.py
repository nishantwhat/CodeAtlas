"""Tests for ingestion models and domain targets."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from program_graph.analysis.ingestion import (
    CompilationContext,
    Language,
    TranslationUnitTarget,
)


def test_translation_unit_target_creation(tmp_path: Path):
    """Verify TranslationUnitTarget initialization and path resolution."""
    dummy_file = tmp_path / "main.cpp"
    dummy_file.touch()

    target = TranslationUnitTarget(
        source_path=dummy_file,
        language=Language.CPP,
        compilation_context=CompilationContext(arguments=["-std=c++17"]),
    )

    assert target.source_path == dummy_file.resolve()
    assert target.language == Language.CPP
    assert target.compilation_context.arguments == ["-std=c++17"]


def test_translation_unit_target_path_validation():
    """Verify validation requires a valid path type."""
    with pytest.raises(ValidationError):
        TranslationUnitTarget(
            source_path=None,  # type: ignore
            language=Language.C,
        )