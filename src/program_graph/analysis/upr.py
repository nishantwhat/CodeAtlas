"""Unified Program Representation (UPR) and serialization module."""

from __future__ import annotations

import json

from pydantic import BaseModel, ConfigDict, Field

from program_graph.analysis.ast import (
    ASTNode,
    ASTRepresentation,
    SourceLocation,
    find_nodes_by_kind,
    walk_ast,
)
from program_graph.analysis.cfg import ControlFlowGraph, build_cfgs_for_ast
from program_graph.analysis.dfg import DataFlowGraph, DFGBuilder
from program_graph.analysis.exceptions import UPRError
from program_graph.analysis.ingestion import TranslationUnitTarget


class CallSite(BaseModel):
    """Function call relationship between caller and callee."""
    model_config = ConfigDict(frozen=True)

    caller_function: str = Field(..., description="Name of caller function/method")
    callee_function: str = Field(..., description="Name of target function being called")
    ast_node_id: int = Field(..., description="AST node ID of CALL_EXPR")
    location: SourceLocation | None = Field(default=None, description="Source code location of call site")


class UnifiedProgramRepresentation(BaseModel):
    """Complete Unified Program Representation (UPR) for a TranslationUnit.
    
    Combines Source Ingestion metadata, AST tree, Function CFGs, DFG def-use relationships,
    and Function Call Graph connections into a single serializable object.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    target: TranslationUnitTarget = Field(..., description="Source file ingestion target metadata")
    ast: ASTRepresentation = Field(..., description="Extracted libclang AST graph")
    cfgs: dict[str, ControlFlowGraph] = Field(default_factory=dict, description="Control Flow Graphs for each function")
    dfg: DataFlowGraph = Field(default_factory=DataFlowGraph, description="Data Flow Graph for variable dependencies")
    call_sites: list[CallSite] = Field(default_factory=list, description="Extracted function call site relationships")

    def to_dict(self) -> dict:
        """Serialize UPR object into a standard dictionary representation."""
        return self.model_dump(mode="json")

    def to_json(self, indent: int = 2) -> str:
        """Serialize UPR object into a JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: dict) -> UnifiedProgramRepresentation:
        """Construct a UnifiedProgramRepresentation object from a dictionary."""
        try:
            return cls.model_validate(data)
        except Exception as e:
            raise UPRError(f"Failed to deserialize UPR from dictionary: {e}") from e

    @classmethod
    def from_json(cls, json_str: str) -> UnifiedProgramRepresentation:
        """Construct a UnifiedProgramRepresentation object from a JSON string."""
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except Exception as e:
            raise UPRError(f"Failed to deserialize UPR from JSON: {e}") from e


def extract_call_sites(ast_root: ASTNode) -> list[CallSite]:
    """Find all CALL_EXPR / CXX_MEMBER_CALL_EXPR nodes and map caller -> callee relationships."""
    call_sites: list[CallSite] = []

    # Find top-level function declarations
    func_nodes = find_nodes_by_kind(
        ast_root,
        ["FUNCTION_DECL", "CXX_METHOD", "CONSTRUCTOR", "DESTRUCTOR"],
    )

    for func in func_nodes:
        caller_name = func.spelling or func.display_name or "unnamed_function"

        # Search for call expressions inside function subtree
        for node in walk_ast(func):
            if node.kind in ("CALL_EXPR", "CXX_MEMBER_CALL_EXPR"):
                callee_name = node.spelling or node.display_name
                # If spelling is empty, attempt to inspect child expression
                if not callee_name and node.children:
                    callee_name = node.children[0].spelling or node.children[0].display_name

                if callee_name:
                    call_sites.append(
                        CallSite(
                            caller_function=caller_name,
                            callee_function=callee_name,
                            ast_node_id=node.id,
                            location=node.location,
                        )
                    )

    return call_sites


def build_upr(
    target: TranslationUnitTarget,
    ast_rep: ASTRepresentation,
) -> UnifiedProgramRepresentation:
    """Build a complete UnifiedProgramRepresentation from an ingested target and AST."""
    try:
        cfgs = build_cfgs_for_ast(ast_rep.root)
        dfg = DFGBuilder().build(ast_rep.root)
        call_sites = extract_call_sites(ast_rep.root)

        return UnifiedProgramRepresentation(
            target=target,
            ast=ast_rep,
            cfgs=cfgs,
            dfg=dfg,
            call_sites=call_sites,
        )
    except Exception as e:
        raise UPRError(f"Failed to assemble Unified Program Representation: {e}") from e
