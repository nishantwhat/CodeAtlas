# Project Progress Log

## Milestone 0 — Repository and Environment Setup
- **Status**: COMPLETE

---

## Milestone 1 — Source Ingestion
- **Status**: COMPLETE

---

## Milestone 2 — AST Extraction
- **Status**: COMPLETE

### Implemented:
- `program_graph.analysis.ast`: Defined `ASTNode`, `ASTRepresentation`, `SourceLocationInfo`, `SourceRangeInfo`, and `ASTExtractionError`.
- `ASTExtractor`: libclang-backed parser extracting typed syntax trees and filtering external library noise.
- Traversal & Search: Added `walk_ast` depth-first generator and `find_nodes_by_kind` search helper.

### Tests Summary:
- 21 total tests passing across all test modules.
- Covered C function declarations, C++ classes/namespaces, AST node serialization, diagnostic capture, and end-to-end pipeline extraction.

### Known Limitations:
- Unused template parameters in uninstantiated C++ templates may not produce full AST subtrees until instantiated.

### Architecture Decisions:
- Isolated `clang.cindex` dependencies completely inside `src/program_graph/analysis/ast.py`.
- Rendered AST structure cleanly serializable to dictionary representations for future API/web rendering.

### Git Commits:
- `feat(ast): define AST representation models`
- `feat(ast): implement Clang AST extractor`
- `feat(ast): add visitor traversal and diagnostic utilities`
- `test(ast): validate AST extraction pipeline`

---

## Next Milestone: Milestone 3 — Control Flow Graph (CFG) Construction