"""
Vyom AST-based formatter.

Implements visitor pattern to normalize Vyom code structure and formatting.
"""

from typing import Any, List, Optional
from ..ast_nodes import *
from .rules import FormattingRules
from .printer import Printer


class VyomFormatter:
    """AST visitor that formats Vyom code according to defined rules."""
    
    def __init__(self, rules: Optional[FormattingRules] = None):
        self.rules = rules or FormattingRules()
        self.printer = Printer(self.rules)
    
    def format_node(self, node: Any) -> str:
        """Format a single AST node."""
        self.printer.reset()
        self._visit(node)
        return self.printer.get_formatted_text()
    
    def format_statements(self, statements: List[Stmt]) -> str:
        """Format a list of statements."""
        self.printer.reset()
        for stmt in statements:
            self._visit(stmt)
        return self.printer.get_formatted_text()
    
    def _visit(self, node: Any) -> None:
        """Dispatch to appropriate visitor method."""
        method_name = f"_visit_{type(node).__name__}"
        visitor = getattr(self, method_name, self._visit_default)
        visitor(node)
    
    def _visit_default(self, node: Any) -> None:
        """Default visitor for unhandled node types."""
        self.printer.write(f"<{type(node).__name__}>")
    
    # ==================== Expression Visitors ====================
    
    def _visit_Literal(self, node: Literal) -> None:
        """Format literal values."""
        if isinstance(node.value, str):
            self.printer.write(f'"{node.value}"')
        elif node.value is None:
            self.printer.write("null")
        elif node.value is True:
            self.printer.write("true")
        elif node.value is False:
            self.printer.write("false")
        else:
            self.printer.write(str(node.value))
    
    def _visit_Variable(self, node: Variable) -> None:
        """Format variable names."""
        self.printer.write(node.name)
    
    def _visit_Binary(self, node: Binary) -> None:
        """Format binary operations."""
        self._visit(node.left)
        self.printer.write_operator(node.op)
        self._visit(node.right)
    
    def _visit_Unary(self, node: Unary) -> None:
        """Format unary operations."""
        if node.op in self.rules.unary_operators:
            self.printer.write(node.op)
        else:
            self.printer.write_operator(node.op)
        self._visit(node.operand)
    
    def _visit_Grouping(self, node: Grouping) -> None:
        """Format grouped expressions."""
        self.printer.write_parenthesized(lambda: self._visit(node.expression))
    
    def _visit_ListLiteral(self, node: ListLiteral) -> None:
        """Format list literals."""
        self.printer.write_bracketed(lambda: self._format_sequence(node.elements))
    
    def _visit_TupleLiteral(self, node: TupleLiteral) -> None:
        """Format tuple literals."""
        self.printer.write("(")
        self._format_sequence(node.elements)
        self.printer.write(")")
    
    def _visit_DictLiteral(self, node: DictLiteral) -> None:
        """Format dictionary literals."""
        if not node.entries:
            self.printer.write("{}")
            return
        
        self.printer.write("{")
        self.printer.space()
        
        for i, (key, value) in enumerate(node.entries):
            if isinstance(key, str):
                self.printer.write(f'"{key}"')
            else:
                self._visit(key)
            self.printer.write(":")
            self.printer.space()
            self._visit(value)
            
            if i < len(node.entries) - 1:
                self.printer.write_comma()
        
        self.printer.space()
        self.printer.write("}")
    
    def _visit_SetLiteral(self, node: SetLiteral) -> None:
        """Format set literals."""
        self.printer.write("set")
        self.printer.write_bracketed(lambda: self._format_sequence(node.elements))
    
    def _visit_ArrayLiteral(self, node: ArrayLiteral) -> None:
        """Format array literals."""
        self.printer.write("array")
        self.printer.write_bracketed(lambda: self._visit(node.size_expr))
    
    def _visit_Subscript(self, node: Subscript) -> None:
        """Format subscript access."""
        self._visit(node.base)
        self.printer.write_bracketed(lambda: self._visit(node.index))
    
    def _visit_Call(self, node: Call) -> None:
        """Format function calls."""
        self._visit(node.callee)
        self.printer.write_parenthesized(lambda: self._format_sequence(node.arguments))
    
    def _visit_Member(self, node: Member) -> None:
        """Format member access."""
        self._visit(node.base)
        self.printer.write(".")
        self.printer.write(node.name)
    
    def _visit_FunctionExpr(self, node: FunctionExpr) -> None:
        """Format function expressions."""
        self.printer.write("function")
        if node.name:
            self.printer.space()
            self.printer.write(node.name)
        
        self.printer.write_parenthesized(lambda: self._format_params(node.params, node.param_types))
        
        if node.return_type:
            self.printer.space()
            self.printer.write(":")
            self.printer.space()
            self.printer.write(node.return_type.name)
        
        self.printer.write_block(lambda: self._visit(node.body), same_line_open=True)
    
    def _visit_Assign(self, node: Assign) -> None:
        """Format assignment expressions."""
        self._visit(node.target)
        self.printer.space()
        self.printer.write("=")
        self.printer.space()
        self._visit(node.value)
    
    def _visit_MatchExpr(self, node: MatchExpr) -> None:
        """Format match expressions."""
        self.printer.write("match")
        self.printer.space()
        self._visit(node.value)
        self.printer.space()
        self.printer.write("{")
        self.printer.newline()
        
        self.printer.indent()
        for i, arm in enumerate(node.arms):
            self._visit_case_arm(arm)
            if i < len(node.arms) - 1:
                self.printer.write(";")
                self.printer.newline()
        self.printer.dedent()
        
        self.printer.newline()
        self.printer.write("}")
    
    # ==================== Statement Visitors ====================
    
    def _visit_ExprStmt(self, node: ExprStmt) -> None:
        """Format expression statements."""
        self._visit(node.expr)
        self.printer.newline()
    
    def _visit_PrintStmt(self, node: PrintStmt) -> None:
        """Format print statements."""
        self.printer.write("show")
        self.printer.write_parenthesized(lambda: self._visit(node.expr))
        self.printer.newline()
    
    def _visit_BlockStmt(self, node: BlockStmt) -> None:
        """Format block statements."""
        for stmt in node.body:
            self._visit(stmt)
    
    def _visit_IfStmt(self, node: IfStmt) -> None:
        """Format if statements."""
        self.printer.write("if")
        self.printer.space()
        self.printer.write_parenthesized(lambda: self._visit(node.condition))
        self.printer.write_block(lambda: self._visit(node.then_branch), same_line_open=True)
        
        if node.else_branch:
            if self.rules.else_on_newline:
                self.printer.write("else")
                self.printer.space()
                if isinstance(node.else_branch, BlockStmt):
                    self.printer.write_block(lambda: self._visit(node.else_branch), same_line_open=True)
                else:
                    self._visit(node.else_branch)
            else:
                self.printer.write(" else ")
                self._visit(node.else_branch)
    
    def _visit_WhileStmt(self, node: WhileStmt) -> None:
        """Format while statements."""
        self.printer.write("while")
        self.printer.space()
        self.printer.write_parenthesized(lambda: self._visit(node.condition))
        self.printer.write_block(lambda: self._visit(node.body), same_line_open=True)
    
    def _visit_ForStmt(self, node: ForStmt) -> None:
        """Format for statements."""
        self.printer.write("for")
        self.printer.space()
        self.printer.write(f"var {node.name} := ")
        self._visit(node.start)
        self.printer.space()
        self.printer.write("to")
        self.printer.space()
        self._visit(node.end)
        
        if node.step:
            self.printer.space()
            self.printer.write("step")
            self.printer.space()
            self._visit(node.step)
        
        self.printer.write_block(lambda: self._visit(node.body), same_line_open=True)
    
    def _visit_LoopStmt(self, node: LoopStmt) -> None:
        """Format infinite loop statements."""
        self.printer.write("loop")
        self.printer.write_block(lambda: self._visit(node.body), same_line_open=True)
    
    def _visit_BreakStmt(self, node: BreakStmt) -> None:
        """Format break statements."""
        self.printer.write("break")
        self.printer.newline()
    
    def _visit_FunctionStmt(self, node: FunctionStmt) -> None:
        """Format function statements."""
        self.printer.write("function")
        self.printer.space()
        self.printer.write(node.name)
        self.printer.write_parenthesized(lambda: self._format_params(node.params, node.param_types))
        
        if node.return_type:
            self.printer.space()
            self.printer.write(":")
            self.printer.space()
            self.printer.write(node.return_type.name)
        
        self.printer.write_block(lambda: self._visit(node.body), same_line_open=True)
    
    def _visit_ReturnStmt(self, node: ReturnStmt) -> None:
        """Format return statements."""
        self.printer.write("return")
        if node.value:
            self.printer.space()
            self._visit(node.value)
        self.printer.newline()
    
    def _visit_ThrowStmt(self, node: ThrowStmt) -> None:
        """Format throw statements."""
        self.printer.write("throw")
        self.printer.space()
        self._visit(node.value)
        self.printer.newline()
    
    def _visit_TryCatchStmt(self, node: TryCatchStmt) -> None:
        """Format try-catch statements."""
        self.printer.write("try")
        self.printer.write_block(lambda: self._visit(node.try_block), same_line_open=True)
        self.printer.write("catch")
        self.printer.space()
        self.printer.write(f"({node.catch_name})")
        self.printer.write_block(lambda: self._visit(node.catch_block), same_line_open=True)
    
    def _visit_LetBlockStmt(self, node: LetBlockStmt) -> None:
        """Format let/var/const statements."""
        if node.is_const:
            keyword = "const"
        elif node.is_var:
            keyword = "var"
        else:
            keyword = "let"
        
        self.printer.write(keyword)
        self.printer.space()
        self.printer.write(node.name)
        
        if node.type_ann:
            self.printer.write(":")
            self.printer.space()
            self.printer.write(node.type_ann.name)
        
        if node.initializer:
            self.printer.space()
            self.printer.write(":=" if keyword in ["let", "var"] else "=")
            self.printer.space()
            self._visit(node.initializer)
        
        if node.block:
            self.printer.write_block(lambda: self._visit(node.block), same_line_open=True)
        else:
            self.printer.newline()
    
    def _visit_MatchStmt(self, node: MatchStmt) -> None:
        """Format match statements."""
        self.printer.write("match")
        self.printer.space()
        self._visit(node.value)
        self.printer.space()
        self.printer.write("{")
        self.printer.newline()
        
        self.printer.indent()
        for i, arm in enumerate(node.arms):
            self._visit_case_arm(arm, is_statement=True)
            if i < len(node.arms) - 1:
                self.printer.newline()
        self.printer.dedent()
        
        self.printer.newline()
        self.printer.write("}")
    
    # ==================== Pattern Visitors ====================
    
    def _visit_case_arm(self, arm: CaseArm, is_statement: bool = False) -> None:
        """Format case arms for pattern matching."""
        self.printer.write("case")
        self.printer.space()
        self._visit_pattern(arm.pattern)
        
        if arm.guard:
            self.printer.space()
            self.printer.write("if")
            self.printer.space()
            self._visit(arm.guard)
        
        if is_statement:
            self.printer.write_block(lambda: self._visit(arm.body), same_line_open=True)
        else:
            self.printer.write(":")
            self.printer.space()
            self._visit(arm.body)
    
    def _visit_pattern(self, pattern: Pattern) -> None:
        """Format pattern nodes."""
        method_name = f"_visit_{type(pattern).__name__}"
        visitor = getattr(self, method_name, self._visit_default)
        visitor(pattern)
    
    def _visit_LiteralPattern(self, pattern: LiteralPattern) -> None:
        """Format literal patterns."""
        self._visit_Literal(Literal(pattern.value))
    
    def _visit_VariablePattern(self, pattern: VariablePattern) -> None:
        """Format variable patterns."""
        self.printer.write(pattern.name)
    
    def _visit_TypePattern(self, pattern: TypePattern) -> None:
        """Format type patterns."""
        self._visit(pattern.type_expr)
    
    def _visit_ListPattern(self, pattern: ListPattern) -> None:
        """Format list patterns."""
        self.printer.write_bracketed(lambda: self._format_pattern_sequence(pattern.elements))
    
    def _visit_TuplePattern(self, pattern: TuplePattern) -> None:
        """Format tuple patterns."""
        self.printer.write("(")
        self._format_pattern_sequence(pattern.elements)
        self.printer.write(")")
    
    def _visit_DictPattern(self, pattern: DictPattern) -> None:
        """Format dictionary patterns."""
        if not pattern.entries:
            self.printer.write("{}")
            return
        
        self.printer.write("{")
        self.printer.space()
        
        for i, (key, value_pattern) in enumerate(pattern.entries):
            self.printer.write(f'"{key}"')
            self.printer.write(":")
            self.printer.space()
            self._visit_pattern(value_pattern)
            
            if i < len(pattern.entries) - 1:
                self.printer.write_comma()
        
        self.printer.space()
        self.printer.write("}")
    
    def _visit_OrPattern(self, pattern: OrPattern) -> None:
        """Format OR patterns."""
        for i, subpattern in enumerate(pattern.patterns):
            self._visit_pattern(subpattern)
            if i < len(pattern.patterns) - 1:
                self.printer.space()
                self.printer.write("|")
                self.printer.space()
    
    def _visit_WildcardPattern(self, pattern: WildcardPattern) -> None:
        """Format wildcard patterns."""
        self.printer.write("_")
    
    # ==================== Helper Methods ====================
    
    def _format_sequence(self, elements: List[Expr]) -> None:
        """Format a sequence of expressions."""
        for i, element in enumerate(elements):
            self._visit(element)
            if i < len(elements) - 1:
                self.printer.write_comma()
    
    def _format_pattern_sequence(self, patterns: List[Pattern]) -> None:
        """Format a sequence of patterns."""
        for i, pattern in enumerate(patterns):
            self._visit_pattern(pattern)
            if i < len(patterns) - 1:
                self.printer.write_comma()
    
    def _format_params(self, params: List[str], param_types: dict) -> None:
        """Format function parameters with optional type annotations."""
        for i, param in enumerate(params):
            self.printer.write(param)
            if param in param_types:
                self.printer.write(":")
                self.printer.space()
                self.printer.write(param_types[param].name)
            if i < len(params) - 1:
                self.printer.write_comma()
