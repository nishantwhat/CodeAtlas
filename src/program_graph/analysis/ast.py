"""AST Extraction module using libclang bindings."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path

import clang.cindex
from pydantic import BaseModel, ConfigDict, Field

from program_graph.analysis.exceptions import ASTExtractionError
from program_graph.analysis.ingestion import Language, TranslationUnitTarget


class SourceLocation(BaseModel):
    """Line and column position within a source file."""
    model_config = ConfigDict(frozen=True)

    line: int = Field(..., description="1-based line number")
    column: int = Field(..., description="1-based column number")
    file_path: Path | None = Field(default=None, description="Path to source file")


# Explicit alias for backwards compatibility
SourceLocationInfo = SourceLocation


class SourceRange(BaseModel):
    """Start and end coordinates for an AST node."""
    model_config = ConfigDict(frozen=True)

    start: SourceLocation
    end: SourceLocation


# Explicit alias for backwards compatibility
SourceRangeInfo = SourceRange


class ASTNode(BaseModel):
    """Node representation in extracted AST graph."""
    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)

    id: int = Field(..., alias="node_id")
    kind: str
    spelling: str = ""
    display_name: str = ""
    location: SourceLocation | None = None
    range: SourceRange | None = None
    type_spelling: str | None = None
    children: list[ASTNode] = Field(default_factory=list)

    @property
    def node_id(self) -> int:
        """Alias for node ID."""
        return self.id

    def to_dict(self) -> dict:
        """Serialize the node to a dictionary representation."""
        return self.model_dump(by_alias=True)


class ASTRepresentation(BaseModel):
    """Root container for extracted TranslationUnit AST."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    target: TranslationUnitTarget
    root: ASTNode
    diagnostics: list[str] = Field(default_factory=list)


class ASTExtractor:
    """Parses source files into structured ASTRepresentation graphs via libclang."""

    def __init__(self, libclang_path: str | Path | None = None) -> None:
        if libclang_path:
            clang.cindex.Config.set_library_file(str(libclang_path))
        self.index = clang.cindex.Index.create()
        self._node_id_counter = 0

    def _next_id(self) -> int:
        self._node_id_counter += 1
        return self._node_id_counter

    def extract(
        self,
        target: TranslationUnitTarget,
        include_headers: bool = False,
    ) -> ASTRepresentation:
        """Parse source file using target flags and return complete ASTRepresentation."""
        if not target.source_path.exists():
            raise ASTExtractionError(f"Source target file does not exist: {target.source_path}")

        self._node_id_counter = 0
        args = list(target.compilation_context.arguments)

        if "-x" not in args:
            lang_flag = "c++" if target.language == Language.CPP else "c"
            args.extend(["-x", lang_flag])

        source_str = str(target.source_path.resolve())

        try:
            tu = self.index.parse(
                path=source_str,
                args=args,
                options=clang.cindex.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD,
            )
        except Exception as e:
            raise ASTExtractionError(
                f"Failed to parse source target '{source_str}' with libclang: {e}"
            ) from e

        if not tu or not tu.cursor:
            raise ASTExtractionError(
                f"Failed to parse source target '{source_str}' with libclang: empty cursor returned"
            )

        root_node = self._build_node(
            cursor=tu.cursor,
            target_file=target.source_path.resolve(),
            include_headers=include_headers,
        )

        diags = [diag.spelling for diag in tu.diagnostics] if tu.diagnostics else []

        return ASTRepresentation(
            target=target,
            root=root_node,
            diagnostics=diags,
        )

    def _build_node(
        self,
        cursor: clang.cindex.Cursor,
        target_file: Path,
        include_headers: bool,
    ) -> ASTNode:
        node_id = self._next_id()

        loc = None
        if cursor.location and cursor.location.file:
            loc = SourceLocation(
                line=cursor.location.line,
                column=cursor.location.column,
                file_path=Path(cursor.location.file.name),
            )

        extent = None
        if (
            cursor.extent
            and cursor.extent.start
            and cursor.extent.start.file
            and cursor.extent.end
            and cursor.extent.end.file
        ):
            extent = SourceRange(
                start=SourceLocation(
                    line=cursor.extent.start.line,
                    column=cursor.extent.start.column,
                    file_path=Path(cursor.extent.start.file.name),
                ),
                end=SourceLocation(
                    line=cursor.extent.end.line,
                    column=cursor.extent.end.column,
                    file_path=Path(cursor.extent.end.file.name),
                ),
            )

        children: list[ASTNode] = []
        for child in cursor.get_children():
            if not include_headers and child.location and child.location.file:
                try:
                    child_file = Path(child.location.file.name).resolve()
                    if child_file != target_file:
                        continue
                except (ValueError, OSError):
                    # Handle invalid file paths gracefully without filtering valid nodes
                    pass

            children.append(
                self._build_node(
                    cursor=child,
                    target_file=target_file,
                    include_headers=include_headers,
                )
            )

        type_spelling = cursor.type.spelling if cursor.type else None

        return ASTNode(
            id=node_id,
            kind=cursor.kind.name,
            spelling=cursor.spelling or "",
            display_name=cursor.displayname or "",
            location=loc,
            range=extent,
            type_spelling=type_spelling,
            children=children,
        )


def find_nodes_by_kind(
    node: ASTNode,
    kinds: set[str] | list[str] | str,
) -> list[ASTNode]:
    """Find all nodes in subtree matching the given kind(s)."""
    target_kinds = {kinds} if isinstance(kinds, str) else set(kinds)
    results: list[ASTNode] = []

    if node.kind in target_kinds:
        results.append(node)

    for child in node.children:
        results.extend(find_nodes_by_kind(child, target_kinds))

    return results


def walk_ast(node: ASTNode) -> Iterator[ASTNode]:
    """Generator that yields all nodes in the AST tree depth-first."""
    yield node
    for child in node.children:
        yield from walk_ast(child)


def traverse_ast(
    node: ASTNode,
    visitor: Callable[[ASTNode], None],
) -> None:
    """Perform a depth-first traversal of the AST tree using a visitor callback."""
    visitor(node)
    for child in node.children:
        traverse_ast(child, visitor)