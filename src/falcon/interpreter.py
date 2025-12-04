"""
Interpreter for Falcon (JS-like) AST.

Updated to support:
- Member access (base.name) resolving attributes on Python objects & dicts
- Method-style calls like console.log("hi")
- Using Promise stub objects returned from builtins
"""
from __future__ import annotations

from typing import Any, List, Optional, Callable
from .ast_nodes import (
    Expr, Literal, Variable, Binary, Unary, Grouping, Call, Member,
    Stmt, ExprStmt, LetStmt, PrintStmt, BlockStmt, IfStmt, WhileStmt,
    FunctionStmt, ReturnStmt,
)
from .env import Environment
from .builtins import BUILTINS, Promise

class InterpreterError(Exception):
    pass


class _ReturnSignal(Exception):
    def __init__(self, value: Any):
        super().__init__("return signal")
        self.value = value


class Function:
    def __init__(self, name: Optional[str], params: List[str], body: BlockStmt, closure: Environment):
        self.name = name
        self.params = params
        self.body = body
        self.closure = closure

    def call(self, interpreter: "Interpreter", args: List[Any]) -> Any:
        if len(args) != len(self.params):
            raise InterpreterError(f"Function expected {len(self.params)} args but got {len(args)}")
        local = Environment(self.closure)
        for name, val in zip(self.params, args):
            local.define(name, val)
        if self.name:
            local.define(self.name, self)
        try:
            for stmt in self.body.body:
                interpreter._execute(stmt, local)
        except _ReturnSignal as rs:
            return rs.value
        return None


class Interpreter:
    def __init__(self):
        self.globals = Environment()
        for name, fn in BUILTINS.items():
            self.globals.define(name, fn)

    def interpret(self, stmts: List[Stmt]) -> None:
        try:
            for s in stmts:
                self._execute(s, self.globals)
        except InterpreterError:
            raise
        except Exception as e:
            raise InterpreterError(str(e)) from e

    # ---- statements ----
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
            try:
                pr = env.get("print")
                if callable(pr):
                    pr(v)
                    return
            except Exception:
                pass
            print(v)
            return

        if isinstance(stmt, BlockStmt):
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
            while self._is_truthy(self._eval(stmt.condition, env)):
                self._execute(stmt.body, env)
            return

        if isinstance(stmt, FunctionStmt):
            func = Function(stmt.name, stmt.params, stmt.body, env)
            env.define(stmt.name, func)
            return

        if isinstance(stmt, ReturnStmt):
            val = self._eval(stmt.value, env) if stmt.value is not None else None
            raise _ReturnSignal(val)

        raise InterpreterError(f"Unknown statement type: {type(stmt).__name__}")

    # ---- expressions ----
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

        if isinstance(expr, Member):
            base_val = self._eval(expr.base, env)
            # If base is dict-like
            if isinstance(base_val, dict):
                if expr.name in base_val:
                    return base_val[expr.name]
            # If base is Python object with attribute
            if hasattr(base_val, expr.name):
                attr = getattr(base_val, expr.name)
                # If it's a function, we return a bound callable that preserves `this` semantics if needed later
                if callable(attr):
                    return attr
                return attr
            raise InterpreterError(f"Attribute '{expr.name}' not found on value")

        if isinstance(expr, Call):
            callee_val = self._eval(expr.callee, env)
            args = [self._eval(a, env) for a in expr.arguments]

            # If callee_val is our Function object
            if isinstance(callee_val, Function):
                return callee_val.call(self, args)

            # If callee_val is Promise factory/class (callable)
            if callee_val is Promise:
                # allow Promise.resolve style usage or new Promise-like usage
                # If called with a single executor function, try to call it immediately (sync stub)
                if len(args) == 1 and callable(args[0]):
                    try:
                        p = Promise(lambda res, rej: args[0](res, rej))
                        return p
                    except Exception as e:
                        return Promise.reject(e)
                # otherwise create a resolved promise from arg0 or None
                return Promise.resolve(args[0] if args else None)

            # If callee_val is a Python callable (built-in)
            if callable(callee_val):
                try:
                    return callee_val(*args)
                except TypeError as e:
                    raise InterpreterError(f"Error calling function: {e}") from e
                except Exception as e:
                    raise InterpreterError(f"Error in builtin call: {e}") from e

            raise InterpreterError("Attempted to call a non-callable value")

        raise InterpreterError(f"Unsupported expression type: {type(expr).__name__}")

    # ---------------- helpers ----------------
    @staticmethod
    def _is_truthy(value: Any) -> bool:
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
