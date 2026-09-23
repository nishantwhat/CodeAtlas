"""Data Flow Graph (DFG) and Def-Use analysis module."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from program_graph.analysis.ast import ASTNode, SourceLocation, walk_ast


class DefUseType(str, Enum):
    """Classification of variable sites."""
    DEF = "def"
    USE = "use"


class DFGEdgeType(str, Enum):
    """Types of data flow edges."""
    DATA_DEPENDENCY = "data_dependency"
    PARAM_PASSING = "param_passing"


class VariableSymbol(BaseModel):
    """Represents a variable or parameter symbol in code."""
    model_config = ConfigDict(frozen=True)

    name: str = Field(..., description="Variable identifier name")
    type_spelling: str | None = Field(default=None, description="Type description string")
    decl_ast_id: int | None = Field(default=None, description="AST node ID of original declaration")


class DefUseSite(BaseModel):
    """A single definition (DEF) or usage (USE) location in code."""
    model_config = ConfigDict(frozen=True)

    site_id: str = Field(..., description="Unique deterministic identifier for site")
    symbol: VariableSymbol = Field(..., description="Target variable symbol")
    site_type: DefUseType = Field(..., description="DEF or USE site classification")
    ast_node_id: int = Field(..., description="AST node ID associated with site")
    location: SourceLocation | None = Field(default=None, description="Source code location")


class DFGEdge(BaseModel):
    """Directed data dependency edge from a DEF site to a USE site."""
    model_config = ConfigDict(frozen=True)

    def_site_id: str = Field(..., description="ID of definition site")
    use_site_id: str = Field(..., description="ID of usage site")
    symbol_name: str = Field(..., description="Name of variable symbol involved")
    edge_type: DFGEdgeType = Field(default=DFGEdgeType.DATA_DEPENDENCY, description="Edge type semantics")


class DataFlowGraph(BaseModel):
    """Data Flow Graph container holding all def-use sites and data flow edges."""
    model_config = ConfigDict(frozen=True)

    def_sites: dict[str, DefUseSite] = Field(default_factory=dict, description="Definition sites indexed by ID")
    use_sites: dict[str, DefUseSite] = Field(default_factory=dict, description="Usage sites indexed by ID")
    edges: list[DFGEdge] = Field(default_factory=list, description="Data dependency edges")


class DFGBuilder:
    """Extracts variable def-use sites and constructs Data Flow Graphs from AST trees."""

    def __init__(self) -> None:
        self._site_counter = 0

    def _next_site_id(self, prefix: str = "site") -> str:
        self._site_counter += 1
        return f"{prefix}_{self._site_counter}"

    def build(self, root: ASTNode) -> DataFlowGraph:
        """Construct a DataFlowGraph for an entire AST or subtree."""
        self._site_counter = 0

        def_sites: dict[str, DefUseSite] = {}
        use_sites: dict[str, DefUseSite] = {}
        var_decls: dict[str, VariableSymbol] = {}
        active_defs: dict[str, list[str]] = {}  # symbol_name -> list of def_site_ids

        # Walk AST to discover declarations, defs, and uses
        for node in walk_ast(root):
            kind = node.kind

            # 1. Variable / Parameter Declarations
            if kind in ("VAR_DECL", "PARM_DECL"):
                sym_name = node.spelling
                if sym_name:
                    sym = VariableSymbol(
                        name=sym_name,
                        type_spelling=node.type_spelling,
                        decl_ast_id=node.id,
                    )
                    var_decls[sym_name] = sym

                    # If variable has an initializer child or is a parameter
                    if node.children or kind == "PARM_DECL":
                        def_id = self._next_site_id("def")
                        site = DefUseSite(
                            site_id=def_id,
                            symbol=sym,
                            site_type=DefUseType.DEF,
                            ast_node_id=node.id,
                            location=node.location,
                        )
                        def_sites[def_id] = site
                        active_defs.setdefault(sym_name, []).append(def_id)

            # 2. Variable Usages (DECL_REF_EXPR)
            elif kind in ("DECL_REF_EXPR", "UNEXPOSED_EXPR"):
                sym_name = node.spelling
                if sym_name and sym_name in var_decls:
                    use_id = self._next_site_id("use")
                    sym = var_decls[sym_name]
                    use_site = DefUseSite(
                        site_id=use_id,
                        symbol=sym,
                        site_type=DefUseType.USE,
                        ast_node_id=node.id,
                        location=node.location,
                    )
                    use_sites[use_id] = use_site

            # 3. Binary Assignments (=, +=, -=, etc.)
            elif kind in ("BINARY_OPERATOR", "COMPOUND_ASSIGNMENT_OPERATOR"):
                # If operator is an assignment, left child is DEF
                if node.spelling and "=" in node.spelling and node.children:
                    lhs = node.children[0]
                    sym_name = lhs.spelling
                    if sym_name and sym_name in var_decls:
                        def_id = self._next_site_id("def")
                        sym = var_decls[sym_name]
                        def_site = DefUseSite(
                            site_id=def_id,
                            symbol=sym,
                            site_type=DefUseType.DEF,
                            ast_node_id=lhs.id,
                            location=lhs.location,
                        )
                        def_sites[def_id] = def_site
                        active_defs.setdefault(sym_name, []).append(def_id)

        # Connect DEF sites to USE sites for each symbol
        edges: list[DFGEdge] = []
        for use_id, use_site in use_sites.items():
            sym_name = use_site.symbol.name
            if sym_name in active_defs:
                # Link to recent def site(s)
                for def_id in active_defs[sym_name]:
                    edges.append(
                        DFGEdge(
                            def_site_id=def_id,
                            use_site_id=use_id,
                            symbol_name=sym_name,
                            edge_type=DFGEdgeType.DATA_DEPENDENCY,
                        )
                    )

        return DataFlowGraph(
            def_sites=def_sites,
            use_sites=use_sites,
            edges=edges,
        )
