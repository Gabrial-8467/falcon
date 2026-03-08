"""Code complexity analysis for Vyom programs."""

from typing import List, Dict, Any, Optional
from ..ast_nodes import *


class ComplexityAnalyzer:
    """Analyzes code complexity metrics."""
    
    def __init__(self):
        self.complexity_score = 0
        self.function_complexities: Dict[str, Dict[str, Any]] = {}
        self.nesting_level = 0
        self.current_function = None
        
    def analyze(self, ast: List[Stmt]) -> Dict[str, Any]:
        """Analyze AST for complexity metrics."""
        self.complexity_score = 0
        self.function_complexities = {}
        self.nesting_level = 0
        self.current_function = None
        
        for stmt in ast:
            self._analyze_statement(stmt)
        
        return {
            'total_complexity': self.complexity_score,
            'function_complexities': self.function_complexities,
            'average_complexity': len(self.function_complexities) > 0 and 
                               self.complexity_score / len(self.function_complexities) or 0
        }
    
    def _analyze_statement(self, stmt: Stmt) -> None:
        """Analyze a single statement."""
        if isinstance(stmt, FunctionStmt):
            self._analyze_function(stmt)
        elif isinstance(stmt, IfStmt):
            self._analyze_if_statement(stmt)
        elif isinstance(stmt, WhileStmt):
            self._analyze_while_statement(stmt)
        elif isinstance(stmt, ForStmt):
            self._analyze_for_statement(stmt)
        elif isinstance(stmt, MatchStmt):
            self._analyze_match_statement(stmt)
        elif isinstance(stmt, BlockStmt):
            self.nesting_level += 1
            for block_stmt in stmt.body:
                self._analyze_statement(block_stmt)
            self.nesting_level -= 1
    
    def _analyze_function(self, stmt: FunctionStmt) -> None:
        """Analyze function complexity."""
        old_function = self.current_function
        old_nesting = self.nesting_level
        
        self.current_function = stmt.name
        self.nesting_level = 0
        
        function_complexity = 1  # Base complexity for function
        
        for body_stmt in stmt.body.body:
            function_complexity += self._get_statement_complexity(body_stmt)
            self._analyze_statement(body_stmt)
        
        self.function_complexities[stmt.name] = {
            'complexity': function_complexity,
            'lines': len(stmt.body.body),
            'parameters': len(stmt.params),
            'nesting_depth': self._calculate_max_nesting(stmt.body)
        }
        
        self.complexity_score += function_complexity
        
        self.current_function = old_function
        self.nesting_level = old_nesting
    
    def _analyze_if_statement(self, stmt: IfStmt) -> None:
        """Analyze if statement complexity."""
        self.complexity_score += 1  # +1 for if
        
        # Analyze then branch
        self.nesting_level += 1
        for then_stmt in stmt.then_branch.body:
            self._analyze_statement(then_stmt)
        self.nesting_level -= 1
        
        # Analyze else branch
        if stmt.else_branch:
            self.complexity_score += 1  # +1 for else
            self.nesting_level += 1
            for else_stmt in stmt.else_branch.body:
                self._analyze_statement(else_stmt)
            self.nesting_level -= 1
    
    def _analyze_while_statement(self, stmt: WhileStmt) -> None:
        """Analyze while statement complexity."""
        self.complexity_score += 1  # +1 for while
        
        self.nesting_level += 1
        for body_stmt in stmt.body.body:
            self._analyze_statement(body_stmt)
        self.nesting_level -= 1
    
    def _analyze_for_statement(self, stmt: ForStmt) -> None:
        """Analyze for statement complexity."""
        self.complexity_score += 1  # +1 for for
        
        self.nesting_level += 1
        for body_stmt in stmt.body.body:
            self._analyze_statement(body_stmt)
        self.nesting_level -= 1
    
    def _analyze_match_statement(self, stmt: MatchStmt) -> None:
        """Analyze match statement complexity."""
        # +1 for match, +1 for each case after the first
        self.complexity_score += 1 + max(0, len(stmt.arms) - 1)
        
        self.nesting_level += 1
        for arm in stmt.arms:
            for arm_stmt in arm.body.body:
                self._analyze_statement(arm_stmt)
        self.nesting_level -= 1
    
    def _get_statement_complexity(self, stmt: Stmt) -> int:
        """Get complexity contribution of a statement."""
        if isinstance(stmt, IfStmt):
            return 1 + (1 if stmt.else_branch else 0)
        elif isinstance(stmt, WhileStmt):
            return 1
        elif isinstance(stmt, ForStmt):
            return 1
        elif isinstance(stmt, MatchStmt):
            return 1 + max(0, len(stmt.arms) - 1)
        elif isinstance(stmt, BlockStmt):
            return sum(self._get_statement_complexity(s) for s in stmt.body)
        else:
            return 0
    
    def _calculate_max_nesting(self, block: BlockStmt, current_depth: int = 0) -> int:
        """Calculate maximum nesting depth in a block."""
        max_depth = current_depth
        
        for stmt in block.body:
            if isinstance(stmt, IfStmt):
                max_depth = max(max_depth, current_depth + 1)
                if stmt.else_branch:
                    max_depth = max(max_depth, self._calculate_max_nesting(stmt.else_branch, current_depth + 1))
            elif isinstance(stmt, WhileStmt) or isinstance(stmt, ForStmt):
                max_depth = max(max_depth, current_depth + 1)
            elif isinstance(stmt, MatchStmt):
                max_depth = max(max_depth, current_depth + 1)
            elif isinstance(stmt, BlockStmt):
                max_depth = max(max_depth, self._calculate_max_nesting(stmt, current_depth))
        
        return max_depth


def analyze_complexity(ast: List[Stmt]) -> Dict[str, Any]:
    """Convenience function to analyze code complexity."""
    analyzer = ComplexityAnalyzer()
    return analyzer.analyze(ast)
