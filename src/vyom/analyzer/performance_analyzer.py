"""Performance analysis for Vyom programs."""

from typing import List, Dict, Any, Optional
from ..ast_nodes import *


class PerformanceAnalyzer:
    """Analyzes code for performance issues and optimizations."""
    
    def __init__(self):
        self.issues: List[Dict[str, Any]] = []
        self.loop_depth = 0
        self.function_calls: Dict[str, int] = {}
        self.variable_usage: Dict[str, List[Dict[str, Any]]] = {}
        
    def analyze(self, ast: List[Stmt]) -> List[Dict[str, Any]]:
        """Analyze AST for performance issues."""
        self.issues = []
        self.loop_depth = 0
        self.function_calls = {}
        self.variable_usage = {}
        
        for stmt in ast:
            self._analyze_statement(stmt)
        
        # Post-analysis checks
        self._analyze_function_call_frequency()
        self._analyze_variable_usage_patterns()
        
        return self.issues
    
    def _analyze_statement(self, stmt: Stmt) -> None:
        """Analyze a single statement."""
        if isinstance(stmt, ExprStmt):
            self._analyze_expression_statement(stmt)
        elif isinstance(stmt, LetStmt):
            self._analyze_variable_declaration(stmt)
        elif isinstance(stmt, FunctionStmt):
            self._analyze_function_declaration(stmt)
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
    
    def _analyze_expression_statement(self, stmt: ExprStmt) -> None:
        """Analyze expression statement."""
        if isinstance(stmt.expr, Call):
            self._analyze_function_call(stmt.expr)
        elif isinstance(stmt.expr, Binary):
            self._analyze_binary_expression(stmt.expr)
        elif isinstance(stmt.expr, ListLiteral):
            self._analyze_list_expression(stmt.expr)
        elif isinstance(stmt.expr, DictLiteral):
            self._analyze_dict_expression(stmt.expr)
    
    def _analyze_function_call(self, expr: Call) -> None:
        """Analyze function call for performance issues."""
        func_name = self._get_function_name(expr.callee)
        
        # Track function call frequency
        self.function_calls[func_name] = self.function_calls.get(func_name, 0) + 1
        
        # Check for expensive operations in loops
        if self.loop_depth > 0:
            if self._is_expensive_function(func_name):
                self._add_performance_issue(
                    'medium',
                    expr.callee.line if hasattr(expr.callee, 'line') else 0,
                    f"Expensive function '{func_name}' called inside loop (depth {self.loop_depth})"
                )
        
        # Check for function call with many arguments
        if len(expr.arguments) > 5:
            self._add_performance_issue(
                'low',
                expr.callee.line if hasattr(expr.callee, 'line') else 0,
                f"Function '{func_name}' called with {len(expr.arguments)} arguments - consider refactoring"
            )
        
        # Analyze arguments
        for arg in expr.arguments:
            self._analyze_expression(arg)
    
    def _analyze_binary_expression(self, expr: Binary) -> None:
        """Analyze binary expression for performance issues."""
        # Check for string concatenation in loops
        op = expr.op if isinstance(expr.op, str) else expr.op.lexeme
        if op == '+' and self.loop_depth > 0:
            if self._is_string_expression(expr.left) or self._is_string_expression(expr.right):
                op_line = expr.op.line if hasattr(expr.op, 'line') else 0
                self._add_performance_issue(
                    'medium',
                    op_line,
                    "String concatenation in loop - consider using string builder"
                )
        
        # Analyze sub-expressions
        self._analyze_expression(expr.left)
        self._analyze_expression(expr.right)
    
    def _analyze_list_expression(self, expr: ListExpr) -> None:
        """Analyze list expression for performance issues."""
        # Check for large list literals
        if len(expr.elements) > 100:
            if hasattr(expr, 'token'):
                line = expr.token.line
            else:
                line = 0
            self._add_performance_issue(
                'low',
                line,
                f"Large list literal with {len(expr.elements)} elements - consider loading from data source"
            )
    
    def _analyze_dict_expression(self, expr: DictExpr) -> None:
        """Analyze dictionary expression for performance issues."""
        # Check for large dictionary literals
        if len(expr.entries) > 50:
            if hasattr(expr, 'token'):
                line = expr.token.line
            else:
                line = 0
            self._add_performance_issue(
                'low',
                line,
                f"Large dictionary literal with {len(expr.entries)} entries - consider loading from data source"
            )
    
    def _analyze_variable_declaration(self, stmt: LetStmt) -> None:
        """Analyze variable declaration for performance issues."""
        var_name = stmt.name
        
        # Track variable usage
        self.variable_usage[var_name] = self.variable_usage.get(var_name, [])
        self.variable_usage[var_name].append({
            'line': stmt.token.line if hasattr(stmt, 'token') else 0,
            'type': 'declaration',
            'in_loop': self.loop_depth > 0
        })
        
        # Check for variable declarations in loops
        if self.loop_depth > 0 and not stmt.is_const:
            if hasattr(stmt, 'token'):
                line = stmt.token.line
            else:
                line = 0
            self._add_performance_issue(
                'low',
                line,
                f"Variable '{var_name}' declared inside loop - consider moving outside"
            )
        
        # Analyze initializer
        if stmt.initializer:
            self._analyze_expression(stmt.initializer)
    
    def _analyze_function_declaration(self, stmt: FunctionStmt) -> None:
        """Analyze function declaration for performance issues."""
        # Check for very long functions
        if len(stmt.body.body) > 50:
            if hasattr(stmt, 'token'):
                line = stmt.token.line
            else:
                line = 0
            self._add_performance_issue(
                'medium',
                line,
                f"Function '{stmt.name}' is very long ({len(stmt.body.body)} lines) - consider breaking up"
            )
        
        # Check for functions with many parameters
        if len(stmt.params) > 8:
            if hasattr(stmt, 'token'):
                line = stmt.token.line
            else:
                line = 0
            self._add_performance_issue(
                'low',
                line,
                f"Function '{stmt.name}' has {len(stmt.params)} parameters - consider using a struct/object"
            )
        
        # Analyze function body
        for body_stmt in stmt.body.body:
            self._analyze_statement(body_stmt)
    
    def _analyze_if_statement(self, stmt: IfStmt) -> None:
        """Analyze if statement for performance issues."""
        # Check for deeply nested if statements
        if self._calculate_if_depth(stmt) > 3:
            if hasattr(stmt, 'token'):
                line = stmt.token.line
            else:
                line = 0
            self._add_performance_issue(
                'low',
                line,
                f"Deeply nested if statements (depth {self._calculate_if_depth(stmt)}) - consider refactoring"
            )
        
        # Analyze branches
        for then_stmt in stmt.then_branch.body:
            self._analyze_statement(then_stmt)
        
        if stmt.else_branch:
            for else_stmt in stmt.else_branch.body:
                self._analyze_statement(else_stmt)
    
    def _analyze_while_statement(self, stmt: WhileStmt) -> None:
        """Analyze while statement for performance issues."""
        self.loop_depth += 1
        
        # Check for potential infinite loops
        if self._is_constant_true(stmt.condition):
            if hasattr(stmt, 'token'):
                line = stmt.token.line
            else:
                line = 0
            self._add_performance_issue(
                'high',
                line,
                "While loop with constant true condition - ensure proper break condition"
            )
        
        # Analyze loop body
        for body_stmt in stmt.body.body:
            self._analyze_statement(body_stmt)
        
        self.loop_depth -= 1
    
    def _analyze_for_statement(self, stmt: ForStmt) -> None:
        """Analyze for statement for performance issues."""
        self.loop_depth += 1
        
        # Check for large loop ranges
        if hasattr(stmt, 'range_end') and isinstance(stmt.range_end, Literal):
            if hasattr(stmt.range_end, 'value') and isinstance(stmt.range_end.value, int):
                if stmt.range_end.value > 100000:
                    if hasattr(stmt, 'token'):
                        line = stmt.token.line
                    else:
                        line = 0
                    self._add_performance_issue(
                        'medium',
                        line,
                        f"Large loop range (up to {stmt.range_end.value}) - consider optimization"
                    )
        
        # Analyze loop body
        for body_stmt in stmt.body.body:
            self._analyze_statement(body_stmt)
        
        self.loop_depth -= 1
    
    def _analyze_match_statement(self, stmt: MatchStmt) -> None:
        """Analyze match statement for performance issues."""
        # Check for match statements with many cases
        if len(stmt.arms) > 20:
            if hasattr(stmt, 'token'):
                line = stmt.token.line
            else:
                line = 0
            self._add_performance_issue(
                'low',
                line,
                f"Match statement with {len(stmt.arms)} cases - consider using a dictionary lookup"
            )
        
        # Analyze match arms
        for arm in stmt.arms:
            for arm_stmt in arm.body.body:
                self._analyze_statement(arm_stmt)
    
    def _analyze_expression(self, expr) -> None:
        """Analyze generic expression."""
        if isinstance(expr, Call):
            self._analyze_function_call(expr)
        elif isinstance(expr, Binary):
            self._analyze_binary_expression(expr)
        elif isinstance(expr, ListLiteral):
            self._analyze_list_expression(expr)
        elif isinstance(expr, DictLiteral):
            self._analyze_dict_expression(expr)
    
    def _analyze_function_call_frequency(self) -> None:
        """Analyze function call frequency for optimization opportunities."""
        for func_name, count in self.function_calls.items():
            if count > 100:
                self._add_performance_issue(
                    'low',
                    0,  # Global issue
                    f"Function '{func_name}' called {count} times - consider caching or optimization"
                )
    
    def _analyze_variable_usage_patterns(self) -> None:
        """Analyze variable usage patterns."""
        for var_name, usages in self.variable_usage.items():
            # Check for variables used only once
            if len(usages) == 1 and usages[0]['type'] == 'declaration':
                self._add_performance_issue(
                    'low',
                    usages[0]['line'],
                    f"Variable '{var_name}' declared but never used"
                )
    
    def _get_function_name(self, callee) -> str:
        """Extract function name from callee expression."""
        if hasattr(callee, 'lexeme'):
            return callee.lexeme
        elif hasattr(callee, 'name'):
            return callee.name
        else:
            return str(callee)
    
    def _is_expensive_function(self, func_name: str) -> bool:
        """Check if function is computationally expensive."""
        expensive_functions = [
            'sort', 'search', 'filter', 'map', 'reduce',
            'regex', 'parse', 'compile', 'evaluate',
            'database', 'network', 'file', 'io'
        ]
        return any(pattern in func_name.lower() for pattern in expensive_functions)
    
    def _is_string_expression(self, expr) -> bool:
        """Check if expression is a string."""
        return hasattr(expr, 'value') and isinstance(expr.value, str)
    
    def _calculate_if_depth(self, stmt: IfStmt, current_depth: int = 0) -> int:
        """Calculate maximum if nesting depth."""
        max_depth = current_depth
        
        for then_stmt in stmt.then_branch.body:
            if isinstance(then_stmt, IfStmt):
                max_depth = max(max_depth, self._calculate_if_depth(then_stmt, current_depth + 1))
        
        if stmt.else_branch:
            for else_stmt in stmt.else_branch.body:
                if isinstance(else_stmt, IfStmt):
                    max_depth = max(max_depth, self._calculate_if_depth(else_stmt, current_depth + 1))
        
        return max_depth
    
    def _is_constant_true(self, expr) -> bool:
        """Check if expression is constantly true."""
        return hasattr(expr, 'lexeme') and expr.lexeme == 'true'
    
    def _add_performance_issue(self, severity: str, line: int, message: str) -> None:
        """Add a performance issue."""
        self.issues.append({
            'severity': severity,
            'line': line,
            'message': message,
            'type': 'performance'
        })


def analyze_performance(ast: List[Stmt]) -> List[Dict[str, Any]]:
    """Convenience function to analyze performance."""
    analyzer = PerformanceAnalyzer()
    return analyzer.analyze(ast)
