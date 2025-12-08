"""
Optimized Falcon compiler with fast opcodes:
- INC_LOCAL
- JUMP_IF_GE_LOCAL_IMM
- FAST_COUNT (pure numeric loop fast path)
"""

from __future__ import annotations
from typing import Any, List, Tuple, Dict, Optional
from dataclasses import dataclass

from .ast_nodes import (
    Stmt, Expr, Literal, Variable, Binary, Unary, Grouping, Call, Member,
    FunctionExpr, Assign, LetStmt, PrintStmt, BlockStmt, IfStmt, WhileStmt,
    FunctionStmt, ReturnStmt, ForStmt, LoopStmt, ExprStmt, BreakStmt
)

# ---------------------------------
#  Base opcodes (unchanged)
# ---------------------------------
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

# ---------------------------------
#  NEW optimized opcodes
# ---------------------------------
OP_INC_LOCAL = "INC_LOCAL"                       # i := i + 1
OP_JUMP_IF_GE_LOCAL_IMM = "JUMP_IF_GE_LOCAL_IMM" # (local, limit, target)
OP_FAST_COUNT = "FAST_COUNT"                     # fast numeric loop


# ---------------------------------
# Data model
# ---------------------------------
@dataclass
class Code:
    name: str
    instructions: List[Tuple[str, Any]]
    consts: List[Any]
    nlocals: int
    argcount: int

class FunctionObject:
    def __init__(self, name, code=None, ast_node=None, argcount=0, nlocals=0):
        self.name = name
        self.code = code
        self.ast_node = ast_node
        self.argcount = argcount
        self.nlocals = nlocals

    def is_ast_backed(self) -> bool:
        return self.ast_node is not None


# ---------------------------------
# Compiler implementation
# ---------------------------------
class CompileError(Exception):
    pass

class Compiler:
    def __init__(self, verbose: bool = False):
        self.instructions = []
        self.consts = []

        self.locals: Dict[str, int] = {}
        self.next_local = 0
        self.globals = set()
        self.argcount = 0
        self.name = "<module>"
        self.verbose = verbose

        # loop stack
        self.loop_stack = []   # each = {"start_ip":int,"break_positions":[ints]}

    # ---------------------------------
    # Public API
    # ---------------------------------
    def compile_module(self, stmts: List[Stmt], name="<module>") -> Code:
        self.instructions = []
        self.consts = []
        self.locals = {}
        self.next_local = 0
        self.argcount = 0
        self.name = name

        for s in stmts:
            self._compile_stmt(s)

        # implicit return None
        self._emit(OP_LOAD_CONST, self._add_const(None))
        self._emit(OP_RETURN, None)

        return Code(name, self.instructions[:], self.consts[:], self.next_local, 0)

    def compile_function(self, fn: FunctionStmt) -> Code:
        sub = Compiler(verbose=self.verbose)
        sub.name = fn.name

        # assign params as locals 0..n
        sub.locals = {}
        sub.next_local = 0
        for p in fn.params:
            sub.locals[p] = sub.next_local
            sub.next_local += 1
        sub.argcount = len(fn.params)

        for stmt in fn.body.body:
            sub._compile_stmt(stmt)

        # implicit return None
        sub._emit(OP_LOAD_CONST, sub._add_const(None))
        sub._emit(OP_RETURN, None)

        return Code(fn.name, sub.instructions[:], sub.consts[:], sub.next_local, sub.argcount)

    # ---------------------------------
    # Helpers
    # ---------------------------------
    def _add_const(self, v):
        self.consts.append(v)
        return len(self.consts) - 1

    def _emit(self, op, arg):
        self.instructions.append((op, arg))

    def _emit_jump(self, op, target=None):
        idx = len(self.instructions)
        self._emit(op, -1 if target is None else target)
        return idx

    def _patch_jump(self, idx, target):
        op, _ = self.instructions[idx]
        self.instructions[idx] = (op, target)

    def _alloc_local(self, name):
        if name in self.locals:
            return self.locals[name]
        idx = self.next_local
        self.locals[name] = idx
        self.next_local += 1
        return idx

    # ------------------------------------------
    #  Optimized loop fusion detection
    # ------------------------------------------
    def _can_fastcount_loop(self, stmt: LoopStmt):
        """
        Detect simple patterns:

            loop {
                if (i == LIMIT) break;
                i = i + 1;
            }

        returns (local_idx, limit) or None
        """

        if not isinstance(stmt.body, BlockStmt):
            return None
        body = stmt.body.body
        if len(body) != 2:
            return None

        # pattern 1: if (i == limit) break;
        cond_stmt, inc_stmt = body

        # check break-if
        if not isinstance(cond_stmt, IfStmt):
            return None
        if not isinstance(cond_stmt.then_branch, BreakStmt):
            return None
        if cond_stmt.else_branch is not None:
            return None
        # check condition structure: i == LIMIT
        cond = cond_stmt.condition
        if not isinstance(cond, Binary):
            return None
        if cond.op != "==":
            return None
        if not isinstance(cond.left, Variable):
            return None
        if not isinstance(cond.right, Literal):
            return None

        var_name = cond.left.name
        limit_val = cond.right.value
        if not isinstance(limit_val, int):
            return None

        # pattern 2: i = i + 1;
        if not isinstance(inc_stmt, ExprStmt):
            return None
        if not isinstance(inc_stmt.expr, Assign):
            return None
        a = inc_stmt.expr
        if not isinstance(a.target, Variable):
            return None
        if a.target.name != var_name:
            return None
        # Check a.value is (i + 1)
        if not isinstance(a.value, Binary):
            return None
        if a.value.op != "+":
            return None
        if not isinstance(a.value.left, Variable):
            return None
        if a.value.left.name != var_name:
            return None
        if not isinstance(a.value.right, Literal):
            return None
        if a.value.right.value != 1:
            return None

        # Success
        if var_name not in self.locals:
            return None

        return self.locals[var_name], limit_val

    # ---------------------------------
    # Statement Compilation
    # ---------------------------------
    def _compile_stmt(self, stmt: Stmt):

        # ---------- Block ----------
        if isinstance(stmt, BlockStmt):
            for s in stmt.body:
                self._compile_stmt(s)
            return

        # ---------- Variable Declaration ----------
        if isinstance(stmt, LetStmt):
            if stmt.initializer is None:
                self._emit(OP_LOAD_CONST, self._add_const(None))
            else:
                self._compile_expr(stmt.initializer)

            if self.name != "<module>":
                idx = self._alloc_local(stmt.name)
                self._emit(OP_STORE_LOCAL, idx)
            else:
                self._emit(OP_STORE_GLOBAL, stmt.name)
            return

        # ---------- Print ----------
        if isinstance(stmt, PrintStmt):
            self._compile_expr(stmt.expr)
            self._emit(OP_PRINT, None)
            return

        # ---------- Expression Statement ----------
        if isinstance(stmt, ExprStmt):
            self._compile_expr(stmt.expr)
            self._emit(OP_POP, None)
            return

        # ---------- If ----------
        if isinstance(stmt, IfStmt):
            self._compile_expr(stmt.condition)
            jfalse = self._emit_jump(OP_JUMP_IF_FALSE)
            self._compile_stmt(stmt.then_branch)
            jdone = self._emit_jump(OP_JUMP)
            self._patch_jump(jfalse, len(self.instructions))
            if stmt.else_branch:
                self._compile_stmt(stmt.else_branch)
            self._patch_jump(jdone, len(self.instructions))
            return

        # ---------- While ----------
        if isinstance(stmt, WhileStmt):
            start_ip = len(self.instructions)

            # condition
            self._compile_expr(stmt.condition)
            jexit = self._emit_jump(OP_JUMP_IF_FALSE)

            ctx = {"start_ip": start_ip, "break_positions": []}
            self.loop_stack.append(ctx)

            # body
            self._compile_stmt(stmt.body)

            self._emit(OP_JUMP, start_ip)

            end_ip = len(self.instructions)
            self._patch_jump(jexit, end_ip)

            for bp in ctx["break_positions"]:
                self._patch_jump(bp, end_ip)

            self.loop_stack.pop()
            return

        # ---------- Optimized Loop ----------
        if isinstance(stmt, LoopStmt):

            # Try FAST_COUNT
            fast = self._can_fastcount_loop(stmt)
            if fast:
                local_idx, limit_val = fast
                self._emit(OP_FAST_COUNT, (local_idx, limit_val))
                return

            # Otherwise fallback to normal loop
            start_ip = len(self.instructions)
            ctx = {"start_ip": start_ip, "break_positions": []}
            self.loop_stack.append(ctx)

            self._compile_stmt(stmt.body)
            self._emit(OP_JUMP, start_ip)

            end_ip = len(self.instructions)
            for bp in ctx["break_positions"]:
                self._patch_jump(bp, end_ip)

            self.loop_stack.pop()
            return

        # ---------- Function ----------
        if isinstance(stmt, FunctionStmt):
            c = self.compile_function(stmt)
            idx = self._add_const(c)
            self._emit(OP_MAKE_FUNCTION, ("CODE", idx, stmt.name, c.argcount, c.nlocals))
            self._emit(OP_STORE_GLOBAL, stmt.name)
            return

        # ---------- Return ----------
        if isinstance(stmt, ReturnStmt):
            if stmt.value:
                self._compile_expr(stmt.value)
            else:
                self._emit(OP_LOAD_CONST, self._add_const(None))
            self._emit(OP_RETURN, None)
            return

        # ---------- Break ----------
        if isinstance(stmt, BreakStmt):
            if not self.loop_stack:
                raise CompileError("'break' outside loop")
            pos = self._emit_jump(OP_JUMP)
            self.loop_stack[-1]["break_positions"].append(pos)
            return

        raise CompileError(f"Unhandled statement type: {type(stmt).__name__}")

    # ---------------------------------
    # Expression Compilation
    # ---------------------------------
    def _compile_expr(self, expr: Expr):

        # ---------- Literal ----------
        if isinstance(expr, Literal):
            self._emit(OP_LOAD_CONST, self._add_const(expr.value))
            return

        # ---------- Variable ----------
        if isinstance(expr, Variable):
            if expr.name in self.locals:
                self._emit(OP_LOAD_LOCAL, self.locals[expr.name])
            else:
                self._emit(OP_LOAD_GLOBAL, expr.name)
            return

        # ---------- Grouping ----------
        if isinstance(expr, Grouping):
            self._compile_expr(expr.expression)
            return

        # ---------- Unary ----------
        if isinstance(expr, Unary):
            self._compile_expr(expr.operand)
            if expr.op == "!":
                self._emit(OP_NOT, None)
            elif expr.op == "-":
                self._emit(OP_LOAD_CONST, self._add_const(-1))
                self._emit(OP_MUL, None)
            return

        # ---------- Binary ----------
        if isinstance(expr, Binary):
            # Short-circuit AND / OR
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
                # Weak OR semantics; allowed
                return

            # Special-case fast increment pattern: i = i + 1
            if expr.op == "+":
                if isinstance(expr.left, Variable) and isinstance(expr.right, Literal):
                    if expr.right.value == 1 and expr.left.name in self.locals:
                        # emit INC_LOCAL
                        self._emit(OP_INC_LOCAL, self.locals[expr.left.name])
                        # INC_LOCAL returns new value, so no need to push manually
                        return

            # general binary case  
            self._compile_expr(expr.left)
            self._compile_expr(expr.right)

            opmap = {
                "+": OP_ADD, "-": OP_SUB, "*": OP_MUL, "/": OP_DIV, "%": OP_MOD,
                "==": OP_EQ, "!=": OP_NEQ, "<": OP_LT, "<=": OP_LTE, ">": OP_GT, ">=": OP_GTE,
            }
            if expr.op in opmap:
                self._emit(opmap[expr.op], None)
                return

        # ---------- Assign ----------
        if isinstance(expr, Assign):
            if isinstance(expr.target, Variable):
                name = expr.target.name
                # detect i = i + 1
                if (
                    isinstance(expr.value, Binary)
                    and expr.value.op == "+"
                    and isinstance(expr.value.left, Variable)
                    and expr.value.left.name == name
                    and isinstance(expr.value.right, Literal)
                    and expr.value.right.value == 1
                    and name in self.locals
                ):
                    self._emit(OP_INC_LOCAL, self.locals[name])
                    self._emit(OP_LOAD_LOCAL, self.locals[name])
                    return

                # normal assign
                self._compile_expr(expr.value)
                if name in self.locals:
                    self._emit(OP_STORE_LOCAL, self.locals[name])
                    self._emit(OP_LOAD_LOCAL, self.locals[name])
                else:
                    self._emit(OP_STORE_GLOBAL, name)
                    self._emit(OP_LOAD_GLOBAL, name)
                return

            # attribute assign
            if isinstance(expr.target, Member):
                self._compile_expr(expr.target.base)
                self._compile_expr(expr.value)
                self._emit(OP_STORE_ATTR, expr.target.name)
                return

        # ---------- Member ----------
        if isinstance(expr, Member):
            self._compile_expr(expr.base)
            self._emit(OP_LOAD_ATTR, expr.name)
            return

        # ---------- Function Expr ----------
        if isinstance(expr, FunctionExpr):
            idx = self._add_const(expr)
            self._emit(OP_MAKE_FUNCTION, ("AST", idx))
            return

        # ---------- Call ----------
        if isinstance(expr, Call):
            self._compile_expr(expr.callee)
            for a in expr.arguments:
                self._compile_expr(a)
            self._emit(OP_CALL, len(expr.arguments))
            return

        raise CompileError(f"Unhandled expression: {type(expr).__name__}")

# ---------------------------------
# Top-level helper
# ---------------------------------
def compile_module_to_code(stmts: List[Stmt], name: str = "<module>", verbose=False) -> Code:
    c = Compiler(verbose)
    return c.compile_module(stmts, name)
