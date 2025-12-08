"""
Optimized Falcon compiler (integer opcodes version)
Includes:
- INC_LOCAL
- JUMP_IF_GE_LOCAL_IMM
- FAST_COUNT(local, limit, target)
"""

from __future__ import annotations
from typing import Any, List, Tuple, Dict
from dataclasses import dataclass

from .ast_nodes import (
    Stmt, Expr, Literal, Variable, Binary, Unary, Grouping, Call, Member,
    FunctionExpr, Assign, LetStmt, PrintStmt, BlockStmt, IfStmt, WhileStmt,
    FunctionStmt, ReturnStmt, ForStmt, LoopStmt, ExprStmt, BreakStmt
)

# -------------------------
# Opcode integer mapping
# -------------------------
OP_LOAD_CONST   = 1
OP_LOAD_GLOBAL  = 2
OP_STORE_GLOBAL = 3
OP_LOAD_LOCAL   = 4
OP_STORE_LOCAL  = 5
OP_POP          = 6

OP_ADD = 7
OP_SUB = 8
OP_MUL = 9
OP_DIV = 10
OP_MOD = 11

OP_EQ  = 12
OP_NEQ = 13
OP_LT = 14
OP_LTE = 15
OP_GT = 16
OP_GTE = 17

OP_AND = 18
OP_OR = 19
OP_NOT = 20

OP_JUMP = 21
OP_JUMP_IF_FALSE = 22
OP_CALL = 23
OP_RETURN = 24

OP_PRINT = 25
OP_MAKE_FUNCTION = 26
OP_LOAD_ATTR = 27
OP_STORE_ATTR = 28

OP_LOOP = 29
OP_NOP = 30

# Optimized opcodes
OP_INC_LOCAL = 31
OP_JUMP_IF_GE_LOCAL_IMM = 32
OP_FAST_COUNT = 33


# -------------------------
# Code object
# -------------------------
@dataclass
class Code:
    name: str
    instructions: List[Tuple[int, Any]]
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

    def is_ast_backed(self):
        return self.ast_node is not None


class CompileError(Exception):
    pass


# ==========================
# Compiler
# ==========================
class Compiler:

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.instructions = []
        self.consts = []
        self.locals: Dict[str, int] = {}
        self.next_local = 0
        self.argcount = 0
        self.name = "<module>"
        self.loop_stack = []

    # -------------
    # Public entry
    # -------------
    def compile_module(self, stmts: List[Stmt], name="<module>"):
        self.__init__(self.verbose)
        self.name = name

        for s in stmts:
            self._compile_stmt(s)

        self._emit(OP_LOAD_CONST, self._add_const(None))
        self._emit(OP_RETURN, None)

        return Code(name, self.instructions[:], self.consts[:], self.next_local, 0)

    # -------------
    # Helpers
    # -------------
    def _add_const(self, v):
        self.consts.append(v)
        return len(self.consts) - 1

    def _emit(self, op, arg):
        self.instructions.append((op, arg))

    def _emit_jump(self, op):
        idx = len(self.instructions)
        self._emit(op, -1)
        return idx

    def _patch(self, idx, target):
        op, _ = self.instructions[idx]
        self.instructions[idx] = (op, target)

    def _alloc_local(self, name):
        if name in self.locals:
            return self.locals[name]
        idx = self.next_local
        self.locals[name] = idx
        self.next_local += 1
        return idx

    # =====================
    # FAST LOOP DETECTION
    # =====================
    def _can_fastcount(self, stmt: LoopStmt):
        """
        Detect:
            if (i == LIMIT) break;
            i = i + 1;
        """
        if not isinstance(stmt.body, BlockStmt):
            return None
        body = stmt.body.body
        if len(body) != 2:
            return None

        cond_stmt, inc_stmt = body

        # Check break-if
        if not isinstance(cond_stmt, IfStmt):
            return None
        if not isinstance(cond_stmt.then_branch, BreakStmt):
            return None
        cond = cond_stmt.condition

        if not (isinstance(cond, Binary) and cond.op == "=="):
            return None
        if not (isinstance(cond.left, Variable) and isinstance(cond.right, Literal)):
            return None

        var = cond.left.name
        limit = cond.right.value
        if not isinstance(limit, int):
            return None
        if var not in self.locals:
            return None

        # Check increment
        if not isinstance(inc_stmt, ExprStmt): return None
        if not isinstance(inc_stmt.expr, Assign): return None

        a = inc_stmt.expr
        if not (isinstance(a.target, Variable) and a.target.name == var):
            return None

        if not (isinstance(a.value, Binary) and a.value.op == "+"):
            return None
        if not (isinstance(a.value.left, Variable) and a.value.left.name == var):
            return None
        if not (isinstance(a.value.right, Literal) and a.value.right.value == 1):
            return None

        return self.locals[var], limit

    # =====================
    # STATEMENTS
    # =====================
    def _compile_stmt(self, stmt):

        # ---------------- Block
        if isinstance(stmt, BlockStmt):
            for s in stmt.body:
                self._compile_stmt(s)
            return

        # ---------------- let
        if isinstance(stmt, LetStmt):
            if stmt.initializer:
                self._compile_expr(stmt.initializer)
            else:
                self._emit(OP_LOAD_CONST, self._add_const(None))
            idx = self._alloc_local(stmt.name)
            self._emit(OP_STORE_LOCAL, idx)
            return

        # ---------------- print
        if isinstance(stmt, PrintStmt):
            self._compile_expr(stmt.expr)
            self._emit(OP_PRINT, None)
            return

        # ---------------- expr stmt
        if isinstance(stmt, ExprStmt):
            self._compile_expr(stmt.expr)
            self._emit(OP_POP, None)
            return

        # ---------------- if
        if isinstance(stmt, IfStmt):
            self._compile_expr(stmt.condition)
            jf = self._emit_jump(OP_JUMP_IF_FALSE)
            self._compile_stmt(stmt.then_branch)
            jend = self._emit_jump(OP_JUMP)
            self._patch(jf, len(self.instructions))
            if stmt.else_branch:
                self._compile_stmt(stmt.else_branch)
            self._patch(jend, len(self.instructions))
            return

        # ---------------- while
        if isinstance(stmt, WhileStmt):
            start = len(self.instructions)
            self._compile_expr(stmt.condition)
            jf = self._emit_jump(OP_JUMP_IF_FALSE)

            ctx = {"breaks": [], "start": start}
            self.loop_stack.append(ctx)

            self._compile_stmt(stmt.body)
            self._emit(OP_JUMP, start)

            end = len(self.instructions)
            self._patch(jf, end)
            for bp in ctx["breaks"]:
                self._patch(bp, end)
            self.loop_stack.pop()
            return

        # ---------------- loop (FAST version)
        if isinstance(stmt, LoopStmt):

            fast = self._can_fastcount(stmt)
            if fast:
                local_idx, limit = fast
                end_target = len(self.instructions) + 1  # NEXT instruction
                self._emit(OP_FAST_COUNT, (local_idx, limit, end_target))
                return

            # fallback: regular loop
            start = len(self.instructions)
            ctx = {"breaks": [], "start": start}
            self.loop_stack.append(ctx)

            self._compile_stmt(stmt.body)
            self._emit(OP_JUMP, start)

            end = len(self.instructions)
            for bp in ctx["breaks"]:
                self._patch(bp, end)

            self.loop_stack.pop()
            return

        # ---------------- function
        if isinstance(stmt, FunctionStmt):
            sub = Compiler(self.verbose)
            sub.name = stmt.name
            # params
            sub.locals = {}
            sub.next_local = 0
            for p in stmt.params:
                sub.locals[p] = sub.next_local
                sub.next_local += 1
            sub.argcount = len(stmt.params)
            # body
            for s in stmt.body.body:
                sub._compile_stmt(s)
            sub._emit(OP_LOAD_CONST, sub._add_const(None))
            sub._emit(OP_RETURN, None)

            code = Code(stmt.name, sub.instructions[:], sub.consts[:],
                        sub.next_local, sub.argcount)
            idx = self._add_const(code)
            self._emit(OP_MAKE_FUNCTION, ("CODE", idx, stmt.name,
                                          code.argcount, code.nlocals))
            self._emit(OP_STORE_GLOBAL, stmt.name)
            return

        # ---------------- return
        if isinstance(stmt, ReturnStmt):
            if stmt.value:
                self._compile_expr(stmt.value)
            else:
                self._emit(OP_LOAD_CONST, self._add_const(None))
            self._emit(OP_RETURN, None)
            return

        # ---------------- break
        if isinstance(stmt, BreakStmt):
            if not self.loop_stack:
                raise CompileError("break outside loop")
            j = self._emit_jump(OP_JUMP)
            self.loop_stack[-1]["breaks"].append(j)
            return

        raise CompileError("Unknown stmt")

    # =====================
    # EXPRESSIONS
    # =====================
    def _compile_expr(self, expr):

        # ----- literal
        if isinstance(expr, Literal):
            self._emit(OP_LOAD_CONST, self._add_const(expr.value))
            return

        # ----- var
        if isinstance(expr, Variable):
            if expr.name in self.locals:
                self._emit(OP_LOAD_LOCAL, self.locals[expr.name])
            else:
                self._emit(OP_LOAD_GLOBAL, expr.name)
            return

        # ----- grouping
        if isinstance(expr, Grouping):
            self._compile_expr(expr.expression)
            return

        # ----- unary
        if isinstance(expr, Unary):
            self._compile_expr(expr.operand)
            if expr.op == "!":
                self._emit(OP_NOT, None)
            elif expr.op == "-":
                self._emit(OP_LOAD_CONST, self._add_const(-1))
                self._emit(OP_MUL, None)
            return

        # ----- binary
        if isinstance(expr, Binary):

            # detect i + 1 → INC_LOCAL
            if (expr.op == "+"
                and isinstance(expr.left, Variable)
                and isinstance(expr.right, Literal)
                and expr.right.value == 1
                and expr.left.name in self.locals):

                idx = self.locals[expr.left.name]
                self._emit(OP_INC_LOCAL, idx)
                # push new value
                self._emit(OP_LOAD_LOCAL, idx)
                return

            # normal binary
            self._compile_expr(expr.left)
            self._compile_expr(expr.right)

            opmap = {
                "+": OP_ADD, "-": OP_SUB, "*": OP_MUL, "/": OP_DIV,
                "%": OP_MOD,
                "==": OP_EQ, "!=": OP_NEQ, "<": OP_LT,
                "<=": OP_LTE, ">": OP_GT, ">=": OP_GTE
            }
            self._emit(opmap[expr.op], None)
            return

        # ----- assign
        if isinstance(expr, Assign):
            name = expr.target.name

            # detect i = i + 1
            if (isinstance(expr.value, Binary)
                and expr.value.op == "+"
                and isinstance(expr.value.left, Variable)
                and expr.value.left.name == name
                and isinstance(expr.value.right, Literal)
                and expr.value.right.value == 1
                and name in self.locals):

                idx = self.locals[name]
                self._emit(OP_INC_LOCAL, idx)
                self._emit(OP_LOAD_LOCAL, idx)
                return

            # regular assignment
            self._compile_expr(expr.value)
            if name in self.locals:
                idx = self.locals[name]
                self._emit(OP_STORE_LOCAL, idx)
                self._emit(OP_LOAD_LOCAL, idx)
            else:
                self._emit(OP_STORE_GLOBAL, name)
                self._emit(OP_LOAD_GLOBAL, name)
            return

        # ---- member load
        if isinstance(expr, Member):
            self._compile_expr(expr.base)
            self._emit(OP_LOAD_ATTR, expr.name)
            return

        # ---- function expr
        if isinstance(expr, FunctionExpr):
            idx = self._add_const(expr)
            self._emit(OP_MAKE_FUNCTION, ("AST", idx))
            return

        # ---- call
        if isinstance(expr, Call):
            self._compile_expr(expr.callee)
            for a in expr.arguments:
                self._compile_expr(a)
            self._emit(OP_CALL, len(expr.arguments))
            return

        raise CompileError("Unknown expr")


def compile_module_to_code(stmts, name="<module>", verbose=False):
    c = Compiler(verbose)
    return c.compile_module(stmts, name)
