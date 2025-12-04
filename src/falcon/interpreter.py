"""
Interpreter for Falcon (JS-like) AST.

This walks AST nodes produced by parser.py (ast_nodes.py) and executes them
using an Environment (env.py). It supports:

- Statements: LetStmt, PrintStmt, ExprStmt, BlockStmt, IfStmt, WhileStmt
- Expressions: Literal, Variable, Binary, Unary, Grouping, Call
- Builtin functions (from builtins.BUILTINS) and user-defined functions
  via FunctionStmt (lightweight closures)
- Proper lexical scopes via Environment(parent=...)
- Return via a dedicated exception raised inside function bodies

Drop this into: src/falcon/interpreter.py
"""
from __future__ import annotations

from typing import Any, List, Optional, Callable
from .ast_nodes import (
    Expr, Literal, Variable, Binary, Unary, Grouping, Call,
    Stmt, ExprStmt, LetStmt, PrintStmt, BlockStmt, IfStmt, WhileStmt,
    FunctionStmt, ReturnStmt,
)
from .env import Environment
from .builtins import BUILTINS


class InterpreterError(Exception):
    pass


class _ReturnSignal(Exception):
    """Internal signal used to return a value from a function body."""
    def __init__(self, value: Any):
        super().__init__("return signal")
        self.value = value


class Function:
    """
    Lightweight function object representing user-defined functions.
    Stores parameter names, a BlockStmt as body, and the closure environment.
    """
    def __init__(self, name: Optional[str], params: List[str], body: BlockStmt, closure: Environment):
        self.name = name
        self.params = params
        self.body = body
        self.closure = closure

    def call(self, interpreter: "Interpreter", args: List[Any]) -> Any:
        if len(args) != len(self.params):
            raise InterpreterError(f"Function expected {len(self.params)} args but got {len(args)}")
        # Create function-local env with closure as parent
        local = Environment(self.closure)
        # Define parameters in local env
        for name, val in zip(self.params, args):
            local.define(name, val)
        # If function has a name, define it inside its own closure (for recursion)
        if self.name:
            local.define(self.name, self)
        try:
            # Execute body (BlockStmt.body is list of statements)
            for stmt in self.body.body:
                interpreter._execute(stmt, local)
        except _ReturnSignal as rs:
            return rs.value
        return None  # implicit undefined / null


class Interpreter:
    def __init__(self):
        # global environment containing builtins
        self.globals = Environment()
        for name, fn in BUILTINS.items():
            # store Python callables directly
            self.globals.define(name, fn)

    def interpret(self, stmts: List[Stmt]) -> None:
        """
        Interpret a list of statements at global scope.
        Raises InterpreterError on runtime issues.
        """
        try:
            for s in stmts:
                self._execute(s, self.globals)
        except InterpreterError:
            raise
        except Exception as e:
            raise InterpreterError(str(e)) from e

    # ---------------- statements ----------------
    def _execute(self, stmt: Stmt, env: Environment) -> None:
        if isinstance(stmt, ExprStmt):
            self._eval(stmt.expr, env)
            return

        if isinstance(stmt, LetStmt):
            value = self._eval(stmt.initializer, env) if stmt.initializer is not None else None
            env.define(stmt.name, value)
            return

        if isinstance(stmt, PrintStmt):
            v = self._eval(stmt.expr, env)
            # prefer built-in print if present
            try:
                pr = env.get("print")
                if callable(pr):
                    pr(v)
                    return
            except Exception:
                pass
            # fallback
            print(v)
            return

        if isinstance(stmt, BlockStmt):
            # Create a new lexical environment for the block
            new_env = Environment(env)
            for s in stmt.body:
                self._execute(s, new_env)
            return

        if isinstance(stmt, IfStmt):
            cond = self._eval(stmt.condition, env)
            if self._is_truthy(cond):
                self._execute(stmt.then_branch, env)
            elif stmt.else_branch is not None:
                self._execute(stmt.else_branch, env)
            return

        if isinstance(stmt, WhileStmt):
            # Evaluate condition before each iteration
            while self._is_truthy(self._eval(stmt.condition, env)):
                self._execute(stmt.body, env)
            return

        if isinstance(stmt, FunctionStmt):
            # Create Function object and bind it in current env
            func = Function(stmt.name, stmt.params, stmt.body, env)
            env.define(stmt.name, func)
            return

        if isinstance(stmt, ReturnStmt):
            # Evaluate return value and signal up the stack
            val = self._eval(stmt.value, env) if stmt.value is not None else None
            raise _ReturnSignal(val)

        raise InterpreterError(f"Unknown statement type: {type(stmt).__name__}")

    # ---------------- expressions ----------------
    def _eval(self, expr: Expr, env: Environment) -> Any:
        if isinstance(expr, Literal):
            return expr.value

        if isinstance(expr, Variable):
            try:
                return env.get(expr.name)
            except NameError as e:
                raise InterpreterError(str(e)) from e

        if isinstance(expr, Grouping):
            return self._eval(expr.expression, env)

        if isinstance(expr, Unary):
            val = self._eval(expr.operand, env)
            if expr.op == "!":
                return not self._is_truthy(val)
            if expr.op == "-":
                if not isinstance(val, (int, float)):
                    raise InterpreterError("Unary '-' expects a number")
                return -val
            raise InterpreterError(f"Unsupported unary operator: {expr.op}")

        if isinstance(expr, Binary):
            # short-circuit for logical operators
            if expr.op == "&&":
                left = self._eval(expr.left, env)
                if not self._is_truthy(left):
                    return left
                return self._eval(expr.right, env)
            if expr.op == "||":
                left = self._eval(expr.left, env)
                if self._is_truthy(left):
                    return left
                return self._eval(expr.right, env)

            left = self._eval(expr.left, env)
            right = self._eval(expr.right, env)

            # arithmetic
            if expr.op == "+":
                return left + right
            if expr.op == "-":
                return left - right
            if expr.op == "*":
                return left * right
            if expr.op == "/":
                return left / right
            if expr.op == "%":
                return left % right

            # comparisons / equality
            if expr.op == "==":
                return left == right
            if expr.op == "!=":
                return left != right
            if expr.op == "<":
                return left < right
            if expr.op == "<=":
                return left <= right
            if expr.op == ">":
                return left > right
            if expr.op == ">=":
                return left >= right

            raise InterpreterError(f"Unsupported binary operator: {expr.op}")

        if isinstance(expr, Call):
            callee_val = self._eval(expr.callee, env)
            args = [self._eval(a, env) for a in expr.arguments]

            # If it's a user-defined Function object
            if isinstance(callee_val, Function):
                return callee_val.call(self, args)

            # If it's a Python callable (builtin)
            if callable(callee_val):
                try:
                    return callee_val(*args)
                except Exception as e:
                    raise InterpreterError(f"Error calling builtin: {e}") from e

            raise InterpreterError("Attempted to call a non-callable value")

        raise InterpreterError(f"Unsupported expression type: {type(expr).__name__}")

    # ---------------- helpers ----------------
    @staticmethod
    def _is_truthy(value: Any) -> bool:
        # JS-like truthiness: false, None, 0, "", empty containers are falsy
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return len(value) > 0
        if isinstance(value, (list, tuple, dict, set)):
            return len(value) > 0
        return True
