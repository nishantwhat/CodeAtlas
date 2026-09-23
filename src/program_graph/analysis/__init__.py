"""Analysis module providing source ingestion, exception hierarchy, and AST extraction."""

from program_graph.analysis.ast import (
    ASTExtractor,
    ASTNode,
    ASTRepresentation,
    SourceLocation,
    SourceLocationInfo,
    SourceRange,
    SourceRangeInfo,
    find_nodes_by_kind,
    traverse_ast,
    walk_ast,
)
from program_graph.analysis.exceptions import (
    ASTExtractionError,
    CompilationDatabaseError,
    IngestionError,
    ProgramGraphError,
    SourceNotFoundError,
    UnsupportedLanguageError,
)
from program_graph.analysis.ingestion import (
    CompilationContext,
    CompilationDatabaseIngestor,
    Language,
    SourceIngestor,
    TranslationUnitTarget,
)

__all__ = [
    "ASTExtractionError",
    "ASTExtractor",
    "ASTNode",
    "ASTRepresentation",
    "CompilationContext",
    "CompilationDatabaseError",
    "CompilationDatabaseIngestor",
    "IngestionError",
    "Language",
    "ProgramGraphError",
    "SourceIngestor",
    "SourceLocation",
    "SourceLocationInfo",
    "SourceNotFoundError",
    "SourceRange",
    "SourceRangeInfo",
    "TranslationUnitTarget",
    "UnsupportedLanguageError",
    "find_nodes_by_kind",
    "traverse_ast",
    "walk_ast",
]
