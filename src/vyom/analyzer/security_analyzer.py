"""Security analysis for Vyom programs."""

from typing import List, Dict, Any, Optional
from ..ast_nodes import *
from ..lexer import Token

class SecurityAnalyzer:
    """Analyzes code for security vulnerabilities and issues."""
    
    def __init__(self):
        self.issues: List[Dict[str, Any]] = []
        self.dangerous_functions = [
            'eval', 'exec', 'compile', 'open', 'file', 'input', 'raw_input'
        ]
        self.sensitive_operations = [
            'system', 'subprocess', 'os', 'sys', 'import', 'load'
        ]
        
    def analyze(self, ast: List[Stmt]) -> List[Dict[str, Any]]:
        """Analyze AST for security issues."""
        self.issues = []
        
        for stmt in ast:
            self._analyze_statement(stmt)
        
        return self.issues
    
    def _analyze_statement(self, stmt: Stmt) -> None:
        """Analyze a single statement."""
        if isinstance(stmt, ExprStmt):
            self._analyze_expression_statement(stmt)
        elif isinstance(stmt, LetStmt):
            self._analyze_variable_declaration(stmt)
        elif isinstance(stmt, FunctionStmt):
            self._analyze_function_declaration(stmt)
        elif isinstance(stmt, BlockStmt):
            for block_stmt in stmt.body:
                self._analyze_statement(block_stmt)
    
    def _analyze_expression_statement(self, stmt: ExprStmt) -> None:
        """Analyze expression statement for security issues."""
        if isinstance(stmt.expr, CallExpr):
            self._analyze_function_call(stmt.expr)
        elif isinstance(stmt.expr, BinaryExpr):
            self._analyze_binary_expression(stmt.expr)
    
    def _analyze_function_call(self, expr: CallExpr) -> None:
        """Analyze function call for security issues."""
        func_name = self._get_function_name(expr.callee)
        
        # Check for dangerous functions
        if func_name in self.dangerous_functions:
            self._add_security_issue(
                'high',
                expr.callee.line if hasattr(expr.callee, 'line') else 0,
                f"Use of dangerous function '{func_name}' can lead to code injection"
            )
        
        # Check for sensitive operations
        if func_name in self.sensitive_operations:
            self._add_security_issue(
                'medium',
                expr.callee.line if hasattr(expr.callee, 'line') else 0,
                f"Use of sensitive function '{func_name}' requires careful validation"
            )
        
        # Check for hardcoded secrets in arguments
        for arg in expr.arguments:
            if isinstance(arg, Literal) and hasattr(arg, 'value'):
                if self._looks_like_secret(str(arg.value)):
                    self._add_security_issue(
                        'high',
                        expr.callee.line if hasattr(expr.callee, 'line') else 0,
                        f"Potential hardcoded secret detected in function call"
                    )
    
    def _analyze_binary_expression(self, expr: Binary) -> None:
        """Analyze binary expression for security issues."""
        # Check for string concatenation with user input
        op = expr.op if isinstance(expr.op, str) else expr.op.lexeme
        if op == '+':
            if self._involves_user_input(expr.left) or self._involves_user_input(expr.right):
                op_line = expr.op.line if hasattr(expr.op, 'line') else 0
                self._add_security_issue(
                    'medium',
                    op_line,
                    "String concatenation with potential user input may lead to injection"
                )
    
    def _analyze_variable_declaration(self, stmt: LetStmt) -> None:
        """Analyze variable declaration for security issues."""
        if stmt.initializer:
            var_name = stmt.name
            
            # Check for hardcoded secrets
            if isinstance(stmt.initializer, Literal) and hasattr(stmt.initializer, 'value'):
                if self._looks_like_secret(str(stmt.initializer.value)):
                    self._add_security_issue(
                        'high',
                        stmt.token.line if hasattr(stmt, 'token') else 0,
                        f"Variable '{var_name}' contains potential hardcoded secret"
                    )
            
            # Check for insecure variable names
            if self._is_insecure_variable_name(var_name):
                self._add_security_issue(
                    'low',
                    stmt.token.line if hasattr(stmt, 'token') else 0,
                    f"Variable '{var_name}' may contain sensitive information"
                )
    
    def _analyze_function_declaration(self, stmt: FunctionStmt) -> None:
        """Analyze function declaration for security issues."""
        # Check function name for security implications
        if self._is_insecure_function_name(stmt.name):
            self._add_security_issue(
                'medium',
                stmt.token.line if hasattr(stmt, 'token') else 0,
                f"Function '{stmt.name}' may perform security-sensitive operations"
            )
        
        # Analyze function body
        for body_stmt in stmt.body.body:
            self._analyze_statement(body_stmt)
    
    def _get_function_name(self, callee) -> str:
        """Extract function name from callee expression."""
        if hasattr(callee, 'lexeme'):
            return callee.lexeme
        elif hasattr(callee, 'name'):
            return callee.name
        else:
            return str(callee)
    
    def _looks_like_secret(self, value: str) -> bool:
        """Check if a string looks like a secret/key."""
        value_lower = value.lower()
        
        # Common secret patterns
        secret_patterns = [
            'password', 'passwd', 'pwd',
            'secret', 'key', 'token',
            'api_key', 'apikey', 'api-key',
            'private_key', 'privatekey',
            'auth', 'credential', 'cred'
        ]
        
        # Check for patterns
        for pattern in secret_patterns:
            if pattern in value_lower:
                return True
        
        # Check for base64-like strings (potential encoded secrets)
        if len(value) > 20 and self._is_base64_like(value):
            return True
        
        # Check for hex-like strings
        if len(value) > 16 and self._is_hex_like(value):
            return True
        
        return False
    
    def _is_base64_like(self, value: str) -> bool:
        """Check if string looks like base64."""
        base64_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=')
        return all(c in base64_chars for c in value) and len(value) % 4 == 0
    
    def _is_hex_like(self, value: str) -> bool:
        """Check if string looks like hexadecimal."""
        hex_chars = set('0123456789abcdefABCDEF')
        return all(c in hex_chars for c in value)
    
    def _involves_user_input(self, expr) -> bool:
        """Check if expression involves user input."""
        # This is a simplified check - in practice, you'd track data flow
        if hasattr(expr, 'lexeme'):
            return any(input_type in expr.lexeme.lower() 
                      for input_type in ['input', 'user', 'form', 'request', 'param'])
        return False
    
    def _is_insecure_variable_name(self, name: str) -> bool:
        """Check if variable name suggests sensitive data."""
        name_lower = name.lower()
        sensitive_patterns = [
            'password', 'passwd', 'pwd',
            'secret', 'key', 'token',
            'auth', 'credential', 'cred',
            'private', 'confidential'
        ]
        return any(pattern in name_lower for pattern in sensitive_patterns)
    
    def _is_insecure_function_name(self, name: str) -> bool:
        """Check if function name suggests security operations."""
        name_lower = name.lower()
        security_patterns = [
            'auth', 'authenticate', 'login',
            'password', 'encrypt', 'decrypt',
            'hash', 'verify', 'validate',
            'sanitize', 'escape', 'filter'
        ]
        return any(pattern in name_lower for pattern in security_patterns)
    
    def _add_security_issue(self, severity: str, line: int, message: str) -> None:
        """Add a security issue."""
        self.issues.append({
            'severity': severity,
            'line': line,
            'message': message,
            'type': 'security'
        })


def analyze_security(ast: List[Stmt]) -> List[Dict[str, Any]]:
    """Convenience function to analyze security."""
    analyzer = SecurityAnalyzer()
    return analyzer.analyze(ast)
