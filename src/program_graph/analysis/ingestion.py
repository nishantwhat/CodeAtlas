"""Data structures and models for C/C++ source code ingestion."""

from enum import Enum
from pathlib import Path
from typing import List, Optional
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