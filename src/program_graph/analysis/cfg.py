"""Control Flow Graph (CFG) extraction and modeling module."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from program_graph.analysis.ast import ASTNode, SourceRange, find_nodes_by_kind
from program_graph.analysis.exceptions import CFGError


class CFGNodeKind(str, Enum):
    """Types of control flow graph nodes."""
    ENTRY = "entry"
    EXIT = "exit"
    STATEMENT = "statement"
    CONDITION = "condition"
    LOOP_HEADER = "loop_header"


class CFGEdgeType(str, Enum):
    """Types of control flow graph edges."""
    UNCONDITIONAL = "unconditional"
    TRUE_BRANCH = "true_branch"
    FALSE_BRANCH = "false_branch"
    LOOP_BODY = "loop_body"
    LOOP_BACK = "loop_back"
    FALLTHROUGH = "fallthrough"


class CFGNode(BaseModel):
    """Node in a function's Control Flow Graph."""
    model_config = ConfigDict(frozen=True)

    node_id: str = Field(..., description="Unique deterministic identifier for CFG node")
    kind: CFGNodeKind = Field(..., description="Node classification type")
    ast_node_ids: list[int] = Field(default_factory=list, description="IDs of AST nodes mapped to this CFG node")
    label: str = Field(default="", description="Human-readable label or code preview")
    source_range: SourceRange | None = Field(default=None, description="Source code range associated with block")


class CFGEdge(BaseModel):
    """Directed edge between CFG nodes."""
    model_config = ConfigDict(frozen=True)

    source_id: str = Field(..., description="Source CFG node ID")
    target_id: str = Field(..., description="Target CFG node ID")
    edge_type: CFGEdgeType = Field(default=CFGEdgeType.UNCONDITIONAL, description="Edge semantics")
    label: str = Field(default="", description="Edge description/label")


class ControlFlowGraph(BaseModel):
    """Control Flow Graph container for a single function or method."""
    model_config = ConfigDict(frozen=True)

    function_name: str = Field(..., description="Name of the function/method")
    entry_node_id: str = Field(..., description="ID of entry node")
    exit_node_id: str = Field(..., description="ID of exit node")
    nodes: dict[str, CFGNode] = Field(default_factory=dict, description="CFG nodes mapped by ID")
    edges: list[CFGEdge] = Field(default_factory=list, description="List of directed CFG edges")


class CFGBuilder:
    """Constructs Control Flow Graphs from AST function nodes."""

    def __init__(self) -> None:
        self._node_counter = 0

    def _next_node_id(self, prefix: str = "cfg_node") -> str:
        self._node_counter += 1
        return f"{prefix}_{self._node_counter}"

    def build_for_function(self, func_node: ASTNode) -> ControlFlowGraph:
        """Build a CFG for a FUNCTION_DECL or CXX_METHOD AST node."""
        if func_node.kind not in ("FUNCTION_DECL", "CXX_METHOD", "CONSTRUCTOR", "DESTRUCTOR"):
            raise CFGError(f"Cannot build CFG for non-function AST node kind: {func_node.kind}")

        func_name = func_node.spelling or func_node.display_name or "unnamed_function"
        self._node_counter = 0

        entry_id = self._next_node_id("entry")
        exit_id = self._next_node_id("exit")

        entry_node = CFGNode(
            node_id=entry_id,
            kind=CFGNodeKind.ENTRY,
            ast_node_ids=[func_node.id],
            label=f"Entry: {func_name}",
            source_range=func_node.range,
        )
        exit_node = CFGNode(
            node_id=exit_id,
            kind=CFGNodeKind.EXIT,
            ast_node_ids=[func_node.id],
            label=f"Exit: {func_name}",
            source_range=func_node.range,
        )

        nodes: dict[str, CFGNode] = {
            entry_id: entry_node,
            exit_id: exit_node,
        }
        edges: list[CFGEdge] = []

        # Find the body (COMPOUND_STMT) child of the function node
        compound_body = None
        for child in func_node.children:
            if child.kind == "COMPOUND_STMT":
                compound_body = child
                break

        if compound_body is None or not compound_body.children:
            # Empty function body
            edges.append(CFGEdge(source_id=entry_id, target_id=exit_id, edge_type=CFGEdgeType.UNCONDITIONAL))
            return ControlFlowGraph(
                function_name=func_name,
                entry_node_id=entry_id,
                exit_node_id=exit_id,
                nodes=nodes,
                edges=edges,
            )

        # Recursively process the function body statements
        current_source_ids = [entry_id]
        final_sources = self._process_statement_list(
            stmts=compound_body.children,
            incoming_ids=current_source_ids,
            exit_id=exit_id,
            nodes=nodes,
            edges=edges,
        )

        for src_id in final_sources:
            # Prevent adding duplicate entry->exit edge if already connected or handled
            if src_id != exit_id:
                edges.append(CFGEdge(source_id=src_id, target_id=exit_id, edge_type=CFGEdgeType.UNCONDITIONAL))

        return ControlFlowGraph(
            function_name=func_name,
            entry_node_id=entry_id,
            exit_node_id=exit_id,
            nodes=nodes,
            edges=edges,
        )

    def _process_statement_list(
        self,
        stmts: list[ASTNode],
        incoming_ids: list[str],
        exit_id: str,
        nodes: dict[str, CFGNode],
        edges: list[CFGEdge],
    ) -> list[str]:
        current_incoming = incoming_ids

        for stmt in stmts:
            if not current_incoming:
                break
            current_incoming = self._process_statement(
                stmt=stmt,
                incoming_ids=current_incoming,
                exit_id=exit_id,
                nodes=nodes,
                edges=edges,
            )

        return current_incoming

    def _process_statement(
        self,
        stmt: ASTNode,
        incoming_ids: list[str],
        exit_id: str,
        nodes: dict[str, CFGNode],
        edges: list[CFGEdge],
    ) -> list[str]:
        kind = stmt.kind

        if kind == "IF_STMT":
            return self._process_if_stmt(stmt, incoming_ids, exit_id, nodes, edges)
        elif kind in ("WHILE_STMT", "FOR_STMT", "DO_STMT"):
            return self._process_loop_stmt(stmt, incoming_ids, exit_id, nodes, edges)
        elif kind == "RETURN_STMT":
            ret_id = self._next_node_id("stmt")
            ret_node = CFGNode(
                node_id=ret_id,
                kind=CFGNodeKind.STATEMENT,
                ast_node_ids=[stmt.id],
                label=f"return ({stmt.spelling})",
                source_range=stmt.range,
            )
            nodes[ret_id] = ret_node
            for inc in incoming_ids:
                edges.append(CFGEdge(source_id=inc, target_id=ret_id, edge_type=CFGEdgeType.UNCONDITIONAL))
            edges.append(CFGEdge(source_id=ret_id, target_id=exit_id, edge_type=CFGEdgeType.UNCONDITIONAL))
            return []  # Control terminates after return
        elif kind == "COMPOUND_STMT":
            return self._process_statement_list(stmt.children, incoming_ids, exit_id, nodes, edges)
        else:
            # Regular statement (DECL_STMT, BINARY_OPERATOR, CALL_EXPR, etc.)
            stmt_id = self._next_node_id("stmt")
            label_text = f"{stmt.kind} ({stmt.spelling})" if stmt.spelling else stmt.kind
            node = CFGNode(
                node_id=stmt_id,
                kind=CFGNodeKind.STATEMENT,
                ast_node_ids=[stmt.id],
                label=label_text,
                source_range=stmt.range,
            )
            nodes[stmt_id] = node
            for inc in incoming_ids:
                edges.append(CFGEdge(source_id=inc, target_id=stmt_id, edge_type=CFGEdgeType.UNCONDITIONAL))
            return [stmt_id]

    def _process_if_stmt(
        self,
        if_node: ASTNode,
        incoming_ids: list[str],
        exit_id: str,
        nodes: dict[str, CFGNode],
        edges: list[CFGEdge],
    ) -> list[str]:
        cond_id = self._next_node_id("cond")
        cond_node = CFGNode(
            node_id=cond_id,
            kind=CFGNodeKind.CONDITION,
            ast_node_ids=[if_node.id],
            label="if condition",
            source_range=if_node.range,
        )
        nodes[cond_id] = cond_node

        for inc in incoming_ids:
            edges.append(CFGEdge(source_id=inc, target_id=cond_id, edge_type=CFGEdgeType.UNCONDITIONAL))

        children = if_node.children
        then_stmt = children[1] if len(children) > 1 else None
        else_stmt = children[2] if len(children) > 2 else None

        then_outs: list[str] = []
        if then_stmt:
            then_branch_ids = [cond_id]
            then_outs = self._process_statement(
                stmt=then_stmt,
                incoming_ids=then_branch_ids,
                exit_id=exit_id,
                nodes=nodes,
                edges=edges,
            )
            # Re-label the first edge created from cond_id to then branch if any
            for i, e in enumerate(edges):
                if e.source_id == cond_id and e.edge_type == CFGEdgeType.UNCONDITIONAL:
                    edges[i] = CFGEdge(
                        source_id=e.source_id,
                        target_id=e.target_id,
                        edge_type=CFGEdgeType.TRUE_BRANCH,
                        label="true",
                    )

        else_outs: list[str] = []
        if else_stmt:
            else_branch_ids = [cond_id]
            else_outs = self._process_statement(
                stmt=else_stmt,
                incoming_ids=else_branch_ids,
                exit_id=exit_id,
                nodes=nodes,
                edges=edges,
            )
            for i, e in enumerate(edges):
                if e.source_id == cond_id and e.edge_type == CFGEdgeType.UNCONDITIONAL:
                    edges[i] = CFGEdge(
                        source_id=e.source_id,
                        target_id=e.target_id,
                        edge_type=CFGEdgeType.FALSE_BRANCH,
                        label="false",
                    )
        else:
            else_outs = [cond_id]

        return list(set(then_outs + else_outs))

    def _process_loop_stmt(
        self,
        loop_node: ASTNode,
        incoming_ids: list[str],
        exit_id: str,
        nodes: dict[str, CFGNode],
        edges: list[CFGEdge],
    ) -> list[str]:
        header_id = self._next_node_id("loop_header")
        header_node = CFGNode(
            node_id=header_id,
            kind=CFGNodeKind.LOOP_HEADER,
            ast_node_ids=[loop_node.id],
            label=f"{loop_node.kind} header",
            source_range=loop_node.range,
        )
        nodes[header_id] = header_node

        for inc in incoming_ids:
            edges.append(CFGEdge(source_id=inc, target_id=header_id, edge_type=CFGEdgeType.UNCONDITIONAL))

        body_stmt = loop_node.children[-1] if loop_node.children else None
        if body_stmt:
            body_outs = self._process_statement(
                stmt=body_stmt,
                incoming_ids=[header_id],
                exit_id=exit_id,
                nodes=nodes,
                edges=edges,
            )
            for i, e in enumerate(edges):
                if e.source_id == header_id and e.edge_type == CFGEdgeType.UNCONDITIONAL:
                    edges[i] = CFGEdge(
                        source_id=e.source_id,
                        target_id=e.target_id,
                        edge_type=CFGEdgeType.LOOP_BODY,
                        label="loop_body",
                    )
            for b_out in body_outs:
                edges.append(CFGEdge(source_id=b_out, target_id=header_id, edge_type=CFGEdgeType.LOOP_BACK, label="backedge"))

        return [header_id]


def build_cfgs_for_ast(root: ASTNode) -> dict[str, ControlFlowGraph]:
    """Helper function to extract CFGs for all function declarations in an AST."""
    func_nodes = find_nodes_by_kind(
        root,
        ["FUNCTION_DECL", "CXX_METHOD", "CONSTRUCTOR", "DESTRUCTOR"],
    )
    builder = CFGBuilder()
    cfgs: dict[str, ControlFlowGraph] = {}

    for f_node in func_nodes:
        name = f_node.spelling or f_node.display_name
        if not name or not f_node.children:
            continue
        try:
            cfg = builder.build_for_function(f_node)
            cfgs[name] = cfg
        except CFGError:
            continue

    return cfgs
