"""
Final optimized Falcon VM (integer opcode version)
Supports:
- INC_LOCAL
- JUMP_IF_GE_LOCAL_IMM
- FAST_COUNT(local, limit, target)
"""

from __future__ import annotations
from typing import Any, Dict, List, Tuple

from .compiler import (
    Code, FunctionObject,

    OP_LOAD_CONST, OP_LOAD_GLOBAL, OP_STORE_GLOBAL,
    OP_LOAD_LOCAL, OP_STORE_LOCAL,
    OP_POP,

    OP_ADD, OP_SUB, OP_MUL, OP_DIV, OP_MOD,

    OP_EQ, OP_NEQ, OP_LT, OP_LTE, OP_GT, OP_GTE,
    OP_AND, OP_OR, OP_NOT,

    OP_JUMP, OP_JUMP_IF_FALSE, OP_CALL, OP_RETURN,

    OP_PRINT, OP_MAKE_FUNCTION, OP_LOAD_ATTR, OP_STORE_ATTR,
    OP_LOOP, OP_NOP,

    OP_INC_LOCAL, OP_JUMP_IF_GE_LOCAL_IMM,
    OP_FAST_COUNT
)

from .builtins import BUILTINS
from .interpreter import Interpreter


class VMRuntimeError(Exception):
    pass


class Frame:
    def __init__(self, code: Code, globals_, locals_, name=None):
        self.code = code
        self.ip = 0
        self.stack: List[Any] = []
        self.locals = locals_
        self.globals = globals_
        self.name = name or code.name


class VM:
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.frames = []
        self.interpreter = Interpreter()
        self.globals = dict(BUILTINS)

    # ---------------------
    # Entry
    # ---------------------
    def run_code(self, code: Code):
        frame = Frame(code, dict(self.globals), [None] * code.nlocals, name=code.name)
        self.frames.append(frame)
        try:
            return self.run_frame(frame)
        finally:
            self.frames.pop()

    # ---------------------
    # Main VM
    # ---------------------
    def run_frame(self, frame):

        instrs = frame.code.instructions
        consts = frame.code.consts
        stack = frame.stack
        locals_ = frame.locals
        globals_ = frame.globals

        ip = frame.ip
        n = len(instrs)

        def push(v): stack.append(v)
        def pop():
            if not stack: raise VMRuntimeError("stack underflow")
            return stack.pop()

        # ----------------------------------
        # Opcode handlers
        # ----------------------------------
        def h_LOAD_CONST(a): push(consts[a])
        def h_LOAD_GLOBAL(a): push(globals_.get(a))
        def h_STORE_GLOBAL(a): globals_[a] = pop()

        def h_LOAD_LOCAL(a): push(locals_[a] if a < len(locals_) else None)
        def h_STORE_LOCAL(a):
            v = pop()
            if a >= len(locals_):
                locals_.extend([None] * (a - len(locals_) + 1))
            locals_[a] = v

        def h_POP(a): pop()

        # arithmetic
        def h_ADD(a):
            b = pop(); 
            c = pop()
            # string concat safety
            if isinstance(b, str) or isinstance(c, str):
                from .builtins import _to_string_impl
                push(_to_string_impl(c) + _to_string_impl(b))
            else:
                push(c+b)

        def h_SUB(a): b=pop(); a1=pop(); push(a1-b)
        def h_MUL(a): b=pop(); a1=pop(); push(a1*b)
        def h_DIV(a): b=pop(); a1=pop(); push(a1/b)
        def h_MOD(a): b=pop(); a1=pop(); push(a1%b)

        def h_EQ(a): b=pop(); a1=pop(); push(a1==b)
        def h_NEQ(a): b=pop(); a1=pop(); push(a1!=b)
        def h_LT(a): b=pop(); a1=pop(); push(a1<b)
        def h_LTE(a): b=pop(); a1=pop(); push(a1<=b)
        def h_GT(a): b=pop(); a1=pop(); push(a1>b)
        def h_GTE(a): b=pop(); a1=pop(); push(a1>=b)

        def h_AND(a): b=pop(); a1=pop(); push(a1 and b)
        def h_OR(a): b=pop(); a1=pop(); push(a1 or b)
        def h_NOT(a): push(not pop())

        # jumps
        def h_JUMP(t): return t
        def h_JUMP_IF_FALSE(t):
            if not self._truthy(pop()):
                return t

        # printing
        def h_PRINT(a):
            v = pop()
            show = globals_.get("show")
            show(v) if callable(show) else print(v)

        # attribute
        def h_LOAD_ATTR(a):
            base = pop()
            if isinstance(base, dict): push(base.get(a))
            else: push(getattr(base, a, None))

        def h_STORE_ATTR(a):
            val = pop()
            base = pop()
            if isinstance(base, dict):
                base[a] = val
            else:
                setattr(base, a, val)
            push(val)

        # functions
        def h_MAKE_FUNCTION(conf):
            mode = conf[0]
            if mode == "AST":
                idx = conf[1]
                ast = consts[idx]
                push(FunctionObject(getattr(ast, "name", None),
                                    None,
                                    ast))
            else:
                _, idx, name, argc, nloc = conf
                c = consts[idx]
                push(FunctionObject(name, c, None))
        
        def h_CALL(argc):
            args = [pop() for _ in range(argc)][::-1]
            callee = pop()

            if isinstance(callee, FunctionObject):
                # AST function
                if callee.is_ast_backed():
                    res = self.interpreter.call_function_ast(callee.ast_node, args)
                    push(res)
                    return

                # bytecode function
                sub = Frame(callee.code,
                            globals_,
                            [None]*callee.code.nlocals,
                            name=callee.name)
                for i in range(min(len(args), callee.code.argcount)):
                    sub.locals[i] = args[i]

                self.frames.append(sub)
                out = self.run_frame(sub)
                self.frames.pop()
                push(out)
                return

            # interpreter function
            call_attr = getattr(callee, "call", None)
            if callable(call_attr):
                try: push(call_attr(self.interpreter, args))
                except TypeError: push(call_attr(*args))
                return
            
            # Python builtin
            if callable(callee):
                push(callee(*args))
                return

            raise VMRuntimeError(f"not callable: {callee}")

        def h_RETURN(a):
            v = pop() if stack else None
            return ("RET", v)

        # ----------------------------------
        # optimized opcodes
        # ----------------------------------
        def h_INC_LOCAL(idx):
            if idx >= len(locals_):
                locals_.extend([None] * (idx - len(locals_) + 1))
            if locals_[idx] is None:
                locals_[idx] = 1
            else:
                locals_[idx] += 1

        def h_JUMP_IF_GE_LOCAL_IMM(arg):
            idx, limit, target = arg
            val = locals_[idx] if idx < len(locals_) and locals_[idx] is not None else 0
            if val >= limit:
                return target

        def h_FAST_COUNT(arg):
            idx, limit, target = arg
            if idx >= len(locals_):
                locals_.extend([None]*(idx-len(locals_)+1))
            locals_[idx] = limit
            return target

        # ----------------------------------
        # DISPATCH TABLE
        # ----------------------------------
        handlers = {
            OP_LOAD_CONST: h_LOAD_CONST,
            OP_LOAD_GLOBAL: h_LOAD_GLOBAL,
            OP_STORE_GLOBAL: h_STORE_GLOBAL,
            OP_LOAD_LOCAL: h_LOAD_LOCAL,
            OP_STORE_LOCAL: h_STORE_LOCAL,
            OP_POP: h_POP,
            OP_ADD: h_ADD, OP_SUB: h_SUB, OP_MUL: h_MUL,
            OP_DIV: h_DIV, OP_MOD: h_MOD,
            OP_EQ: h_EQ, OP_NEQ: h_NEQ,
            OP_LT: h_LT, OP_LTE: h_LTE,
            OP_GT: h_GT, OP_GTE: h_GTE,
            OP_AND: h_AND, OP_OR: h_OR, OP_NOT: h_NOT,
            OP_JUMP: h_JUMP,
            OP_JUMP_IF_FALSE: h_JUMP_IF_FALSE,
            OP_PRINT: h_PRINT,
            OP_MAKE_FUNCTION: h_MAKE_FUNCTION,
            OP_LOAD_ATTR: h_LOAD_ATTR,
            OP_STORE_ATTR: h_STORE_ATTR,
            OP_CALL: h_CALL,
            OP_RETURN: h_RETURN,
            OP_INC_LOCAL: h_INC_LOCAL,
            OP_JUMP_IF_GE_LOCAL_IMM: h_JUMP_IF_GE_LOCAL_IMM,
            OP_FAST_COUNT: h_FAST_COUNT,
        }

        # ----------------------------------
        # MAIN LOOP
        # ----------------------------------
        while ip < n:
            op, arg = instrs[ip]
            ip += 1

            h = handlers.get(op)
            if h is None:
                raise VMRuntimeError(f"unknown opcode {op}")

            result = h(arg)

            if result is None:
                continue

            if isinstance(result, int):
                ip = result
                continue

            if isinstance(result, tuple) and result[0] == "RET":
                return result[1]

            raise VMRuntimeError(f"invalid handler return {result}")

        return None

    @staticmethod
    def _truthy(v):
        if v is None: return False
        if isinstance(v, bool): return v
        if isinstance(v, (int,float)): return v != 0
        if isinstance(v, str): return len(v)>0
        if isinstance(v, (list,dict,tuple,set)): return len(v)>0
        return True
