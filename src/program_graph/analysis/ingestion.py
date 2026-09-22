"""Data structures and models for C/C++ source code ingestion."""

from enum import Enum
from pathlib import Path
from typing import List, Optional, Set
from pydantic import BaseModel, Field, field_validator


class Language(str, Enum):
    C = "c"
    CPP = "cpp"


class SourceFile(BaseModel):
    """Represents an ingested C/C++ source file."""

    path: Path
    language: Language
    project_root: Optional[Path] = None
    compiler_flags: List[str] = Field(default_factory=list)
    compilation_directory: Optional[Path] = None

    @field_validator("path", "project_root", "compilation_directory", mode="before")
    @classmethod
    def normalize_path(cls, v: Optional[Path | str]) -> Optional[Path]:
        if v is None:
            return None
        return Path(v).resolve()

    @property
    def exists(self) -> bool:
        return self.path.exists() and self.path.is_file()


class IngestionError(Exception):
    """Base exception for source ingestion failures."""

    pass


class CompilationDatabaseError(IngestionError):
    """Exception raised when reading or interpreting compile_commands.json fails."""

    pass


class StandaloneIngestor:
    """Ingestor for standalone C/C++ source files."""

    C_EXTENSIONS: Set[str] = {".c", ".h"}
    CPP_EXTENSIONS: Set[str] = {".cpp", ".cc", ".cxx", ".hpp", ".hxx", ".h"}

    @classmethod
    def detect_language(cls, path: Path) -> Language:
        ext = path.suffix.lower()
        if ext in cls.CPP_EXTENSIONS and ext not in {".c"}:
            return Language.CPP
        elif ext in cls.C_EXTENSIONS:
            return Language.C
        raise IngestionError(f"Unsupported file extension '{ext}' for file: {path}")

    def ingest(self, file_path: Path | str, default_flags: Optional[List[str]] = None) -> SourceFile:
        path = Path(file_path).resolve()

        if not path.exists():
            raise IngestionError(f"Source file does not exist: {path}")

        if not path.is_file():
            raise IngestionError(f"Path is not a regular file: {path}")

        language = self.detect_language(path)
        flags = default_flags.copy() if default_flags else []

        return SourceFile(
            path=path,
            language=language,
            project_root=path.parent,
            compiler_flags=flags,
            compilation_directory=path.parent,
        )