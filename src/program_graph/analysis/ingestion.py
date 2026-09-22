"""Data structures and models for C/C++ source code ingestion."""

from enum import Enum
import json
import shlex
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
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
    CPP_EXTENSIONS: Set[str] = {".cpp", ".cc", ".cxx", ".hpp", ".hxx"}

    @classmethod
    def detect_language(cls, path: Path) -> Language:
        ext = path.suffix.lower()
        if ext in cls.CPP_EXTENSIONS:
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


class CompilationDatabaseIngestor:
    """Ingestor for C/C++ source files using compile_commands.json."""

    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path).resolve()
        self.entries: Dict[Path, Dict[str, Any]] = {}
        self._load_db()

    def _load_db(self) -> None:
        if not self.db_path.exists():
            raise CompilationDatabaseError(f"Compilation database not found: {self.db_path}")

        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise CompilationDatabaseError(f"Malformed JSON in compilation database: {e}") from e

        if not isinstance(data, list):
            raise CompilationDatabaseError("Compilation database JSON root must be an array")

        for entry in data:
            if not isinstance(entry, dict) or "file" not in entry:
                continue

            file_ref = Path(entry["file"])
            comp_dir = Path(entry.get("directory", self.db_path.parent))
            
            # Resolve relative file path using compilation directory
            abs_file = file_ref if file_ref.is_absolute() else (comp_dir / file_ref).resolve()
            self.entries[abs_file] = entry

    def _extract_flags(self, entry: Dict[str, Any]) -> List[str]:
        if "arguments" in entry and isinstance(entry["arguments"], list):
            raw_args = entry["arguments"]
        elif "command" in entry and isinstance(entry["command"], str):
            raw_args = shlex.split(entry["command"])
        else:
            return []

        # Omit compiler executable name and the source file argument itself
        flags: List[str] = []
        skip_next = False
        
        for idx, arg in enumerate(raw_args[1:], start=1):
            if skip_next:
                skip_next = False
                continue
            if arg in {"-o", "-c"}:
                if arg == "-o":
                    skip_next = True
                continue
            flags.append(arg)

        return flags

    def ingest(self, file_path: Path | str) -> SourceFile:
        path = Path(file_path).resolve()

        if not path.exists():
            raise IngestionError(f"Source file does not exist: {path}")

        if path not in self.entries:
            raise CompilationDatabaseError(
                f"Source file {path} not found in compilation database at {self.db_path}"
            )

        entry = self.entries[path]
        comp_dir = Path(entry.get("directory", self.db_path.parent)).resolve()
        language = StandaloneIngestor.detect_language(path)
        flags = self._extract_flags(entry)

        return SourceFile(
            path=path,
            language=language,
            project_root=self.db_path.parent,
            compiler_flags=flags,
            compilation_directory=comp_dir,
        )