"""
Final optimized Vyom VM (integer opcode version)
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
        self.stack: List[Any] = [None] * 256  # Pre-allocated stack
        self.sp = -1  # Stack pointer for faster access
        self.locals = locals_
        self.globals = globals_
        self.name = name or code.name
    
    def push(self, v: Any) -> None:
        """Optimized push operation"""
        self.sp += 1
        self.stack[self.sp] = v
    
    def pop(self) -> Any:
        """Optimized pop operation"""
        v = self.stack[self.sp]
        self.sp -= 1
        return v


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
        sp = frame.sp  # Use local variable for stack pointer
        locals_ = frame.locals
        globals_ = frame.globals

        ip = frame.ip
        n = len(instrs)

        # Inline push/pop for maximum performance
        def push(v: Any) -> None:
            nonlocal sp
            sp += 1
            stack[sp] = v
        
        def pop() -> Any:
            nonlocal sp
            v = stack[sp]
            sp -= 1
            return v

        # ----------------------------------
        # Inline stack operations for performance
        # ----------------------------------

        # ----------------------------------
        # MAIN LOOP - Optimized dispatch
        # ----------------------------------
        while ip < n:
            op, arg = instrs[ip]
            ip += 1

            # Optimized dispatch with if-elif chains (faster than dict lookup)
            if op == OP_LOAD_CONST:
                push(consts[arg])
            elif op == OP_LOAD_GLOBAL:
                push(globals_.get(arg))
            elif op == OP_STORE_GLOBAL:
                globals_[arg] = pop()
            elif op == OP_LOAD_LOCAL:
                push(locals_[arg] if arg < len(locals_) else None)
            elif op == OP_STORE_LOCAL:
                v = pop()
                if arg >= len(locals_):
                    locals_.extend([None] * (arg - len(locals_) + 1))
                locals_[arg] = v
            elif op == OP_POP:
                pop()
            
            # Optimized arithmetic operations
            elif op == OP_ADD:
                b = pop()
                a = pop()
                # Inline string concatenation check
                if isinstance(b, str) or isinstance(a, str):
                    from .builtins import _to_string_impl
                    push(_to_string_impl(a) + _to_string_impl(b))
                else:
                    push(a + b)
            elif op == OP_SUB:
                b = pop()
                a = pop()
                push(a - b)
            elif op == OP_MUL:
                b = pop()
                a = pop()
                push(a * b)
            elif op == OP_DIV:
                b = pop()
                a = pop()
                push(a / b)
            elif op == OP_MOD:
                b = pop()
                a = pop()
                push(a % b)
            
            # Optimized comparison operations
            elif op == OP_EQ:
                b = pop()
                a = pop()
                push(a == b)
            elif op == OP_NEQ:
                b = pop()
                a = pop()
                push(a != b)
            elif op == OP_LT:
                b = pop()
                a = pop()
                push(a < b)
            elif op == OP_LTE:
                b = pop()
                a = pop()
                push(a <= b)
            elif op == OP_GT:
                b = pop()
                a = pop()
                push(a > b)
            elif op == OP_GTE:
                b = pop()
                a = pop()
                push(a >= b)
            
            # Optimized logical operations
            elif op == OP_AND:
                b = pop()
                a = pop()
                push(a and b)
            elif op == OP_OR:
                b = pop()
                a = pop()
                push(a or b)
            elif op == OP_NOT:
                push(not pop())
            
            # Optimized jump operations
            elif op == OP_JUMP:
                ip = arg
                continue
            elif op == OP_JUMP_IF_FALSE:
                if not self._truthy(pop()):
                    ip = arg
                continue
            
            # Optimized print operation
            elif op == OP_PRINT:
                v = pop()
                show = globals_.get("show")
                if callable(show):
                    show(v)
                else:
                    print(v)
            
            # Optimized attribute operations
            elif op == OP_LOAD_ATTR:
                base = pop()
                if isinstance(base, dict):
                    push(base.get(arg))
                else:
                    push(getattr(base, arg, None))
            elif op == OP_STORE_ATTR:
                val = pop()
                base = pop()
                if isinstance(base, dict):
                    base[arg] = val
                else:
                    setattr(base, arg, val)
                push(val)
            
            # Function operations
            elif op == OP_MAKE_FUNCTION:
                mode = arg[0]
                if mode == "AST":
                    idx = arg[1]
                    ast = consts[idx]
                    push(FunctionObject(getattr(ast, "name", None), None, ast))
                else:
                    _, idx, name, argc, nloc = arg
                    c = consts[idx]
                    push(FunctionObject(name, c, None))
            elif op == OP_CALL:
                argc = arg
                args = [pop() for _ in range(argc)][::-1]
                callee = pop()

                if isinstance(callee, FunctionObject):
                    # AST function
                    if callee.is_ast_backed():
                        res = self.interpreter.call_function_ast(callee.ast_node, args)
                        push(res)
                        continue

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
                    continue

                # interpreter function
                call_attr = getattr(callee, "call", None)
                if callable(call_attr):
                    try: push(call_attr(self.interpreter, args))
                    except TypeError: push(call_attr(*args))
                    continue
                
                # Python builtin
                if callable(callee):
                    push(callee(*args))
                    continue

                raise VMRuntimeError(f"not callable: {callee}")

            elif op == OP_RETURN:
                result = pop() if sp >= 0 else None
                return result
            
            # Optimized opcodes
            elif op == OP_INC_LOCAL:
                idx = arg
                if idx >= len(locals_):
                    locals_.extend([None] * (idx - len(locals_) + 1))
                if locals_[idx] is None:
                    locals_[idx] = 1
                else:
                    locals_[idx] += 1
            elif op == OP_JUMP_IF_GE_LOCAL_IMM:
                idx, limit, target = arg
                val = locals_[idx] if idx < len(locals_) and locals_[idx] is not None else 0
                if val >= limit:
                    ip = target
                    continue
            elif op == OP_FAST_COUNT:
                idx, limit, target = arg
                if idx >= len(locals_):
                    locals_.extend([None]*(idx-len(locals_)+1))
                locals_[idx] = limit
                ip = target
                continue
            
            else:
                raise VMRuntimeError(f"unknown opcode {op}")
            
            # Update stack pointer for next iteration
            frame.sp = sp

        return None


    @staticmethod
    def _truthy(v):
        if v is None: return False
        if isinstance(v, bool): return v
        if isinstance(v, (int,float)): return v != 0
        if isinstance(v, str): return len(v)>0
        if isinstance(v, (list,dict,tuple,set)): return len(v)>0
        return True
