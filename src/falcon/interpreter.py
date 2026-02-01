"""
Interpreter for Falcon (JS-like) AST.

Updated to support:
- Member access (base.name) resolving attributes on Python objects & dicts
- Method-style calls like console.log("hi")
- Function expressions evaluation (returns Function object)
- Assignment expressions (target = value) with env.assign and member set
- String coercion for '+' and helper _to_string to match builtins.toString
- var / const declaration support via LetStmt.is_const
- ForStmt and LoopStmt runtime handling
- `show` as the primary output builtin (no legacy `print` handling)
- `break` statement support (BreakStmt) with proper loop-scoped behavior
"""
from __future__ import annotations

from typing import Any, List, Optional, Callable
from .ast_nodes import (
    Expr, Literal, Variable, Binary, Unary, Grouping, Call, Member, FunctionExpr, Assign,
    Stmt, ExprStmt, LetStmt, BlockStmt, IfStmt, WhileStmt,
    FunctionStmt, ReturnStmt, ForStmt, LoopStmt, BreakStmt,
)
from .env import Environment
from .builtins import BUILTINS, Promise

class InterpreterError(Exception):
    pass


class _ReturnSignal(Exception):
    def __init__(self, value: Any):
        super().__init__("return signal")
        self.value = value


class _BreakSignal(Exception):
    """Internal signal used to unwind out of loops for 'break'."""
    pass


class Function:
    """
    Runtime function wrapper for AST-defined functions (used by interpreter).
    The compiler/VM may produce different callable objects; this is the interpreter's.
    """
    def __init__(self, name: Optional[str], params: List[str], body: BlockStmt, closure: Environment):
        self.name = name
        self.params = params
        self.body = body
        self.closure = closure

    def call(self, interpreter: "Interpreter", args: List[Any]) -> Any:
        if len(args) != len(self.params):
            raise InterpreterError(f"Function expected {len(self.params)} args but got {len(args)}")
        local = Environment(self.closure)
        local.is_function_scope = True
        local.is_function_scope = True
        local.is_function_scope = True
        local.is_function_scope = True
        for name, val in zip(self.params, args):
            local.define(name, val)
        if self.name:
            # bind the function itself in its local scope (allow recursion)
            # make the function binding const to avoid accidental overwrite inside its own scope
            local.define(self.name, self, is_const=True)
        try:
            for stmt in self.body.body:
                interpreter._execute(stmt, local)
        except _ReturnSignal as rs:
            return rs.value
        return None


    def __init__(self):
        self.globals = Environment()
        for name, fn in BUILTINS.items():
            self.globals.define(name, fn, is_const=True)
        self._loop_depth = 0
        self._loop_depth = 0
    def _function_env(self, env: Environment) -> Environment:
        """Return the nearest function-scope environment (or globals)."""
        while env is not None and not getattr(env, "is_function_scope", False):
            env = env.parent
        return env if env is not None else self.globals

    def _hoist_vars(self, stmts: List[Stmt], env: Environment) -> None:
        """Pre‑declare all `var` declarations in the given environment.
        Variables are defined with value None (JS `undefined`)."""
        for stmt in stmts:
            if isinstance(stmt, LetStmt) and getattr(stmt, "is_var", False):
                func_env = self._function_env(env)
                if stmt.name not in func_env.values:
                    func_env.define(stmt.name, None, is_const=False)
            # Recurse into blocks
            if isinstance(stmt, BlockStmt):
                self._hoist_vars(stmt.body, env)
            # Functions introduce new scopes – do not hoist inside them
            if isinstance(stmt, FunctionStmt):
                continue

        # Hoisting does not reinitialize globals; globals are set in __init__


    def interpret(self, stmts: List[Stmt]) -> None:
        self._hoist_vars(stmts, self.globals)
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
            target_env = self._function_env(env) if getattr(stmt, "is_var", False) else env
            target_env.define(stmt.name, value, is_const=getattr(stmt, "is_const", False))
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

        # ---------------- BreakStmt ----------------
        if isinstance(stmt, BreakStmt):
            if self._loop_depth <= 0:
                raise InterpreterError("Runtime error: 'break' used outside of a loop")
            # signal to unwind the nearest loop
            raise _BreakSignal()

        # ---------------- ForStmt (Falcon-style 'for') ----------------
        if isinstance(stmt, ForStmt):
            # Evaluate start/end/step in the current env
            start_val = self._eval(stmt.start, env)
            end_val = self._eval(stmt.end, env)
            step_val = self._eval(stmt.step, env) if stmt.step is not None else 1

            # create a loop-local environment so the iterator is scoped to the loop
            loop_env = Environment(env)
            # initialize loop variable
            loop_env.define(stmt.name, start_val)

            # ensure numeric step
            try:
                s = float(step_val)
            except Exception:
                raise InterpreterError("for-loop 'step' must be a number")
            if s == 0:
                raise InterpreterError("for-loop 'step' must not be zero")

            # helper for inclusive 'to' semantics
            def _cond(cur, endv, stepn):
                try:
                    if stepn > 0:
                        return cur <= endv
                    else:
                        return cur >= endv
                except Exception:
                    raise InterpreterError("for-loop comparison failed (non-comparable values)")

            # run loop; support 'return' inside body via _ReturnSignal propagation
            self._loop_depth += 1
            try:
                while _cond(loop_env.get(stmt.name), end_val, s):
                    try:
                        for st in stmt.body.body:
                            self._execute(st, loop_env)
                    except _ReturnSignal:
                        # propagate return upwards
                        raise
                    except _BreakSignal:
                        # break out of this for-loop
                        break
                    # increment iterator using Python numeric semantics
                    cur = loop_env.get(stmt.name)
                    try:
                        loop_env.assign(stmt.name, cur + step_val)
                    except Exception as e:
                        raise InterpreterError(f"Failed to increment loop variable: {e}") from e
            finally:
                self._loop_depth -= 1
            return

        # ---------------- LoopStmt (infinite) ----------------
        if isinstance(stmt, LoopStmt):
            loop_env = Environment(env)
            self._loop_depth += 1
            try:
                while True:
                    try:
                        for st in stmt.body.body:
                            self._execute(st, loop_env)
                    except _ReturnSignal:
                        # propagate return outwards
                        raise
                    except _BreakSignal:
                        # exit the infinite loop
                        break
            finally:
                self._loop_depth -= 1
            # loop naturally falls through after break; otherwise it never returns
            return

        if isinstance(stmt, FunctionStmt):
            func = Function(stmt.name, stmt.params, stmt.body, env)
            env.define(stmt.name, func)
            return

        if isinstance(stmt, ReturnStmt):
            val = self._eval(stmt.value, env) if stmt.value is not None else None
            raise _ReturnSignal(val)

        raise InterpreterError(f"Unknown statement type: {type(stmt).__name__}")
    
    # ---------------- expressions ----------------
    def _eval(self, expr: Expr, env: Environment) -> Any:
        if isinstance(expr, Literal):
            return expr.value

        if isinstance(expr, Variable):
            # Defensive: 'break' should never be treated as a variable.
            # If it appears here, either the lexer produced IDENT for 'break'
            # or an older module/path is being executed. Give a clear error.
            if expr.name == "break":
                raise InterpreterError(
                    "Runtime error: 'break' used as an identifier/variable. "
                    "The 'break' keyword must be a statement inside a loop (e.g. `break;`). "
                    "If you see this unexpectedly, ensure your lexer/parser emit a BreakStmt "
                    "and that you're running the up-to-date interpreter module."
                )
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
                # If either operand is a string, coerce both to strings
                if isinstance(left, str) or isinstance(right, str):
                    return self._to_string(left) + self._to_string(right)
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

        if isinstance(expr, Assign):
            # evaluate value first
            val = self._eval(expr.value, env)
            target = expr.target
            # Variable target
            if isinstance(target, Variable):
                try:
                    env.assign(target.name, val)
                except NameError as e:
                    raise InterpreterError(str(e)) from e
                return val
            # Member target (base.name)
            if isinstance(target, Member):
                base_val = self._eval(target.base, env)
                # dict-like
                if isinstance(base_val, dict):
                    base_val[target.name] = val
                    return val
                # python object attribute
                try:
                    setattr(base_val, target.name, val)
                    return val
                except Exception as e:
                    raise InterpreterError(f"Failed to set attribute '{target.name}': {e}") from e
            raise InterpreterError("Invalid assignment target")

        if isinstance(expr, Member):
            base_val = self._eval(expr.base, env)
            # If base is dict-like
            if isinstance(base_val, dict):
                if expr.name in base_val:
                    return base_val[expr.name]
                # undefined property -> None
                return None
            # If base is Python object with attribute
            if hasattr(base_val, expr.name):
                attr = getattr(base_val, expr.name)
                if callable(attr):
                    return attr
                return attr
            # property doesn't exist, return None
            return None

        if isinstance(expr, FunctionExpr):
            # Create a Function object capturing current env as closure
            return Function(expr.name, expr.params, expr.body, env)

        if isinstance(expr, Call):
            callee_val = self._eval(expr.callee, env)
            args = [self._eval(a, env) for a in expr.arguments]

            # If callee_val is our Function object
            if isinstance(callee_val, Function):
                return callee_val.call(self, args)

            # If callee_val is Promise factory/class (callable)
            if callee_val is Promise:
                if len(args) == 1 and callable(args[0]):
                    try:
                        p = Promise(lambda res, rej: args[0](res, rej))
                        return p
                    except Exception as e:
                        return Promise.reject(e)
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
    def _to_string(self, value: Any) -> str:
        """
        Consistent string conversion used by '+' coercion.
        Mirrors builtins.toString behavior:
         - None -> "null"
         - bool -> "true"/"false"
         - numbers -> str()
         - strings -> unchanged
         - lists/dicts -> json.dumps if possible
         - fallback -> repr()
        """
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, str):
            return value
        if isinstance(value, (int, float)):
            return str(value)
        try:
            import json
            return json.dumps(value)
        except Exception:
            try:
                return repr(value)
            except Exception:
                return "<unrepresentable>"

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

    # ---------------- VM/interoperability helper ----------------
    def call_function_ast(self, func_node, args: List[Any]) -> Any:
        """
        Call an AST-backed function node from VM code. The VM/Compiler should
        arrange for func_node to contain `.params` and `.body`, and ideally a
        `.closure_env` attribute pointing at a suitable Environment (or None).
        If `.closure_env` is None, fall back to interpreter.globals.
        """
        closure_env = getattr(func_node, "closure_env", None)
        if closure_env is None:
            closure_env = self.globals

        local = Environment(closure_env)
        params = getattr(func_node, "params", [])
        for name, val in zip(params, args):
            local.define(name, val)
        # bind function name for recursion if present
        name = getattr(func_node, "name", None)
        if name:
            # provide a callable that routes back to interpreter call
            def _recur_wrapper(*a):
                return self.call_function_ast(func_node, list(a))
            local.define(name, _recur_wrapper, is_const=True)

        try:
            for stmt in func_node.body.body:
                self._execute(stmt, local)
        except _ReturnSignal as rs:
            return rs.value
        return None
