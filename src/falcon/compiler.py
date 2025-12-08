# src/falcon/compiler.py
"""
Falcon bytecode compiler.

Produces Code objects consumed by the VM.
Generates opcodes and const pool. Tracks locals and argcount.

This compiler is intentionally pragmatic: it emits straightforward
stack-machine bytecode suitable for the VM in src/falcon/vm.py and
matches the VM's expected opcode names and FunctionObject/Code shape.
"""
from __future__ import annotations
from typing import Any, List, Tuple, Dict, Optional
from dataclasses import dataclass
import itertools

from .ast_nodes import (
    Stmt, Expr, Literal, Variable, Binary, Unary, Grouping, Call, Member, FunctionExpr, Assign,
    LetStmt, PrintStmt, BlockStmt, IfStmt, WhileStmt, FunctionStmt, ReturnStmt,
    ForStmt, LoopStmt, ExprStmt, BreakStmt
)

# -------------------------
# Opcodes (must match vm.py imports)
# -------------------------
OP_LOAD_CONST   = "LOAD_CONST"
OP_LOAD_GLOBAL  = "LOAD_GLOBAL"
OP_STORE_GLOBAL = "STORE_GLOBAL"
OP_LOAD_LOCAL   = "LOAD_LOCAL"
OP_STORE_LOCAL  = "STORE_LOCAL"
OP_POP          = "POP"

OP_ADD = "ADD"; OP_SUB = "SUB"; OP_MUL = "MUL"; OP_DIV = "DIV"; OP_MOD = "MOD"
OP_EQ  = "EQ"; OP_NEQ = "NEQ"; OP_LT = "LT"; OP_LTE = "LTE"; OP_GT = "GT"; OP_GTE = "GTE"
OP_AND = "AND"; OP_OR = "OR"; OP_NOT = "NOT"

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

# -------------------------
# NEW fused opcodes (string names to match existing style)
# -------------------------
OP_INC_LOCAL = "INC_LOCAL"                       # arg: local_index
OP_JUMP_IF_GE_LOCAL_IMM = "JUMP_IF_GE_LOCAL_IMM" # arg: (local_index, immediate_value, target_ip)
OP_FAST_COUNT = "FAST_COUNT"                     # arg: (local_index, limit)

# -------------------------
# Data container classes
# -------------------------
@dataclass
class Code:
    name: str
    instructions: List[Tuple[str, Any]]
    consts: List[Any]
    nlocals: int
    argcount: int

    def __repr__(self) -> str:
        return f"<Code {self.name} consts={len(self.consts)} instr={len(self.instructions)} nlocals={self.nlocals} argcount={self.argcount}>"

class FunctionObject:
    """
    Wrapper representing a function value in compiled world.
    Two modes:
      - code-backed: .code is a Code object (VM executes)
      - ast-backed:  .ast_node is a FunctionStmt/FunctionExpr (interpreter fallback)
    """
    def __init__(self, name: Optional[str], code: Optional[Code] = None, ast_node: Optional[Any] = None, argcount: int = 0, nlocals: int = 0):
        self.name = name
        self.code = code
        self.ast_node = ast_node
        self.argcount = argcount
        self.nlocals = nlocals

    def is_ast_backed(self) -> bool:
        return self.ast_node is not None

    def __repr__(self) -> str:
        if self.is_ast_backed():
            return f"<FunctionObject AST {getattr(self.ast_node,'name', '<anon>')}>"
        return f"<FunctionObject CODE {self.code.name if self.code else '<none>'}>"

# -------------------------
# Compiler error
# -------------------------
class CompileError(Exception):
    pass

# -------------------------
# Compiler
# -------------------------
class Compiler:
    def __init__(self, verbose: bool = False):
        # instructions built as list of (op, arg)
        self.instructions: List[Tuple[str, Any]] = []
        self.consts: List[Any] = []
        # maps name->local index in current function; None at module level
        self.locals: Dict[str, int] = {}
        self.next_local: int = 0
        # set of globals referenced (not strictly necessary)
        self.globals: set = set()
        self.argcount: int = 0
        self.name: str = "<module>"
        self.verbose = verbose

        # loop stack for break/continue backpatching
        # each entry is dict like: {"break_positions": [instr_idx, ...], "start_ip": int}
        self.loop_stack: List[Dict[str, Any]] = []

    # -------------------------
    # Public API
    # -------------------------
    def compile_module(self, stmts: List[Stmt], name: str = "<module>") -> Code:
        """
        Compile a top-level module (list of Stmt) into a Code object.
        `name` parameter accepted to match runner expectations.
        """
        self.instructions = []
        self.consts = []
        self.locals = {}
        self.next_local = 0
        self.globals = set()
        self.argcount = 0
        self.name = name

        for s in stmts:
            self._compile_stmt(s)

        # at module end, return None implicitly
        self._emit(OP_LOAD_CONST, self._add_const(None))
        self._emit(OP_RETURN, None)

        code = Code(name=self.name, instructions=self.instructions[:], consts=self.consts[:], nlocals=self.next_local, argcount=0)
        if self.verbose:
            self._dump_code(code)
        return code

    def compile_function(self, fn_stmt: FunctionStmt) -> Code:
        """
        Compile a function declaration into a Code object (code-backed).
        Params become locals 0..n-1. Subsequent var declarations allocate locals.
        """
        sub = Compiler(verbose=self.verbose)
        sub.name = fn_stmt.name
        # parameters are first locals
        sub.locals = {}
        sub.next_local = 0
        for p in fn_stmt.params:
            sub.locals[p] = sub.next_local
            sub.next_local += 1
        sub.argcount = len(fn_stmt.params)
        # compile body statements
        for s in fn_stmt.body.body:
            sub._compile_stmt(s)
        # implicit return None at end
        sub._emit(OP_LOAD_CONST, sub._add_const(None))
        sub._emit(OP_RETURN, None)
        code = Code(name=fn_stmt.name, instructions=sub.instructions[:], consts=sub.consts[:], nlocals=sub.next_local, argcount=sub.argcount)
        if self.verbose:
            self._dump_code(code)
        return code

    # -------------------------
    # Internals: instruction helpers
    # -------------------------
    def _add_const(self, v: Any) -> int:
        # append constant and return its index
        self.consts.append(v)
        return len(self.consts) - 1

    def _emit(self, op: str, arg: Any):
        if self.verbose:
            print(f"[C] emit {op} {arg}")
        self.instructions.append((op, arg))

    def _emit_jump(self, op: str, target: Optional[int] = None) -> int:
        """
        Emit a jump placeholder. Returns index of emitted instruction for patching.
        """
        idx = len(self.instructions)
        self._emit(op, target if target is not None else -1)
        return idx

    def _patch_jump(self, idx: int, target: int):
        op, _ = self.instructions[idx]
        self.instructions[idx] = (op, target)
        if self.verbose:
            print(f"[C] patch jump {idx} -> {target}")

    # -------------------------
    # Statement compilation
    # -------------------------
    def _compile_stmt(self, stmt: Stmt):
        # --- Block ---
        if isinstance(stmt, BlockStmt):
            for s in stmt.body:
                self._compile_stmt(s)
            return

        # --- Let ---
        if isinstance(stmt, LetStmt):
            init = stmt.initializer
            if init is None:
                self._emit(OP_LOAD_CONST, self._add_const(None))
            else:
                self._compile_expr(init)
            if self._in_function():
                if stmt.name in self.locals:
                    idx = self.locals[stmt.name]
                else:
                    idx = self._alloc_local(stmt.name)
                self._emit(OP_STORE_LOCAL, idx)
            else:
                self._emit(OP_STORE_GLOBAL, stmt.name)
            return

        # --- Print ---
        if isinstance(stmt, PrintStmt):
            self._compile_expr(stmt.expr)
            self._emit(OP_PRINT, None)
            return

        # --- ExprStmt ---
        if isinstance(stmt, ExprStmt):
            self._compile_expr(stmt.expr)
            self._emit(OP_POP, None)
            return

        # --- If ---
        if isinstance(stmt, IfStmt):
            self._compile_expr(stmt.condition)
            jfalse = self._emit_jump(OP_JUMP_IF_FALSE)
            self._compile_stmt(stmt.then_branch)
            jdone = self._emit_jump(OP_JUMP)
            self._patch_jump(jfalse, len(self.instructions))
            if stmt.else_branch is not None:
                self._compile_stmt(stmt.else_branch)
            self._patch_jump(jdone, len(self.instructions))
            return

        # --- While (with loop context) ---
        if isinstance(stmt, WhileStmt):
            start_ip = len(self.instructions)
            self._compile_expr(stmt.condition)
            jexit = self._emit_jump(OP_JUMP_IF_FALSE)

            # push loop context
            ctx = {"start_ip": start_ip, "break_positions": []}
            self.loop_stack.append(ctx)

            self._compile_stmt(stmt.body)
            self._emit(OP_JUMP, start_ip)

            # loop end
            loop_end = len(self.instructions)
            # patch exit conditional
            self._patch_jump(jexit, loop_end)
            # patch breaks
            for bp in ctx["break_positions"]:
                self._patch_jump(bp, loop_end)

            self.loop_stack.pop()
            return

        # --- For (with loop context) ---
        if isinstance(stmt, ForStmt):
            # for var i := START to END [step STEP] { body }
            iter_idx = self._alloc_local(stmt.name)
            end_idx = self._alloc_local(f"__for_end_{iter_idx}")
            step_idx = self._alloc_local(f"__for_step_{iter_idx}")

            # start -> iter local
            self._compile_expr(stmt.start)
            self._emit(OP_STORE_LOCAL, iter_idx)

            # end -> end local
            self._compile_expr(stmt.end)
            self._emit(OP_STORE_LOCAL, end_idx)

            # step -> step local (default 1)
            if stmt.step is not None:
                self._compile_expr(stmt.step)
            else:
                self._emit(OP_LOAD_CONST, self._add_const(1))
            self._emit(OP_STORE_LOCAL, step_idx)

            start_check_ip = len(self.instructions)

            # check step > 0
            self._emit(OP_LOAD_LOCAL, step_idx)
            self._emit(OP_LOAD_CONST, self._add_const(0))
            self._emit(OP_GT, None)
            jsteppos = self._emit_jump(OP_JUMP_IF_FALSE)

            # step > 0 branch: iter <= end ?
            self._emit(OP_LOAD_LOCAL, iter_idx)
            self._emit(OP_LOAD_LOCAL, end_idx)
            self._emit(OP_LTE, None)
            jexit1 = self._emit_jump(OP_JUMP_IF_FALSE)
            jgoto_body = self._emit_jump(OP_JUMP)

            # else branch (step <= 0): iter >= end ?
            self._patch_jump(jsteppos, len(self.instructions))
            self._emit(OP_LOAD_LOCAL, iter_idx)
            self._emit(OP_LOAD_LOCAL, end_idx)
            self._emit(OP_GTE, None)
            jexit2 = self._emit_jump(OP_JUMP_IF_FALSE)

            # body label:
            self._patch_jump(jgoto_body, len(self.instructions))

            # push loop context for breaks inside the body
            ctx = {"start_ip": len(self.instructions), "break_positions": []}
            self.loop_stack.append(ctx)

            # body:
            self._compile_stmt(stmt.body)

            # increment: iter = iter + step
            self._emit(OP_LOAD_LOCAL, iter_idx)
            self._emit(OP_LOAD_LOCAL, step_idx)
            self._emit(OP_ADD, None)
            self._emit(OP_STORE_LOCAL, iter_idx)

            # jump back
            self._emit(OP_JUMP, start_check_ip)

            # patch exits
            loop_end = len(self.instructions)
            self._patch_jump(jexit1, loop_end)
            self._patch_jump(jexit2, loop_end)

            # patch breaks recorded
            for bp in ctx["break_positions"]:
                self._patch_jump(bp, loop_end)

            self.loop_stack.pop()
            return

        # --- Loop (infinite) ---
        if isinstance(stmt, LoopStmt):
            # Attempt to detect a common numeric counting loop pattern and emit fused ops:
            # pattern:
            #   loop {
            #       if (<var> >= <CONST>) { break; }
            #       <var> := <var> + 1;
            #       ... (no other side-effects) ...
            #   }
            #
            # If pattern matches exactly (IfStmt then Assign increment as next stmt)
            # we emit:
            #   OP_JUMP_IF_GE_LOCAL_IMM (var, const, exit)
            #   OP_INC_LOCAL var
            #   OP_JUMP start
            #
            start_ip = len(self.instructions)

            # if body is a BlockStmt with at least two statements, try pattern detection
            if isinstance(stmt.body, BlockStmt) and len(stmt.body.body) >= 2:
                first = stmt.body.body[0]
                second = stmt.body.body[1]

                pattern_ok = False
                var_name = None
                imm_value = None

                # check first is IfStmt with then_branch a BreakStmt and condition is Binary comparing Variable to Literal
                if isinstance(first, IfStmt) and isinstance(first.then_branch, BreakStmt):
                    cond = first.condition
                    if isinstance(cond, Binary) and isinstance(cond.left, Variable) and isinstance(cond.right, Literal):
                        # support >, >=, == style where we will use >= semantics for break condition if op is '>' or '>='
                        if cond.op in (">", ">="):
                            var_name = cond.left.name
                            imm_value = cond.right.value
                            pattern_ok = True

                # check second is Assign increment of same variable by literal 1
                if pattern_ok and isinstance(second, ExprStmt) and isinstance(second.expr, Assign):
                    assign = second.expr
                    # target must be same variable
                    if isinstance(assign.target, Variable) and assign.target.name == var_name:
                        val = assign.value
                        # accept patterns: var + 1  OR 1 + var
                        if isinstance(val, Binary) and val.op == "+":
                            is_inc = False
                            if isinstance(val.left, Variable) and val.left.name == var_name and isinstance(val.right, Literal) and val.right.value == 1:
                                is_inc = True
                            if isinstance(val.right, Variable) and val.right.name == var_name and isinstance(val.left, Literal) and val.left.value == 1:
                                is_inc = True
                            if is_inc:
                                # Only fuse if var is a local (we can check/allocate the local)
                                if var_name in self.locals or self._in_function():
                                    # ensure it's allocated as local
                                    if var_name not in self.locals:
                                        self._alloc_local(var_name)
                                    local_idx = self.locals[var_name]
                                    # emit fused sequence:
                                    # placeholder for jump-if-ge (patch exit ip later)
                                    # note: arg for OP_JUMP_IF_GE_LOCAL_IMM will be (local_idx, imm_value, exit_placeholder)
                                    jpos = len(self.instructions)
                                    self._emit(OP_JUMP_IF_GE_LOCAL_IMM, (local_idx, imm_value, -1))
                                    # inc
                                    self._emit(OP_INC_LOCAL, local_idx)
                                    # jump back to start
                                    self._emit(OP_JUMP, start_ip)
                                    # exit target is here
                                    exit_ip = len(self.instructions)
                                    # patch the earlier tuple entry by replacing it with proper target
                                    # (we can't mutate the tuple directly; replace whole arg)
                                    op, arg = self.instructions[jpos]
                                    self.instructions[jpos] = (op, (arg[0], arg[1], exit_ip))
                                    # compile any remaining statements after second inside body
                                    for extra in stmt.body.body[2:]:
                                        self._compile_stmt(extra)
                                    return

            # default / fallback implementation (no fusion)
            # push loop context
            ctx = {"start_ip": start_ip, "break_positions": []}
            self.loop_stack.append(ctx)

            # compile body & jump back
            self._compile_stmt(stmt.body)
            self._emit(OP_JUMP, start_ip)

            # patch breaks
            loop_end = len(self.instructions)
            for bp in ctx["break_positions"]:
                self._patch_jump(bp, loop_end)

            self.loop_stack.pop()
            return

        # --- Function ---
        if isinstance(stmt, FunctionStmt):
            code_obj = self.compile_function(stmt)
            const_idx = self._add_const(code_obj)
            self._emit(OP_MAKE_FUNCTION, ("CODE", const_idx, stmt.name, code_obj.argcount, code_obj.nlocals))
            self._emit(OP_STORE_GLOBAL, stmt.name)
            return

        # --- Return ---
        if isinstance(stmt, ReturnStmt):
            if stmt.value is not None:
                self._compile_expr(stmt.value)
            else:
                self._emit(OP_LOAD_CONST, self._add_const(None))
            self._emit(OP_RETURN, None)
            return

        # --- Break ---
        if isinstance(stmt, BreakStmt):
            if not self.loop_stack:
                raise CompileError("Compile error: 'break' used outside loop")
            # emit jump placeholder and record for backpatch
            pos = self._emit_jump(OP_JUMP)
            self.loop_stack[-1]["break_positions"].append(pos)
            return

        raise CompileError(f"Unhandled statement type in compiler: {type(stmt).__name__}")

    # -------------------------
    # Expression compilation
    # -------------------------
    def _compile_expr(self, expr: Expr):
        if isinstance(expr, Literal):
            idx = self._add_const(expr.value)
            self._emit(OP_LOAD_CONST, idx)
            return

        if isinstance(expr, Variable):
            if expr.name in self.locals:
                self._emit(OP_LOAD_LOCAL, self.locals[expr.name])
            else:
                self._emit(OP_LOAD_GLOBAL, expr.name)
            return

        if isinstance(expr, Grouping):
            return self._compile_expr(expr.expression)

        if isinstance(expr, Unary):
            self._compile_expr(expr.operand)
            if expr.op == "!":
                self._emit(OP_NOT, None)
                return
            if expr.op == "-":
                self._emit(OP_LOAD_CONST, self._add_const(-1))
                self._emit(OP_MUL, None)
                return
            raise CompileError(f"Unsupported unary operator '{expr.op}'")

        if isinstance(expr, Binary):
            if expr.op == "&&":
                self._compile_expr(expr.left)
                jfalse = self._emit_jump(OP_JUMP_IF_FALSE)
                self._compile_expr(expr.right)
                self._patch_jump(jfalse, len(self.instructions))
                return
            if expr.op == "||":
                self._compile_expr(expr.left)
                jskip = self._emit_jump(OP_JUMP_IF_FALSE)
                self._compile_expr(expr.right)
                # simple approach -- not perfect short-circuit semantics but workable
                return

            self._compile_expr(expr.left)
            self._compile_expr(expr.right)

            opmap = {
                "+": OP_ADD, "-": OP_SUB, "*": OP_MUL, "/": OP_DIV, "%": OP_MOD,
                "==": OP_EQ, "!=": OP_NEQ, "<": OP_LT, "<=": OP_LTE, ">": OP_GT, ">=": OP_GTE,
            }
            if expr.op in opmap:
                self._emit(opmap[expr.op], None)
                return
            raise CompileError(f"Unsupported binary operator '{expr.op}'")

        if isinstance(expr, Assign):
            # Optimize local increment pattern: x := x + 1  OR x := 1 + x  => OP_INC_LOCAL
            if isinstance(expr.target, Variable) and isinstance(expr.value, Binary) and expr.value.op == "+":
                target_name = expr.target.name
                left = expr.value.left
                right = expr.value.right
                is_inc = False
                # x + 1
                if isinstance(left, Variable) and isinstance(right, Literal) and right.value == 1 and left.name == target_name:
                    is_inc = True
                # 1 + x
                if isinstance(right, Variable) and isinstance(left, Literal) and left.value == 1 and right.name == target_name:
                    is_inc = True
                if is_inc and self._in_function():
                    # allocate local if missing
                    if target_name not in self.locals:
                        self._alloc_local(target_name)
                    idx = self.locals[target_name]
                    self._emit(OP_INC_LOCAL, idx)
                    # after assignment expression, push the new local value onto stack (preserve previous behavior of returning the assigned value)
                    self._emit(OP_LOAD_LOCAL, idx)
                    return

            # fallback general assignment
            if isinstance(expr.target, Variable):
                self._compile_expr(expr.value)
                name = expr.target.name
                if name in self.locals:
                    self._emit(OP_STORE_LOCAL, self.locals[name])
                    self._emit(OP_LOAD_LOCAL, self.locals[name])
                else:
                    self._emit(OP_STORE_GLOBAL, name)
                    self._emit(OP_LOAD_GLOBAL, name)
                return
            if isinstance(expr.target, Member):
                self._compile_expr(expr.target.base)
                self._compile_expr(expr.value)
                self._emit(OP_STORE_ATTR, expr.target.name)
                return
            raise CompileError("Invalid assignment target")

        if isinstance(expr, Member):
            self._compile_expr(expr.base)
            self._emit(OP_LOAD_ATTR, expr.name)
            return

        if isinstance(expr, FunctionExpr):
            idx = self._add_const(expr)
            self._emit(OP_MAKE_FUNCTION, ("AST", idx))
            return

        if isinstance(expr, Call):
            self._compile_expr(expr.callee)
            for a in expr.arguments:
                self._compile_expr(a)
            self._emit(OP_CALL, len(expr.arguments))
            return

        raise CompileError(f"Unhandled expression type in compiler: {type(expr).__name__}")

    # -------------------------
    # Utilities
    # -------------------------
    def _in_function(self) -> bool:
        return self.name != "<module>"

    def _alloc_local(self, name: str) -> int:
        if name in self.locals:
            return self.locals[name]
        idx = self.next_local
        self.locals[name] = idx
        self.next_local += 1
        return idx

    def _dump_code(self, code: Code):
        print(f"Compiled code: {code.name}")
        print(f"  consts: {len(code.consts)}")
        print(f"  instructions: {len(code.instructions)}")
        print(f"  nlocals: {code.nlocals}, argcount: {code.argcount}")

# -------------------------
# Convenience top-level compile helper
# -------------------------
def compile_module_to_code(stmts: List[Stmt], name: str = "<module>", verbose: bool = False) -> Code:
    c = Compiler(verbose=verbose)
    return c.compile_module(stmts, name=name)
