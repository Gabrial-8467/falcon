# src/falcon/vm.py
"""
Stack-based VM for Falcon (A3 hybrid).

- Executes Code objects produced by compiler.Compiler
- Supports builtin calls via BUILTINS mapping
- If a FunctionObject is AST-backed (captures present), VM will delegate execution to the Interpreter fallback
- Designed for safety and clarity
"""

from __future__ import annotations
from typing import Any, List, Tuple, Dict, Optional
import sys
import types

from .compiler import Code, FunctionObject
from .builtins import BUILTINS
from .interpreter import Interpreter, InterpreterError  # interpreter is fallback for closures
from .compiler import OP_LOAD_CONST, OP_LOAD_GLOBAL, OP_STORE_GLOBAL, OP_LOAD_LOCAL, OP_STORE_LOCAL
from .compiler import OP_POP, OP_ADD, OP_SUB, OP_MUL, OP_DIV, OP_MOD
from .compiler import OP_EQ, OP_NEQ, OP_LT, OP_LTE, OP_GT, OP_GTE
from .compiler import OP_AND, OP_OR, OP_NOT
from .compiler import OP_JUMP, OP_JUMP_IF_FALSE, OP_CALL, OP_RETURN
from .compiler import OP_PRINT, OP_MAKE_FUNCTION, OP_LOAD_ATTR, OP_STORE_ATTR, OP_LOOP, OP_NOP

# We'll import remaining ops names if needed by string name lookups
# Local small helper exceptions
class VMRuntimeError(Exception):
    pass

class Frame:
    def __init__(self, code: Code, globals_: Dict[str, Any], locals_: List[Any], ret_addr: int = 0, name: Optional[str]=None):
        self.code = code
        self.ip = 0
        self.stack: List[Any] = []
        self.locals = locals_
        self.globals = globals_
        self.ret_addr = ret_addr
        self.name = name or code.name

    def __repr__(self):
        return f"<Frame {self.name} ip={self.ip} stack={len(self.stack)}>"

class VM:
    def __init__(self, verbose: bool = False):
        self.frames: List[Frame] = []
        self.globals: Dict[str, Any] = {}
        # seed builtins into globals (as constants)
        for k, v in BUILTINS.items():
            self.globals[k] = v
        self.verbose = verbose
        self.interpreter = Interpreter()  # fallback interpreter for closures & complex constructs

    def run_code(self, code: Code):
        # create top-level frame
        globals_ = dict(self.globals)
        locals_ = [None] * code.nlocals
        frame = Frame(code, globals_, locals_, name=code.name)
        self.frames.append(frame)
        try:
            res = self.run_frame(frame)
            return res
        finally:
            self.frames.pop()

    def run_frame(self, frame: Frame):
        code = frame.code
        stack = frame.stack
        instrs = code.instructions
        consts = code.consts

        def push(v): stack.append(v)
        def pop():
            if not stack:
                raise VMRuntimeError("Stack underflow")
            return stack.pop()

        while frame.ip < len(instrs):
            op, arg = instrs[frame.ip]
            if self.verbose:
                print(f"[VM] {frame.name}:{frame.ip} {op} {arg}  STACK={stack}")
            frame.ip += 1

            if op == OP_LOAD_CONST:
                push(consts[arg])
                continue
            if op == OP_LOAD_GLOBAL:
                name = arg
                push(frame.globals.get(name, None))
                continue
            if op == OP_STORE_GLOBAL:
                name = arg
                v = pop()
                frame.globals[name] = v
                continue
            if op == OP_LOAD_LOCAL:
                idx = arg
                try:
                    push(frame.locals[idx])
                except IndexError:
                    push(None)
                continue
            if op == OP_STORE_LOCAL:
                idx = arg
                v = pop()
                # grow locals array if needed
                if idx >= len(frame.locals):
                    frame.locals.extend([None] * (idx - len(frame.locals) + 1))
                frame.locals[idx] = v
                continue
            if op == OP_POP:
                pop()
                continue

            if op == OP_ADD:
                b = pop(); a = pop()
                try:
                    push(self._binary_add(a, b))
                except Exception as e:
                    raise VMRuntimeError(
                        f"ADD error in frame '{frame.name}' at ip={frame.ip-1}: {e} | operands: {a!r}, {b!r}"
                    ) from e
                continue
            if op == OP_SUB:
                b = pop(); a = pop()
                try:
                    push(a - b)
                except Exception as e:
                    raise VMRuntimeError(
                        f"SUB error in frame '{frame.name}' at ip={frame.ip-1}: {e} | operands: {a!r}, {b!r}"
                    ) from e
                continue
            if op == OP_MUL:
                b = pop(); a = pop()
                try:
                    push(a * b)
                except Exception as e:
                    raise VMRuntimeError(
                        f"MUL error in frame '{frame.name}' at ip={frame.ip-1}: {e} | operands: {a!r}, {b!r}"
                    ) from e
                continue
            if op == OP_DIV:
                b = pop(); a = pop()
                try:
                    push(a / b)
                except Exception as e:
                    raise VMRuntimeError(
                        f"DIV error in frame '{frame.name}' at ip={frame.ip-1}: {e} | operands: {a!r}, {b!r}"
                    ) from e
                continue
            if op == OP_MOD:
                b = pop(); a = pop()
                try:
                    push(a % b)
                except Exception as e:
                    raise VMRuntimeError(
                        f"MOD error in frame '{frame.name}' at ip={frame.ip-1}: {e} | operands: {a!r}, {b!r}"
                    ) from e
                continue


            if op == OP_EQ:
                b = pop(); a = pop(); push(a == b); continue
            if op == OP_NEQ:
                b = pop(); a = pop(); push(a != b); continue
            if op == OP_LT:
                b = pop(); a = pop(); push(a < b); continue
            if op == OP_LTE:
                b = pop(); a = pop(); push(a <= b); continue
            if op == OP_GT:
                b = pop(); a = pop(); push(a > b); continue
            if op == OP_GTE:
                b = pop(); a = pop(); push(a >= b); continue

            if op == OP_AND:
                b = pop(); a = pop(); push(a and b); continue
            if op == OP_OR:
                b = pop(); a = pop(); push(a or b); continue
            if op == OP_NOT:
                a = pop(); push(not a); continue

            if op == OP_JUMP:
                frame.ip = arg
                continue
            if op == OP_JUMP_IF_FALSE:
                cond = pop()
                if not self._is_truthy(cond):
                    frame.ip = arg
                continue

            if op == OP_PRINT:
                val = pop()
                # prefer show builtin if exists
                show = frame.globals.get("show") or BUILTINS.get("show")
                if callable(show):
                    try:
                        show(val)
                    except Exception:
                        print(val)
                else:
                    print(val)
                continue

            if op == OP_MAKE_FUNCTION:
                mode = arg[0]
                if mode == "AST":
                    idx = arg[1]
                    ast_node = consts[idx]
                    # FunctionObject with ast_node -> interpreter fallback
                    fobj = FunctionObject(ast_node.name if hasattr(ast_node, "name") else None, None, ast_node)
                    push(fobj)
                    continue
                if mode == "CODE":
                    # arg = ("CODE", const_idx, name, argcount, nlocals)
                    _, const_idx, fname, argcount, nlocals = arg
                    c = consts[const_idx]
                    fobj = FunctionObject(fname, c, None)
                    push(fobj)
                    continue
                raise VMRuntimeError("Unknown MAKE_FUNCTION mode")

            if op == OP_LOAD_ATTR:
                attr = arg
                base = pop()
                # dict-like
                try:
                    if isinstance(base, dict):
                        push(base.get(attr, None))
                    else:
                        push(getattr(base, attr, None))
                except Exception as e:
                    raise VMRuntimeError(f"Load attribute error: {e}") from e
                continue

            if op == OP_STORE_ATTR:
                # VM expects: ... base, value  -> set base.attr = value
                value = pop()
                base = pop()
                try:
                    if isinstance(base, dict):
                        base[arg] = value
                    else:
                        setattr(base, arg, value)
                    # leave value on stack as assignment expression result
                    push(value)
                except Exception as e:
                    raise VMRuntimeError(f"Store attribute error: {e}") from e
                continue

            if op == OP_CALL:
                argc = arg
                args = [pop() for _ in range(argc)][::-1]
                callee = pop()
                # If FunctionObject and code-backed -> create new frame and run
                if isinstance(callee, FunctionObject):
                    if callee.is_ast_backed():
                        # delegate to interpreter fallback (ensures closures work)
                        try:
                            # Interp needs a FunctionStmt/FunctionExpr; use interpreter API to call it
                            # We'll expect interpreter to expose a call_function-like ability:
                            # For simplicity, call interpreter.interpret on a small wrapper:
                            # Build a synthetic call: create a FunctionStmt/Expr and run with interpreter
                            # We assume Interpreter has a method `call_function_ast(func_node, args)`
                            if hasattr(self.interpreter, "call_function_ast"):
                                result = self.interpreter.call_function_ast(callee.ast_node, args)
                                push(result)
                                continue
                            # Fallback: inject AST as top-level run (less ideal)
                            raise VMRuntimeError("Interpreter fallback call not implemented (no call_function_ast)")
                        except InterpreterError as e:
                            raise VMRuntimeError(f"Interpreter error: {e}") from e
                    else:
                        # code-backed function: create new frame
                        subcode: Code = callee.code
                        # prepare locals: size = nlocals, fill with None, then set first argcount locals to args
                        locals_ = [None] * subcode.nlocals
                        for i, a in enumerate(args[:subcode.argcount]):
                            if i < len(locals_):
                                locals_[i] = a
                        new_frame = Frame(subcode, frame.globals, locals_, name=subcode.name)
                        # push current frame and run new one
                        self.frames.append(new_frame)
                        try:
                            result = self.run_frame(new_frame)
                        finally:
                            self.frames.pop()
                        push(result)
                        continue
                # If callee is a Python callable (builtin)
                if callable(callee):
                    try:
                        res = callee(*args)
                        push(res)
                        continue
                    except Exception as e:
                        raise VMRuntimeError(f"Builtin call error: {e}") from e
                raise VMRuntimeError(f"Attempted to call non-callable: {callee}")

            if op == OP_RETURN:
                # return value is top of stack
                val = None
                if stack:
                    val = pop()
                return val

            if op == OP_LOOP:
                # not used much here
                continue

            if op == OP_NOP:
                continue

            raise VMRuntimeError(f"Unknown opcode: {op}")

        # end while
        # if reached end without return, return None
        return None

    # ---------------- helpers ----------------
    @staticmethod
    def _is_truthy(v: Any) -> bool:
        if v is None:
            return False
        if isinstance(v, bool):
            return v
        if isinstance(v, (int, float)):
            return v != 0
        if isinstance(v, str):
            return len(v) > 0
        if isinstance(v, (list, dict, tuple, set)):
            return len(v) > 0
        return True

    @staticmethod
    def _binary_add(a: Any, b: Any) -> Any:
        # string coercion if either is str
        if isinstance(a, str) or isinstance(b, str):
            try:
                from .builtins import _to_string_impl
                return _to_string_impl(a) + _to_string_impl(b)
            except Exception:
                return str(a) + str(b)
        return a + b
