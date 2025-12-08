# src/falcon/vm.py
"""
Stack-based VM for Falcon (handler-table optimized).

- Executes Code objects produced by compiler.Compiler
- Supports builtin calls via BUILTINS mapping
- If a FunctionObject is AST-backed (captures present), VM will delegate execution to the Interpreter fallback
- Designed for clarity, with a faster handler-table dispatch than long if/elif chains
"""

from __future__ import annotations
from typing import Any, List, Tuple, Dict, Optional
import os

from .compiler import Code, FunctionObject
from .builtins import BUILTINS
from .interpreter import Interpreter, InterpreterError  # interpreter is fallback for closures

# import opcode names (strings) from compiler (must match)
from .compiler import (
    OP_LOAD_CONST, OP_LOAD_GLOBAL, OP_STORE_GLOBAL, OP_LOAD_LOCAL, OP_STORE_LOCAL,
    OP_POP, OP_ADD, OP_SUB, OP_MUL, OP_DIV, OP_MOD,
    OP_EQ, OP_NEQ, OP_LT, OP_LTE, OP_GT, OP_GTE,
    OP_AND, OP_OR, OP_NOT,
    OP_JUMP, OP_JUMP_IF_FALSE, OP_CALL, OP_RETURN,
    OP_PRINT, OP_MAKE_FUNCTION, OP_LOAD_ATTR, OP_STORE_ATTR, OP_LOOP, OP_NOP
)

# fused opcodes (strings defined in compiler)
from .compiler import OP_INC_LOCAL, OP_JUMP_IF_GE_LOCAL_IMM, OP_FAST_COUNT

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
        """
        Optimized handler-table driven run_frame.
        Handlers accept (arg, ip) and return:
          - None to continue at current ip
          - int to set ip (absolute)
          - ("__VM_RETURN__", value) to return from this frame
        """
        instrs = frame.code.instructions
        consts = frame.code.consts

        # local references to avoid attribute lookups
        globals_local = frame.globals
        locals_local = frame.locals
        stack_local: List[Any] = frame.stack
        instrs_local = instrs
        consts_local = consts
        n_instrs = len(instrs_local)

        # small push/pop helpers
        def push(v: Any):
            stack_local.append(v)

        def pop():
            if not stack_local:
                raise VMRuntimeError("Stack underflow")
            return stack_local.pop()

        # profile support
        profile_mode = os.environ.get("VM_PROFILE") == "1"
        opcode_counts: Optional[Dict[str, int]] = {} if profile_mode else None

        # ---------- handlers ----------
        def h_load_const(arg, ip):
            push(consts_local[arg])
            return None

        def h_load_global(arg, ip):
            push(globals_local.get(arg, None))
            return None

        def h_store_global(arg, ip):
            v = pop()
            globals_local[arg] = v
            return None

        def h_load_local(arg, ip):
            idx = arg
            try:
                push(locals_local[idx])
            except Exception:
                push(None)
            return None

        def h_store_local(arg, ip):
            idx = arg
            v = pop()
            if idx >= len(locals_local):
                locals_local.extend([None] * (idx - len(locals_local) + 1))
            locals_local[idx] = v
            return None

        def h_pop(arg, ip):
            pop()
            return None

        # arithmetic with string coercion behavior kept via builtins helper
        def h_add(arg, ip):
            b = pop(); a = pop()
            try:
                # preserve string coercion semantics
                if isinstance(a, str) or isinstance(b, str):
                    from .builtins import _to_string_impl
                    push(_to_string_impl(a) + _to_string_impl(b))
                else:
                    push(a + b)
            except Exception as e:
                raise VMRuntimeError(f"ADD error in frame '{frame.name}' at ip={ip-1}: {e}") from e
            return None

        def h_sub(arg, ip):
            b = pop(); a = pop()
            try:
                push(a - b)
            except Exception as e:
                raise VMRuntimeError(f"SUB error in frame '{frame.name}' at ip={ip-1}: {e}") from e
            return None

        def h_mul(arg, ip):
            b = pop(); a = pop()
            try:
                push(a * b)
            except Exception as e:
                raise VMRuntimeError(f"MUL error in frame '{frame.name}' at ip={ip-1}: {e}") from e
            return None

        def h_div(arg, ip):
            b = pop(); a = pop()
            try:
                push(a / b)
            except Exception as e:
                raise VMRuntimeError(f"DIV error in frame '{frame.name}' at ip={ip-1}: {e}") from e
            return None

        def h_mod(arg, ip):
            b = pop(); a = pop()
            try:
                push(a % b)
            except Exception as e:
                raise VMRuntimeError(f"MOD error in frame '{frame.name}' at ip={ip-1}: {e}") from e
            return None

        # comparisons
        def h_eq(arg, ip):
            b = pop(); a = pop(); push(a == b); return None
        def h_neq(arg, ip):
            b = pop(); a = pop(); push(a != b); return None
        def h_lt(arg, ip):
            b = pop(); a = pop(); push(a < b); return None
        def h_lte(arg, ip):
            b = pop(); a = pop(); push(a <= b); return None
        def h_gt(arg, ip):
            b = pop(); a = pop(); push(a > b); return None
        def h_gte(arg, ip):
            b = pop(); a = pop(); push(a >= b); return None

        # logical
        def h_and(arg, ip):
            b = pop(); a = pop(); push(a and b); return None
        def h_or(arg, ip):
            b = pop(); a = pop(); push(a or b); return None
        def h_not(arg, ip):
            a = pop(); push(not a); return None

        # control flow
        def h_jump(arg, ip):
            # arg is an absolute instruction index
            return arg

        def h_jump_if_false(arg, ip):
            cond = pop()
            if not self._is_truthy(cond):
                return arg
            return None

        # print / IO
        def h_print(arg, ip):
            val = pop()
            show = globals_local.get("show") or BUILTINS.get("show")
            if callable(show):
                try:
                    show(val)
                except Exception:
                    # fallback to Python print if builtin failed
                    print(val)
            else:
                print(val)
            return None

        # make function
        def h_make_function(arg, ip):
            mode = arg[0]
            if mode == "AST":
                idx = arg[1]
                ast_node = consts_local[idx]
                fobj = FunctionObject(ast_node.name if hasattr(ast_node, "name") else None, None, ast_node)
                push(fobj)
                return None
            if mode == "CODE":
                _, const_idx, fname, argcount, nlocals = arg
                c = consts_local[const_idx]
                fobj = FunctionObject(fname, c, None)
                push(fobj)
                return None
            raise VMRuntimeError("Unknown MAKE_FUNCTION mode")

        # attribute ops
        def h_load_attr(arg, ip):
            attr = arg
            base = pop()
            try:
                if isinstance(base, dict):
                    push(base.get(attr, None))
                else:
                    push(getattr(base, attr, None))
            except Exception as e:
                raise VMRuntimeError(f"Load attribute error: {e}") from e
            return None

        def h_store_attr(arg, ip):
            value = pop()
            base = pop()
            try:
                if isinstance(base, dict):
                    base[arg] = value
                else:
                    setattr(base, arg, value)
                push(value)
            except Exception as e:
                raise VMRuntimeError(f"Store attribute error: {e}") from e
            return None

        # call dispatch (keeps original semantics)
        def h_call(arg, ip):
            argc = arg
            args = [pop() for _ in range(argc)][::-1] if argc else []
            callee = pop()

            # 1) VM code-backed FunctionObject
            if isinstance(callee, FunctionObject):
                if callee.is_ast_backed():
                    try:
                        if hasattr(self.interpreter, "call_function_ast"):
                            result = self.interpreter.call_function_ast(callee.ast_node, args)
                            push(result)
                            return None
                        raise VMRuntimeError("Interpreter fallback call not implemented (no call_function_ast)")
                    except InterpreterError as e:
                        raise VMRuntimeError(f"Interpreter error: {e}") from e
                else:
                    subcode: Code = callee.code
                    new_locals = [None] * subcode.nlocals
                    for i, a in enumerate(args[:subcode.argcount]):
                        if i < len(new_locals):
                            new_locals[i] = a
                    new_frame = Frame(subcode, globals_local, new_locals, name=subcode.name)
                    self.frames.append(new_frame)
                    try:
                        result = self.run_frame(new_frame)
                    finally:
                        self.frames.pop()
                    push(result)
                    return None

            # 2) Interpreter-provided callables (Function instances)
            try:
                call_attr = getattr(callee, "call", None)
                if callable(call_attr):
                    try:
                        result = call_attr(self.interpreter, args)
                    except TypeError:
                        result = call_attr(*args)
                    push(result)
                    return None
            except Exception as e:
                raise VMRuntimeError(f"Error calling interpreter function: {e}") from e

            # 3) Python builtins / host callables
            if callable(callee):
                try:
                    res = callee(*args)
                    push(res)
                    return None
                except Exception as e:
                    raise VMRuntimeError(f"Builtin call error: {e}") from e

            raise VMRuntimeError(f"Attempted to call non-callable: {callee}")

        def h_return(arg, ip):
            val = None
            if stack_local:
                val = pop()
            return ("__VM_RETURN__", val)

        def h_loop(arg, ip):
            # reserved noop
            return None

        def h_nop(arg, ip):
            return None

        # ------------------ fused op handlers ------------------
        def h_inc_local(arg, ip):
            idx = arg
            if idx >= len(locals_local):
                locals_local.extend([None] * (idx - len(locals_local) + 1))
            curr = locals_local[idx] if locals_local[idx] is not None else 0
            locals_local[idx] = curr + 1
            return None

        def h_jump_if_ge_local_imm(arg, ip):
            # arg is (idx, imm, target)
            idx, imm, target = arg
            val = locals_local[idx] if idx < len(locals_local) and locals_local[idx] is not None else 0
            if val >= imm:
                return target
            return None

        def h_fast_count(arg, ip):
            # arg is (idx, limit)
            idx, limit = arg
            if idx >= len(locals_local):
                locals_local.extend([None] * (idx - len(locals_local) + 1))
            # aggressive fast-path: set local to limit (no side-effects executed)
            locals_local[idx] = limit
            return None

        # ------------------ handler table ------------------
        handlers: Dict[str, Any] = {
            OP_LOAD_CONST: h_load_const,
            OP_LOAD_GLOBAL: h_load_global,
            OP_STORE_GLOBAL: h_store_global,
            OP_LOAD_LOCAL: h_load_local,
            OP_STORE_LOCAL: h_store_local,
            OP_POP: h_pop,
            OP_ADD: h_add,
            OP_SUB: h_sub,
            OP_MUL: h_mul,
            OP_DIV: h_div,
            OP_MOD: h_mod,
            OP_EQ: h_eq,
            OP_NEQ: h_neq,
            OP_LT: h_lt,
            OP_LTE: h_lte,
            OP_GT: h_gt,
            OP_GTE: h_gte,
            OP_AND: h_and,
            OP_OR: h_or,
            OP_NOT: h_not,
            OP_JUMP: h_jump,
            OP_JUMP_IF_FALSE: h_jump_if_false,
            OP_PRINT: h_print,
            OP_MAKE_FUNCTION: h_make_function,
            OP_LOAD_ATTR: h_load_attr,
            OP_STORE_ATTR: h_store_attr,
            OP_CALL: h_call,
            OP_RETURN: h_return,
            OP_LOOP: h_loop,
            OP_NOP: h_nop,
            # fused
            OP_INC_LOCAL: h_inc_local,
            OP_JUMP_IF_GE_LOCAL_IMM: h_jump_if_ge_local_imm,
            OP_FAST_COUNT: h_fast_count,
        }

        # --------------- main dispatch loop ----------------
        ip = frame.ip
        while ip < n_instrs:
            op, arg = instrs_local[ip]
            if self.verbose:
                print(f"[VM] {frame.name}:{ip} {op} {arg}  STACK={stack_local}")
            if profile_mode and opcode_counts is not None:
                opcode_counts[op] = opcode_counts.get(op, 0) + 1
            ip += 1  # advance past current instruction slot

            handler = handlers.get(op)
            if handler is None:
                raise VMRuntimeError(f"Unknown opcode: {op}")

            result = handler(arg, ip)
            # handler result handling
            if result is None:
                continue
            if isinstance(result, tuple) and result and result[0] == "__VM_RETURN__":
                # set ip for trace/debug and return value
                frame.ip = ip
                return result[1]
            if isinstance(result, int):
                ip = result
                continue
            raise VMRuntimeError(f"Handler returned unexpected result for opcode {op}: {result}")

        # fallthrough: reached end without explicit return
        frame.ip = ip
        if profile_mode and opcode_counts is not None:
            try:
                print(f"VM opcode counts for frame {frame.name}:")
                for op_code, cnt in sorted(opcode_counts.items(), key=lambda kv: -kv[1])[:50]:
                    print(f"  OP {op_code}: {cnt}")
            except Exception:
                pass
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
