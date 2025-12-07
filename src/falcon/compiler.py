# src/falcon/compiler.py
"""
Compiler: AST -> bytecode for Falcon A3 hybrid VM.

Design notes:
- Produces a Code object with:
    - instructions (list of (opcode, operand?) tuples)
    - constants pool (list)
    - argcount, local variable slots
- Simple variable indexing: locals first (by declaration order), otherwise globals.
- Detects simple captures: if a function body refers to names not defined as locals/params, we mark it CAPTURED.
  Captured functions remain as AST-backed closures and will be executed by the interpreter at runtime.
- Bytecode is intentionally small and readable.
"""

from __future__ import annotations
from typing import Any, List, Dict, Tuple, Optional, Set

from .ast_nodes import *
from .tokens import TokenType

# Opcodes (small set)
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
OP_DEFINE_LOCAL = "DEFINE_LOCAL"
OP_DEFINE_GLOBAL = "DEFINE_GLOBAL"
OP_NOP = "NOP"
OP_PRINT = "PRINT"  # convenience
OP_MAKE_FUNCTION = "MAKE_FUNCTION"  # create a function object from compiled code or AST
OP_LOAD_ATTR = "LOAD_ATTR"
OP_STORE_ATTR = "STORE_ATTR"
OP_LOOP = "LOOP"  # infinite loop (can be compiled as jump)

# Helper dataclasses
class Code:
    def __init__(self, instructions: List[Tuple[str, Any]], consts: List[Any], argcount: int, nlocals: int, name: Optional[str]=None):
        self.instructions = instructions
        self.consts = consts
        self.argcount = argcount
        self.nlocals = nlocals
        self.name = name or "<code>"

    def __repr__(self):
        return f"<Code {self.name} args={self.argcount} locals={self.nlocals} consts={len(self.consts)} instr={len(self.instructions)}>"

class FunctionObject:
    """
    Function wrapper exposed to VM:
      - if .code is Code -> VM can execute
      - if .ast_node is FunctionStmt/FunctionExpr -> this is a captured function and should be executed by interpreter fallback
    """
    def __init__(self, name: Optional[str], code: Optional[Code], ast_node=None):
        self.name = name
        self.code = code
        self.ast_node = ast_node  # when captures present: keep AST node for interpreter fallback

    def is_ast_backed(self):
        return self.ast_node is not None

    def __repr__(self):
        if self.code:
            return f"<FunctionObject {self.name} code={self.code}>"
        return f"<FunctionObject {self.name} AST>"

# ---------------------------------------------------------
# Simple static analyzer: find names defined and free vars
# ---------------------------------------------------------
def analyze_scope_function(func_node: FunctionStmt | FunctionExpr) -> Tuple[Set[str], Set[str]]:
    """
    Return (defined_names, referenced_names)
    defined_names: parameters + locally 'var' declared names
    referenced_names: names referenced anywhere in body (Variable nodes)
    """
    defined: Set[str] = set()
    referenced: Set[str] = set()

    # params
    for p in func_node.params:
        defined.add(p)

    # traverse body
    def visit_stmt(s):
        if isinstance(s, BlockStmt):
            for st in s.body:
                visit_stmt(st)
        elif isinstance(s, LetStmt):
            defined.add(s.name)
            if s.initializer:
                visit_expr(s.initializer)
        elif isinstance(s, ExprStmt):
            visit_expr(s.expr)
        elif isinstance(s, PrintStmt):
            visit_expr(s.expr)
        elif isinstance(s, IfStmt):
            visit_expr(s.condition)
            visit_stmt(s.then_branch)
            if s.else_branch:
                visit_stmt(s.else_branch)
        elif isinstance(s, WhileStmt):
            visit_expr(s.condition)
            visit_stmt(s.body)
        elif isinstance(s, ForStmt):
            # for var i := start to end [step] { body }
            defined.add(s.name)
            visit_expr(s.start)
            visit_expr(s.end)
            if s.step:
                visit_expr(s.step)
            visit_stmt(s.body)
        elif isinstance(s, LoopStmt):
            visit_stmt(s.body)
        elif isinstance(s, FunctionStmt):
            # function declaration introduces a defined name
            defined.add(s.name)
            # nested function - we still visit body to collect referenced names
            for st in s.body.body:
                visit_stmt(st)
        elif isinstance(s, ReturnStmt):
            if s.value:
                visit_expr(s.value)
        else:
            # fallback: try to inspect attributes
            for attr in getattr(s, "__dict__", {}).values():
                if isinstance(attr, list):
                    for it in attr:
                        if isinstance(it, (Expr, Stmt)):
                            if isinstance(it, Expr):
                                visit_expr(it)
                            else:
                                visit_stmt(it)
                elif isinstance(attr, (Expr, Stmt)):
                    if isinstance(attr, Expr):
                        visit_expr(attr)
                    else:
                        visit_stmt(attr)

    def visit_expr(e):
        if isinstance(e, Literal):
            return
        if isinstance(e, Variable):
            referenced.add(e.name)
            return
        if isinstance(e, Binary):
            visit_expr(e.left); visit_expr(e.right); return
        if isinstance(e, Unary):
            visit_expr(e.operand); return
        if isinstance(e, Grouping):
            visit_expr(e.expression); return
        if isinstance(e, Call):
            visit_expr(e.callee)
            for a in e.arguments:
                visit_expr(a)
            return
        if isinstance(e, Member):
            visit_expr(e.base); # attribute name is not a Variable
            return
        if isinstance(e, FunctionExpr):
            # nested function expr: its params & locals are separate,
            # but we should visit its body to collect referenced names (could reference outer)
            for st in e.body.body:
                visit_stmt(st)
            return
        if isinstance(e, Assign):
            visit_expr(e.target)
            visit_expr(e.value)
            return

    for st in func_node.body.body if hasattr(func_node, "body") else []:
        visit_stmt(st)

    return defined, referenced

# ---------------------------------------------------------
# Compiler class
# ---------------------------------------------------------
class Compiler:
    def __init__(self):
        self.consts: List[Any] = []
        self.instructions: List[Tuple[str, Any]] = []
        # local variable ordering for current function
        self.local_names: List[str] = []
        self.name_to_local: Dict[str,int] = {}

    def reset_function(self):
        self.consts = []
        self.instructions = []
        self.local_names = []
        self.name_to_local = {}

    def add_const(self, v: Any) -> int:
        try:
            return self.consts.index(v)
        except ValueError:
            self.consts.append(v)
            return len(self.consts)-1

    def emit(self, opcode: str, operand: Any = None):
        self.instructions.append((opcode, operand))

    def compile_module(self, stmts: List[Stmt]) -> Code:
        # top-level: treat as a function with 0 args and dynamic locals for top-level var declarations.
        self.reset_function()
        # gather top-level var declarations to reserve locals
        for s in stmts:
            if isinstance(s, LetStmt):
                self._ensure_local(s.name)
        for s in stmts:
            self.compile_stmt(s)
        # final: return None
        self.emit(OP_LOAD_CONST, self.add_const(None))
        self.emit(OP_RETURN, None)
        return Code(self.instructions[:], self.consts[:], argcount=0, nlocals=len(self.local_names), name="<module>")

    # ---------------- statements compilation ----------------
    def compile_stmt(self, stmt: Stmt):
        if isinstance(stmt, ExprStmt):
            self.compile_expr(stmt.expr)
            self.emit(OP_POP)
            return
        if isinstance(stmt, LetStmt):
            # initializer or None
            val = stmt.initializer
            if val:
                self.compile_expr(val)
            else:
                self.emit(OP_LOAD_CONST, self.add_const(None))
            # define local if in function; top-level treat as global definition
            # we'll use locals if compiling a function (local_names present)
            if self.local_names is not None:
                idx = self._ensure_local(stmt.name)
                self.emit(OP_STORE_LOCAL, idx)
            else:
                # fallback: global
                self.emit(OP_STORE_GLOBAL, stmt.name)
            return
        if isinstance(stmt, PrintStmt):
            self.compile_expr(stmt.expr)
            self.emit(OP_PRINT)
            return
        if isinstance(stmt, BlockStmt):
            # new block: just compile statements sequentially
            for s in stmt.body:
                self.compile_stmt(s)
            return
        if isinstance(stmt, IfStmt):
            self.compile_expr(stmt.condition)
            # jump_if_false placeholder
            jfalse_pos = len(self.instructions)
            self.emit(OP_JUMP_IF_FALSE, None)
            # then
            self.compile_stmt(stmt.then_branch)
            # jump over else
            jdone_pos = len(self.instructions)
            self.emit(OP_JUMP, None)
            # patch jfalse to current position
            cur = len(self.instructions)
            self.instructions[jfalse_pos] = (OP_JUMP_IF_FALSE, cur)
            # else
            if stmt.else_branch:
                self.compile_stmt(stmt.else_branch)
            # patch done
            cur2 = len(self.instructions)
            self.instructions[jdone_pos] = (OP_JUMP, cur2)
            return
        if isinstance(stmt, WhileStmt):
            start_pos = len(self.instructions)
            self.compile_expr(stmt.condition)
            jfalse_pos = len(self.instructions)
            self.emit(OP_JUMP_IF_FALSE, None)
            self.compile_stmt(stmt.body)
            # jump back
            self.emit(OP_JUMP, start_pos)
            # patch jfalse
            self.instructions[jfalse_pos] = (OP_JUMP_IF_FALSE, len(self.instructions))
            return
        if isinstance(stmt, ForStmt):
            # for var i := start to end [step step] { body }
            # compile start, store into local
            self.compile_expr(stmt.start)
            idx = self._ensure_local(stmt.name)
            self.emit(OP_STORE_LOCAL, idx)
            # compute end and step and store on stack, we'll use locals for them
            self.compile_expr(stmt.end)
            end_idx = self._ensure_local(f"__for_end_{idx}")
            self.emit(OP_STORE_LOCAL, end_idx)
            if stmt.step:
                self.compile_expr(stmt.step)
            else:
                self.emit(OP_LOAD_CONST, self.add_const(1))
            step_idx = self._ensure_local(f"__for_step_{idx}")
            self.emit(OP_STORE_LOCAL, step_idx)
            # loop start
            loop_start = len(self.instructions)
            # load loop var and end and step
            self.emit(OP_LOAD_LOCAL, idx)
            self.emit(OP_LOAD_LOCAL, end_idx)
            self.emit(OP_LOAD_LOCAL, step_idx)
            # compare: depending on sign handled in VM by LOOKUP; here simple: do <=
            self.emit(OP_LTE)  # uses top two values: left <= right; NOTE: this will consume two operands; we must ensure VM knows consuming order
            jfalse_pos = len(self.instructions)
            self.emit(OP_JUMP_IF_FALSE, None)
            # body
            self.compile_stmt(stmt.body)
            # increment
            self.emit(OP_LOAD_LOCAL, idx)
            self.emit(OP_LOAD_LOCAL, step_idx)
            self.emit(OP_ADD)
            self.emit(OP_STORE_LOCAL, idx)
            # jump back
            self.emit(OP_JUMP, loop_start)
            # patch jfalse
            self.instructions[jfalse_pos] = (OP_JUMP_IF_FALSE, len(self.instructions))
            return
        if isinstance(stmt, LoopStmt):
            loop_start = len(self.instructions)
            self.compile_stmt(stmt.body)
            self.emit(OP_JUMP, loop_start)
            return
        if isinstance(stmt, FunctionStmt):
            # compile nested function into a Code object _unless_ it captures free variables.
            defined, referenced = analyze_scope_function(stmt)
            # free variables = referenced - defined
            free = referenced - defined
            if free:
                # leave AST-backed function: MAKE_FUNCTION with AST node
                idx = self.add_const(stmt)  # store AST function as const
                self.emit(OP_MAKE_FUNCTION, ("AST", idx))  # VM will wrap into FunctionObject(ast_node=...)
                # and store into local (or global if top-level)
                local_idx = self._ensure_local(stmt.name)
                self.emit(OP_STORE_LOCAL, local_idx)
                return
            # else compile function body as code
            # create a new sub-compiler for function body
            sub = Compiler()
            # reserve params as locals
            for p in stmt.params:
                sub._ensure_local(p)
            # reserve any let declarations inside
            for st in stmt.body.body:
                if isinstance(st, LetStmt):
                    sub._ensure_local(st.name)
            # compile body
            for st in stmt.body.body:
                sub.compile_stmt(st)
            sub.emit(OP_LOAD_CONST, sub.add_const(None))
            sub.emit(OP_RETURN, None)
            c = Code(sub.instructions[:], sub.consts[:], argcount=len(stmt.params), nlocals=len(sub.local_names), name=stmt.name)
            idx = self.add_const(c)
            self.emit(OP_MAKE_FUNCTION, ("CODE", idx, stmt.name, len(stmt.params), len(sub.local_names)))
            # store into local
            local_idx = self._ensure_local(stmt.name)
            self.emit(OP_STORE_LOCAL, local_idx)
            return
        if isinstance(stmt, ReturnStmt):
            if stmt.value:
                self.compile_expr(stmt.value)
            else:
                self.emit(OP_LOAD_CONST, self.add_const(None))
            self.emit(OP_RETURN, None)
            return

        raise NotImplementedError(f"Compiler: statement not implemented: {stmt}")

    # ---------------- expressions compilation ----------------
    def compile_expr(self, expr: Expr):
        if isinstance(expr, Literal):
            idx = self.add_const(expr.value)
            self.emit(OP_LOAD_CONST, idx)
            return
        if isinstance(expr, Variable):
            # if local defined
            if expr.name in self.name_to_local:
                self.emit(OP_LOAD_LOCAL, self.name_to_local[expr.name])
                return
            # else global
            self.emit(OP_LOAD_GLOBAL, expr.name)
            return
        if isinstance(expr, Grouping):
            self.compile_expr(expr.expression)
            return
        if isinstance(expr, Unary):
            self.compile_expr(expr.operand)
            if expr.op == "!":
                self.emit(OP_NOT)
                return
            if expr.op == "-":
                self.emit(OP_LOAD_CONST, self.add_const(0))
                self.emit(OP_SUB)
                return
            raise NotImplementedError(f"Unary op {expr.op}")
        if isinstance(expr, Binary):
            # evaluate left then right
            self.compile_expr(expr.left)
            self.compile_expr(expr.right)
            op = expr.op
            if op == "+":
                self.emit(OP_ADD)
            elif op == "-":
                self.emit(OP_SUB)
            elif op == "*":
                self.emit(OP_MUL)
            elif op == "/":
                self.emit(OP_DIV)
            elif op == "%":
                self.emit(OP_MOD)
            elif op == "==":
                self.emit(OP_EQ)
            elif op == "!=":
                self.emit(OP_NEQ)
            elif op == "<":
                self.emit(OP_LT)
            elif op == "<=":
                self.emit(OP_LTE)
            elif op == ">":
                self.emit(OP_GT)
            elif op == ">=":
                self.emit(OP_GTE)
            elif op == "&&":
                self.emit(OP_AND)
            elif op == "||":
                self.emit(OP_OR)
            else:
                raise NotImplementedError(f"Binary op {op}")
            return
        if isinstance(expr, Assign):
            # target is Variable or Member
            self.compile_expr(expr.value)
            if isinstance(expr.target, Variable):
                if expr.target.name in self.name_to_local:
                    self.emit(OP_STORE_LOCAL, self.name_to_local[expr.target.name])
                    # load assigned value to leave it on stack (assignment returns value)
                    self.emit(OP_LOAD_LOCAL, self.name_to_local[expr.target.name])
                    return
                else:
                    self.emit(OP_STORE_GLOBAL, expr.target.name)
                    self.emit(OP_LOAD_GLOBAL, expr.target.name)
                    return
            if isinstance(expr.target, Member):
                # compile base, then attribute name and store (we push base and value)
                self.compile_expr(expr.target.base)
                # swap base and value
                self.emit(OP_STORE_ATTR, expr.target.name)  # VM will expect (base, value) on stack and set attr
                # to return value, reload member
                self.compile_expr(expr.target)
                return
            raise NotImplementedError("Assign target not supported")
        if isinstance(expr, Member):
            # base then attribute name
            self.compile_expr(expr.base)
            self.emit(OP_LOAD_ATTR, expr.name)
            return
        if isinstance(expr, FunctionExpr):
            # similar logic to FunctionStmt: detect captures
            # Build a synthetic name for anonymous
            name = expr.name
            defined, referenced = analyze_scope_function(expr)
            free = referenced - defined
            if free:
                # keep as AST-backed function object -> const store AST node
                idx = self.add_const(expr)
                self.emit(OP_MAKE_FUNCTION, ("AST", idx))
                return
            # compile into code
            sub = Compiler()
            for p in expr.params:
                sub._ensure_local(p)
            for st in expr.body.body:
                if isinstance(st, LetStmt):
                    sub._ensure_local(st.name)
            for st in expr.body.body:
                sub.compile_stmt(st)
            sub.emit(OP_LOAD_CONST, sub.add_const(None))
            sub.emit(OP_RETURN, None)
            c = Code(sub.instructions[:], sub.consts[:], argcount=len(expr.params), nlocals=len(sub.local_names), name=name or "<lambda>")
            idx = self.add_const(c)
            self.emit(OP_MAKE_FUNCTION, ("CODE", idx, name or "<lambda>", len(expr.params), len(sub.local_names)))
            return
        if isinstance(expr, Call):
            # compile callee then args
            self.compile_expr(expr.callee)
            for a in expr.arguments:
                self.compile_expr(a)
            # emit CALL with argcount
            self.emit(OP_CALL, len(expr.arguments))
            return

        raise NotImplementedError(f"compile_expr not implemented for {type(expr).__name__}")

    # ---------------- helpers ----------------
    def _ensure_local(self, name: str) -> int:
        if name in self.name_to_local:
            return self.name_to_local[name]
        idx = len(self.local_names)
        self.local_names.append(name)
        self.name_to_local[name] = idx
        return idx
