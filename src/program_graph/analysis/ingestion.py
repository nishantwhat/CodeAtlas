"""Source code ingestion, discovery, and compilation context resolution module."""

from __future__ import annotations

import json
import shlex
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

from program_graph.analysis.exceptions import (
    CompilationDatabaseError,
    IngestionError,
    SourceNotFoundError,
    UnsupportedLanguageError,
)


class Language(str, Enum):
    """Supported source programming languages."""
    C = "c"
    CPP = "cpp"


C_EXTENSIONS: set[str] = {".c", ".h"}
CPP_EXTENSIONS: set[str] = {".cpp", ".hpp", ".cc", ".cxx", ".hh", ".C", ".H"}


class CompilationContext(BaseModel):
    """Compiler arguments and context for parsing a translation unit."""
    model_config = ConfigDict(frozen=True)

    arguments: list[str] = Field(
        default_factory=list,
        description="Compiler command-line flags and include options",
    )
    directory: Path | None = Field(
        default=None,
        description="Working directory during compilation",
    )


class TranslationUnitTarget(BaseModel):
    """Represents a fully ingested and validated C/C++ source file target."""

    model_config = ConfigDict(frozen=True)

    source_path: Path = Field(
        ..., description="Absolute path to the validated source file"
    )
    language: Language = Field(..., description="Detected programming language")
    project_root: Path | None = Field(
        default=None, description="Root directory of the project containing the file"
    )
    compilation_context: CompilationContext = Field(
        default_factory=CompilationContext,
        description="Compiler flags and working directory required for parsing",
    )

    @field_validator("source_path")
    @classmethod
    def validate_absolute_path(cls, v: Path) -> Path:
        """Ensure paths are normalized and absolute."""
        return v.resolve()

    @property
    def path(self) -> Path:
        """Backwards-compatible alias for source_path."""
        return self.source_path

    @property
    def compiler_flags(self) -> list[str]:
        """Backwards-compatible access to compilation arguments."""
        return self.compilation_context.arguments


def _clean_compiler_arguments(args: list[str]) -> list[str]:
    """Strip compiler invocation binary, output flags (-o), action flags (-c), and positional source inputs."""
    cleaned: list[str] = []
    skip_next = False

    for i, arg in enumerate(args):
        if skip_next:
            skip_next = False
            continue

        if i == 0 and not arg.startswith("-"):
            continue

        if arg in ("-o", "--output"):
            skip_next = True
            continue

        if arg.startswith(("-o", "--output=")):
            continue

        if arg in ("-c", "-S", "-E"):
            continue

        if not arg.startswith("-"):
            ext = Path(arg).suffix.lower()
            if ext in (C_EXTENSIONS | CPP_EXTENSIONS):
                continue

        cleaned.append(arg)

    return cleaned


class SourceIngestor:
    """Ingests individual standalone C/C++ source files."""

    def __init__(
        self,
        project_root: Path | str | None = None,
        default_c_standard: str = "c11",
        default_cpp_standard: str = "c++17",
    ) -> None:
        self.project_root = Path(project_root).resolve() if project_root else None
        self.default_c_standard = default_c_standard
        self.default_cpp_standard = default_cpp_standard

    def detect_language(self, source_path: Path) -> Language:
        """Detect programming language based on file extension."""
        ext = source_path.suffix
        if ext in C_EXTENSIONS:
            return Language.C
        if ext in CPP_EXTENSIONS:
            return Language.CPP
        raise UnsupportedLanguageError(f"Unsupported file extension: {ext} for file {source_path}")

    def ingest(
        self,
        source_path: Path | str,
        default_flags: list[str] | None = None,
    ) -> TranslationUnitTarget:
        """Validate and construct a TranslationUnitTarget for a standalone source file."""
        path = Path(source_path).resolve()

        if not path.exists():
            raise SourceNotFoundError(f"Source file does not exist: {path}")

        if not path.is_file():
            raise IngestionError(f"Source path is not a regular file: {path}")

        language = self.detect_language(path)

        args: list[str] = []
        if default_flags is not None:
            args.extend(_clean_compiler_arguments(default_flags))
        else:
            if language == Language.C:
                args.extend(["-x", "c", f"-std={self.default_c_standard}"])
            else:
                args.extend(["-x", "c++", f"-std={self.default_cpp_standard}"])

        proj_root = self.project_root if self.project_root else path.parent

        context = CompilationContext(
            arguments=args,
            directory=proj_root,
        )

        return TranslationUnitTarget(
            source_path=path,
            language=language,
            project_root=proj_root,
            compilation_context=context,
        )


class CompilationDatabaseIngestor:
    """Ingests source targets using a JSON compilation database (compile_commands.json)."""

    def __init__(self, cdb_path: Path | str | None = None, strict: bool = False) -> None:
        self.cdb_path: Path | None = Path(cdb_path).resolve() if cdb_path else None
        self._commands: list[dict] = []
        self.strict = strict
        if self.cdb_path:
            self.load(self.cdb_path)

    def load(self, cdb_path: Path | str) -> None:
        """Safely loads and parses the compile_commands.json file."""
        path = Path(cdb_path).resolve()
        if not path.exists():
            raise CompilationDatabaseError(f"Compilation database file not found: {path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, list):
                raise CompilationDatabaseError("Malformed JSON: Compilation database must be a top-level list.")

            self._commands = data
            self.cdb_path = path

        except (json.JSONDecodeError, ValueError) as e:
            raise CompilationDatabaseError(f"Malformed JSON compilation database structure: {e}") from e

    def get_target(self, source_path: Path | str) -> TranslationUnitTarget:
        """Find source entry in compilation database and return its TranslationUnitTarget."""
        path = Path(source_path).resolve()
        if not path.exists():
            raise SourceNotFoundError(f"Source file does not exist: {path}")

        for entry in self._commands:
            entry_file = Path(entry.get("file", "")).resolve()
            if entry_file == path:
                directory = Path(entry.get("directory", path.parent)).resolve()
                command = entry.get("command")
                args = entry.get("arguments")
                if args is None and command:
                    args = shlex.split(command)
                cleaned_args = _clean_compiler_arguments(args or [])

                ext = path.suffix
                lang = Language.CPP if ext in CPP_EXTENSIONS else Language.C

                return TranslationUnitTarget(
                    source_path=path,
                    language=lang,
                    project_root=directory,
                    compilation_context=CompilationContext(
                        arguments=cleaned_args,
                        directory=directory,
                    ),
                )

        if self.strict:
            raise CompilationDatabaseError(f"Source file {source_path} not found in compilation database")

        return SourceIngestor(project_root=path.parent).ingest(path)

    def ingest(self, source_path: Path | str) -> TranslationUnitTarget:
        """Ingest the target file by resolving its compilation context."""
        return self.get_target(source_path)
