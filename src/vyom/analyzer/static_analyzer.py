"""Static analysis for Vyom code quality and best practices."""

from typing import List, Dict, Any, Optional
from ..ast_nodes import *
from ..lexer import Token


class StaticAnalyzer:
    """Analyzes Vyom code for quality issues and best practices."""
    
    def __init__(self):
        self.issues: List[Dict[str, Any]] = []
        self.variables: Dict[str, Dict[str, Any]] = {}
        self.functions: Dict[str, Dict[str, Any]] = {}
        
    def analyze(self, ast: List[Stmt]) -> List[Dict[str, Any]]:
        """Analyze AST for static issues."""
        self.issues = []
        self.variables = {}
        self.functions = {}
        
        for stmt in ast:
            self._analyze_statement(stmt)
        
        return self.issues
    
    def _analyze_statement(self, stmt: Stmt) -> None:
        """Analyze a single statement."""
        if isinstance(stmt, LetStmt):
            self._analyze_variable_declaration(stmt)
        elif isinstance(stmt, FunctionStmt):
            self._analyze_function_declaration(stmt)
        elif isinstance(stmt, ExprStmt):
            self._analyze_expression_statement(stmt)
        elif isinstance(stmt, IfStmt):
            self._analyze_if_statement(stmt)
        elif isinstance(stmt, WhileStmt):
            self._analyze_while_statement(stmt)
        elif isinstance(stmt, ForStmt):
            self._analyze_for_statement(stmt)
        elif isinstance(stmt, MatchStmt):
            self._analyze_match_statement(stmt)
        elif isinstance(stmt, BlockStmt):
            for block_stmt in stmt.body:
                self._analyze_statement(block_stmt)
    
    def _analyze_variable_declaration(self, stmt: LetStmt) -> None:
        """Analyze variable declaration."""
        var_name = stmt.name
        
        # Check for unused variables
        self.variables[var_name] = {
            'used': False,
            'line': stmt.token.line if hasattr(stmt, 'token') else 0,
            'is_const': stmt.is_const,
            'has_type': stmt.type_ann is not None
        }
        
        # Check for const without initialization
        if stmt.is_const and stmt.initializer is None:
            self._add_issue(
                'warning',
                stmt.token.line if hasattr(stmt, 'token') else 0,
                f"Constant '{var_name}' declared without initialization"
            )
        
        # Check variable naming conventions
        if not self._is_valid_variable_name(var_name):
            self._add_issue(
                'info',
                stmt.token.line if hasattr(stmt, 'token') else 0,
                f"Variable '{var_name}' should follow snake_case naming convention"
            )
    
    def _analyze_function_declaration(self, stmt: FunctionStmt) -> None:
        """Analyze function declaration."""
        func_name = stmt.name
        
        self.functions[func_name] = {
            'params': stmt.params,
            'line': stmt.token.line if hasattr(stmt, 'token') else 0,
            'has_return_type': stmt.return_type is not None,
            'param_types': stmt.param_types
        }
        
        # Check function naming conventions
        if not self._is_valid_function_name(func_name):
            self._add_issue(
                'info',
                stmt.token.line if hasattr(stmt, 'token') else 0,
                f"Function '{func_name}' should follow snake_case naming convention"
            )
        
        # Check for empty functions
        if len(stmt.body.body) == 0:
            self._add_issue(
                'warning',
                stmt.token.line if hasattr(stmt, 'token') else 0,
                f"Function '{func_name}' has empty body"
            )
        
        # Analyze function body
        for body_stmt in stmt.body.body:
            self._analyze_statement(body_stmt)
    
    def _analyze_expression_statement(self, stmt: ExprStmt) -> None:
        """Analyze expression statement."""
        if isinstance(stmt.expr, Call):
            self._analyze_function_call(stmt.expr)
    
    def _analyze_function_call(self, expr: Call) -> None:
        """Analyze function call."""
        # Check for calls to undefined functions
        func_name = expr.callee.lexeme if hasattr(expr.callee, 'lexeme') else str(expr.callee)
        
        if func_name not in self.functions and func_name not in ['show', 'len', 'type', 'str', 'int', 'bool', 'list', 'dict', 'set', 'array']:
            self._add_issue(
                'warning',
                expr.callee.line if hasattr(expr.callee, 'line') else 0,
                f"Call to undefined function '{func_name}'"
            )
        
        # Check for too many arguments
        if func_name in self.functions:
            expected_params = len(self.functions[func_name]['params'])
            actual_params = len(expr.arguments)
            
            if actual_params != expected_params:
                self._add_issue(
                    'error',
                    expr.callee.line if hasattr(expr.callee, 'line') else 0,
                    f"Function '{func_name}' expects {expected_params} arguments, got {actual_params}"
                )
    
    def _analyze_if_statement(self, stmt: IfStmt) -> None:
        """Analyze if statement."""
        # Check for missing else branch
        if stmt.else_branch is None:
            self._add_issue(
                'info',
                stmt.token.line if hasattr(stmt, 'token') else 0,
                "Consider adding an else branch for comprehensive handling"
            )
        
        # Analyze branches
        for branch_stmt in stmt.then_branch.body:
            self._analyze_statement(branch_stmt)
        
        if stmt.else_branch:
            for else_stmt in stmt.else_branch.body:
                self._analyze_statement(else_stmt)
    
    def _analyze_while_statement(self, stmt: WhileStmt) -> None:
        """Analyze while statement."""
        # Check for potential infinite loops
        if self._is_constant_true(stmt.condition):
            self._add_issue(
                'warning',
                stmt.token.line if hasattr(stmt, 'token') else 0,
                "While loop with constant true condition may cause infinite loop"
            )
        
        # Analyze loop body
        for body_stmt in stmt.body.body:
            self._analyze_statement(body_stmt)
    
    def _analyze_for_statement(self, stmt: ForStmt) -> None:
        """Analyze for statement."""
        # Analyze loop body
        for body_stmt in stmt.body.body:
            self._analyze_statement(body_stmt)
    
    def _analyze_match_statement(self, stmt: MatchStmt) -> None:
        """Analyze match statement."""
        # Check for exhaustive patterns
        if not self._has_wildcard_pattern(stmt.arms):
            self._add_issue(
                'warning',
                stmt.token.line if hasattr(stmt, 'token') else 0,
                "Match statement missing wildcard pattern (case _:)"
            )
        
        # Analyze match arms
        for arm in stmt.arms:
            for arm_stmt in arm.body.body:
                self._analyze_statement(arm_stmt)
    
    def _is_constant_true(self, expr: Expr) -> bool:
        """Check if expression is constantly true."""
        if hasattr(expr, 'lexeme') and expr.lexeme == 'true':
            return True
        return False
    
    def _has_wildcard_pattern(self, arms: List['CaseArm']) -> bool:
        """Check if match has wildcard pattern."""
        for arm in arms:
            if hasattr(arm.pattern, 'lexeme') and arm.pattern.lexeme == '_':
                return True
        return False
    
    def _is_valid_variable_name(self, name: str) -> bool:
        """Check if variable name follows snake_case convention."""
        return name.replace('_', '').isalnum() and name == name.lower()
    
    def _is_valid_function_name(self, name: str) -> bool:
        """Check if function name follows snake_case convention."""
        return name.replace('_', '').isalnum() and name == name.lower()
    
    def _add_issue(self, severity: str, line: int, message: str) -> None:
        """Add an analysis issue."""
        self.issues.append({
            'severity': severity,
            'line': line,
            'message': message,
            'type': 'static_analysis'
        })


def analyze_code(ast: List[Stmt]) -> List[Dict[str, Any]]:
    """Convenience function to analyze code."""
    analyzer = StaticAnalyzer()
    return analyzer.analyze(ast)
