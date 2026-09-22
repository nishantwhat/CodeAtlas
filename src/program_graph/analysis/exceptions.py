"""Custom exceptions for the program_graph package."""


class ProgramGraphError(Exception):
    """Base exception for all program_graph errors."""


class IngestionError(ProgramGraphError):
    """Raised when source file or project ingestion fails."""


class SourceNotFoundError(IngestionError):
    """Raised when a requested source file cannot be found."""


class UnsupportedLanguageError(IngestionError):
    """Raised when a file extension is not recognized as C or C++."""


class CompilationDatabaseError(IngestionError):
    """Raised when compile_commands.json is invalid, missing, or malformed."""


class ASTExtractionError(IngestionError):
    """Raised when Clang fails to parse or extract the AST from a source target."""