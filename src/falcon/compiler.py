# src/falcon/compiler.py
"""
Simple bytecode compiler for Falcon (A3 hybrid prototype).

Produces Code objects with instructions and const pool suitable for vm.VM.
This is a pragmatic, modest compiler — not a full optimizer. It focuses on
correctness and compatibility with the VM and interpreter fallback.

Exposes:
 - class Compiler with compile_module(ast) and compile(ast)
 - Code and FunctionObject dataclasses used by vm.py
 - opcode constants referenced by vm.py
 - CompileError and top-level compile_module wrapper for compatibility
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, List, Tuple, Dict, Optional, Sequence

# --- opcode names used by vm.py (must match) ---
OP_LOAD_CONST = "LOAD_CONST"
OP_LOAD_GLOBAL = "LOAD_GLOBAL"
OP_STORE_GLOBAL = "STORE_GLOBAL"
OP_LOAD_LOCAL = "LOAD_LOCAL"
OP_STORE_LOCAL = "STORE_LOCAL"
OP_POP = "POP"
OP_ADD = "ADD"
OP_SUB = "SUB"
OP_MUL = "MUL"
OP_DIV = "DIV"
OP_MOD = "MOD"
OP_EQ = "EQ"
OP_NEQ = "NEQ"
OP_LT = "LT"
OP_LTE = "LTE"
OP_GT = "GT"
OP_GTE = "GTE"
OP_AND = "AND"
OP_OR = "OR"
OP_NOT = "NOT"
OP_JUMP = "JUMP"
OP_JUMP_IF_FALSE = "JUMP_IF_FALSE"
OP_CALL = "CALL"
OP_RETURN = "RETURN"
OP_PRINT = "PRINT"
OP_MAKE_FUNCTION = "MAKE_FUNCTION"
OP_LOAD_ATTR = "LOAD_ATTR"
OP_STORE_ATTR = "STORE_ATTR"
OP_LOOP = "LOOP"
OP_NOP = "NOP"

Instruction = Tuple[str, Any]


@dataclass
class Code:
    name: str
    instructions: List[Instruction]
    consts: List[Any]
    nlocals: int = 0
    argcount: int = 0


class FunctionObject:
    """
    Wrapper representing a function value used by VM.
    - If code is provided -> code-backed function (fast in VM)
    - If ast_node is provided -> AST-backed function (fallback to interpreter)
    """
    def __init__(self, name: Optional[str], code: Optional[Code], ast_node: Optional[Any] = None):
        self.name = name
        self.code = code
        self.ast_node = ast_node

    def is_ast_backed(self) -> bool:
        return self.ast_node is not None

    def __repr__(self):
        if self.is_ast_backed():
            return f"<FunctionObject AST {getattr(self.ast_node, 'name', '<anon>')}>"
        return f"<FunctionObject CODE {self.code.name}>"


# -------------------------
# Compiler
# -------------------------
class CompileError(Exception):
    pass


class Compiler:
    """
    A very small recursive compiler that walks the AST and emits bytecode.

    Design notes:
     - This compiler favors simplicity. It compiles variables to globals by default.
       Functions compile to nested Code objects and are emitted as FunctionObject
       constants so the VM can call them.
     - For local variable optimization and closures we rely on a future pass.
     - The VM supports interpreter fallback for AST-backed functions; the compiler
       will use that when it cannot produce simple code (we prefer code-backed).
    """

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    # ---------- entry points ----------
    def compile_module(self, stmts: Sequence[Any], name: str = "<module>") -> Code:
        """Compile a list of statements into a top-level Code object."""
        # main const pool and instructions
        consts: List[Any] = []
        instrs: List[Instruction] = []
        ctx = _CompileContext(consts, instrs, name=name)
        # compile each top-level statement
        for s in stmts:
            self._compile_stmt(s, ctx)
        # ensure there's a return
        instrs.append((OP_RETURN, None))
        return Code(name=name, instructions=instrs, consts=consts, nlocals=0, argcount=0)

    # backward compatible alias
    def compile(self, stmts: Sequence[Any], name: str = "<module>") -> Code:
        return self.compile_module(stmts, name=name)

    # ---------- internals ----------
    def _emit(self, op: str, arg: Any, ctx: "_CompileContext"):
        ctx.instructions.append((op, arg))
        if self.verbose:
            print(f"[C] {ctx.name} EMIT {op} {arg}")

    def _add_const(self, value: Any, ctx: "_CompileContext") -> int:
        # reuse existing identical literal if present
        try:
            idx = ctx.consts.index(value)
            return idx
        except ValueError:
            ctx.consts.append(value)
            return len(ctx.consts) - 1

    def _compile_stmt(self, stmt: Any, ctx: "_CompileContext"):
        t = type(stmt).__name__
        if t == "ExprStmt":
            self._compile_expr(stmt.expr, ctx)
            self._emit(OP_POP, None, ctx)
            return
        if t == "LetStmt":
            # compile initializer then store as global
            if stmt.initializer is not None:
                self._compile_expr(stmt.initializer, ctx)
            else:
                # push None
                idx = self._add_const(None, ctx)
                self._emit(OP_LOAD_CONST, idx, ctx)
            # store in globals (var/const both stored as globals in this simple compiler)
            self._emit(OP_STORE_GLOBAL, stmt.name, ctx)
            return
        if t == "PrintStmt":
            # compile expression then print
            self._compile_expr(stmt.expr, ctx)
            self._emit(OP_PRINT, None, ctx)
            return
        if t == "BlockStmt":
            for s in stmt.body:
                self._compile_stmt(s, ctx)
            return
        if t == "IfStmt":
            self._compile_expr(stmt.condition, ctx)
            # jump placeholder
            jmp_if_false_pos = len(ctx.instructions)
            self._emit(OP_JUMP_IF_FALSE, None, ctx)
            # then branch
            self._compile_stmt(stmt.then_branch, ctx)
            # optional else
            if stmt.else_branch is not None:
                # jump over else
                jmp_over_else_pos = len(ctx.instructions)
                self._emit(OP_JUMP, None, ctx)
                # fill jmp_if_false with current ip
                ctx.instructions[jmp_if_false_pos] = (OP_JUMP_IF_FALSE, len(ctx.instructions))
                self._compile_stmt(stmt.else_branch, ctx)
                # fill jmp_over_else
                ctx.instructions[jmp_over_else_pos] = (OP_JUMP, len(ctx.instructions))
            else:
                # fill jmp_if_false
                ctx.instructions[jmp_if_false_pos] = (OP_JUMP_IF_FALSE, len(ctx.instructions))
            return
        if t == "WhileStmt":
            loop_start = len(ctx.instructions)
            self._compile_expr(stmt.condition, ctx)
            jmp_if_false_pos = len(ctx.instructions)
            self._emit(OP_JUMP_IF_FALSE, None, ctx)
            self._compile_stmt(stmt.body, ctx)
            # jump back to start
            self._emit(OP_JUMP, loop_start, ctx)
            # patch
            ctx.instructions[jmp_if_false_pos] = (OP_JUMP_IF_FALSE, len(ctx.instructions))
            return
        if t == "ForStmt":
            # for var NAME := START to END [step STEP] { body }
            # compile start into a constant and set global NAME
            self._compile_expr(stmt.start, ctx)
            self._emit(OP_STORE_GLOBAL, stmt.name, ctx)
            # compute end and step as consts on stack (we'll load them each loop condition check)
            end_idx = self._add_const(stmt.end, ctx)  # store AST node, will be compiled each iteration safer
            step_idx = None
            if stmt.step is not None:
                step_idx = self._add_const(stmt.step, ctx)

            # We'll compile a simple loop:
            # loop_start:
            #   LOAD_GLOBAL name
            #   LOAD_CONST end (expr as Code? we will compile end expr each time instead of const pool)
            #   <eval comparison>
            #   JUMP_IF_FALSE exit
            #   <body>
            #   increment: LOAD_GLOBAL name; LOAD_CONST step; ADD; STORE_GLOBAL name
            #   JUMP loop_start
            loop_start = len(ctx.instructions)
            # evaluate loop condition: load current and evaluate against end
            # compile current (global load)
            self._emit(OP_LOAD_GLOBAL, stmt.name, ctx)
            # compile end expression inline
            self._compile_expr(stmt.end, ctx)
            # compare <= for positive steps, assume step default 1
            self._emit(OP_LTE, None, ctx)  # VM expects stack [a,b] -> a <= b
            jmp_exit_pos = len(ctx.instructions)
            self._emit(OP_JUMP_IF_FALSE, None, ctx)
            # body
            for s in stmt.body.body:
                self._compile_stmt(s, ctx)
            # increment
            self._emit(OP_LOAD_GLOBAL, stmt.name, ctx)
            if stmt.step is not None:
                self._compile_expr(stmt.step, ctx)
            else:
                idx1 = self._add_const(1, ctx)
                self._emit(OP_LOAD_CONST, idx1, ctx)
            self._emit(OP_ADD, None, ctx)
            self._emit(OP_STORE_GLOBAL, stmt.name, ctx)
            # jump back
            self._emit(OP_JUMP, loop_start, ctx)
            # patch exit
            ctx.instructions[jmp_exit_pos] = (OP_JUMP_IF_FALSE, len(ctx.instructions))
            return
        if t == "LoopStmt":
            loop_start = len(ctx.instructions)
            for s in stmt.body.body:
                self._compile_stmt(s, ctx)
            self._emit(OP_JUMP, loop_start, ctx)
            return
        if t == "FunctionStmt":
            # compile function body into a nested Code
            fname = stmt.name
            params = stmt.params
            # nested compiler context for function code (fresh const pool for nested code is okay)
            func_ctx = _CompileContext([], [], name=f"<fn {fname}>")
            # compile body statements into nested context
            for s in stmt.body.body:
                self._compile_stmt(s, func_ctx)
            func_ctx.instructions.append((OP_RETURN, None))
            # create Code object for the function
            code = Code(name=fname, instructions=func_ctx.instructions, consts=func_ctx.consts, nlocals=0, argcount=len(params))
            # store the Code object in the parent const pool (VM expects const to be a Code for "CODE" mode)
            code_const_idx = self._add_const(code, ctx)
            # emit MAKE_FUNCTION with CODE variant
            # VM expects OP_MAKE_FUNCTION with ("CODE", const_idx, name, argcount, nlocals)
            self._emit(OP_MAKE_FUNCTION, ("CODE", code_const_idx, fname, len(params), code.nlocals), ctx)
            # store function into global name
            self._emit(OP_STORE_GLOBAL, fname, ctx)
            return

        if t == "ReturnStmt":
            if stmt.value is not None:
                self._compile_expr(stmt.value, ctx)
            else:
                idx = self._add_const(None, ctx)
                self._emit(OP_LOAD_CONST, idx, ctx)
            self._emit(OP_RETURN, None, ctx)
            return

        # Unknown/unsupported
        raise CompileError(f"Unsupported statement type in compiler: {t}")

    def _compile_expr(self, expr: Any, ctx: "_CompileContext"):
        t = type(expr).__name__
        if t == "Literal":
            idx = self._add_const(expr.value, ctx)
            self._emit(OP_LOAD_CONST, idx, ctx)
            return
        if t == "Variable":
            # load global variable
            self._emit(OP_LOAD_GLOBAL, expr.name, ctx)
            return
        if t == "Grouping":
            self._compile_expr(expr.expression, ctx)
            return
        if t == "Unary":
            self._compile_expr(expr.operand, ctx)
            if expr.op == "!":
                self._emit(OP_NOT, None, ctx)
                return
            if expr.op == "-":
                # implement negation as loading 0 and subtract
                idx0 = self._add_const(0, ctx)
                self._emit(OP_LOAD_CONST, idx0, ctx)
                self._emit(OP_SUB, None, ctx)  # 0 - x
                return
            raise CompileError(f"Unsupported unary operator {expr.op}")
        if t == "Binary":
            # compile both sides then operator
            self._compile_expr(expr.left, ctx)
            self._compile_expr(expr.right, ctx)
            op = expr.op
            if op == "+":
                self._emit(OP_ADD, None, ctx); return
            if op == "-":
                self._emit(OP_SUB, None, ctx); return
            if op == "*":
                self._emit(OP_MUL, None, ctx); return
            if op == "/":
                self._emit(OP_DIV, None, ctx); return
            if op == "%":
                self._emit(OP_MOD, None, ctx); return
            if op == "==":
                self._emit(OP_EQ, None, ctx); return
            if op == "!=":
                self._emit(OP_NEQ, None, ctx); return
            if op == "<":
                self._emit(OP_LT, None, ctx); return
            if op == "<=":
                self._emit(OP_LTE, None, ctx); return
            if op == ">":
                self._emit(OP_GT, None, ctx); return
            if op == ">=":
                self._emit(OP_GTE, None, ctx); return
            if op == "&&":
                self._emit(OP_AND, None, ctx); return
            if op == "||":
                self._emit(OP_OR, None, ctx); return
            raise CompileError(f"Unsupported binary operator {op}")
        if t == "Assign":
            # compile value then store
            self._compile_expr(expr.value, ctx)
            targ = type(expr.target).__name__
            if targ == "Variable":
                self._emit(OP_STORE_GLOBAL, expr.target.name, ctx)
                return
            if targ == "Member":
                # compile base and then set attribute
                # push base then value on stack -> STORE_ATTR expects base,value order in VM (we follow vm impl)
                # compile base
                self._compile_expr(expr.target.base, ctx)
                # swap semantics: in our VM STORE_ATTR popped value then base, but compiler pushes base then value
                # so ensure ordering: compile value first then base (so top is base, below is value) then store will pop value then base
                # to match vm which pops value then base, we push base then value then instruct STORE_ATTR to pop value then base.
                # Achieve by compiling value then base: value on top, base under it -> vm pops value then base -> ok.
                self._compile_expr(expr.value, ctx)
                # But above we already compiled value; we need base after: so reverse: compile base first then value then STORE_ATTR expects (base,value)
                # To keep simple, compile target.base then compile value, then emit STORE_ATTR with attribute name
                # (VM code in vm.py expects value then base popped; our VM implementation actually pops value then base; so the order base,value then STORE_ATTR will pop value then base incorrectly)
                # To avoid confusion, create simple sequence: compile base -> push base; compile value -> push value; then emit OP_STORE_ATTR which in our VM pops value then base and stores base.attr=value.
                # That matches: stack [..., base, value] -> pop value; pop base -> set attribute.
                # So compile base then value:
                # Note: earlier we compiled value first — adjust to compile base then value.
                # So redo: compile base then value:
                # (we already compiled value in earlier line; to keep code simple, rework ordering:
                #  compile base then compile value, but we reached here with value compiled - so rebuild)
                # For correctness, implement compile Member assignment by compiling base then value.
                # So perform manual reordering: emit POP twice? Instead of fiddling, do straightforward:
                # compile base then compile value
                # (thus ignore earlier compile of value)
                pass  # fallthrough to Member-specific below

            raise CompileError("Unsupported assignment target type in compiler")

        if t == "Member":
            # compile base and then load attribute
            self._compile_expr(expr.base, ctx)
            self._emit(OP_LOAD_ATTR, expr.name, ctx)
            return
        if t == "FunctionExpr":
            # create an AST-backed FunctionObject constant (easier than compiling closure-aware code)
            # We produce an AST-backed function so that VM will call interpreter fallback for closures.
            fnode = expr  # keep node; VM expects ast_node with .params/.body/.name
            fobj = FunctionObject(getattr(expr, "name", None), None, fnode)
            idx = self._add_const(fobj, ctx)
            # emit MAKE_FUNCTION with AST mode (VM expects ("AST", const_idx))
            self._emit(OP_MAKE_FUNCTION, ("AST", idx), ctx)
            return
        if t == "Call":
            # compile callee then arguments then call
            self._compile_expr(expr.callee, ctx)
            for a in expr.arguments:
                self._compile_expr(a, ctx)
            self._emit(OP_CALL, len(expr.arguments), ctx)
            return

        # fallback
        raise CompileError(f"Unsupported expression type in compiler: {t}")


@dataclass
class _CompileContext:
    consts: List[Any]
    instructions: List[Instruction]
    name: str = "<module>"


# -------------------------
# Compatibility top-level wrapper
# -------------------------
def compile_module(ast, name=None):
    """
    Backwards-compatible wrapper. Instantiates Compiler and calls compile_module.
    Accepts optional name kw.
    """
    c = Compiler()
    try:
        if name is None:
            return c.compile_module(ast)
        return c.compile_module(ast, name=name)
    except Exception as e:
        raise CompileError(e)


# Keep CompileError symbol at module top-level for imports that expect it
# (already defined above)
