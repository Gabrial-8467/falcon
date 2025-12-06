"""
AST node definitions for Falcon.

Lightweight dataclasses representing Expressions and Statements
for the JS-like Falcon prototype.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, List, Optional


# ---------------------
# Expression nodes
# ---------------------
class Expr:
    """Base class for expressions."""


@dataclass
class Literal(Expr):
    value: Any

    def __repr__(self) -> str:
        return f"Literal({self.value!r})"


@dataclass
class Variable(Expr):
    name: str

    def __repr__(self) -> str:
        return f"Variable({self.name})"


@dataclass
class Binary(Expr):
    left: Expr
    op: str
    right: Expr

    def __repr__(self) -> str:
        return f"Binary({self.left!r} {self.op} {self.right!r})"


@dataclass
class Unary(Expr):
    op: str
    operand: Expr

    def __repr__(self) -> str:
        return f"Unary({self.op} {self.operand!r})"


@dataclass
class Grouping(Expr):
    expression: Expr

    def __repr__(self) -> str:
        return f"Grouping({self.expression!r})"


@dataclass
class Call(Expr):
    callee: Expr
    arguments: List[Expr]

    def __repr__(self) -> str:
        args = ", ".join(repr(a) for a in self.arguments)
        return f"Call({self.callee!r}, [{args}])"


@dataclass
class Member(Expr):
    """
    Member access: base.name  (e.g., console.log)
    """
    base: Expr
    name: str

    def __repr__(self) -> str:
        return f"Member({self.base!r}.{self.name})"


@dataclass
class FunctionExpr(Expr):
    """Function expression (anonymous or named) usable in expression position."""
    name: Optional[str]
    params: List[str]
    body: 'BlockStmt'  # reuse BlockStmt for the body

    def __repr__(self) -> str:
        return f"FunctionExpr({self.name or '<anon>'}({', '.join(self.params)}), {self.body!r})"


# ---------------------
# Statement nodes
# ---------------------
class Stmt:
    """Base class for statements."""


@dataclass
class ExprStmt(Stmt):
    expr: Expr

    def __repr__(self) -> str:
        return f"ExprStmt({self.expr!r})"


@dataclass
class LetStmt(Stmt):
    name: str
    initializer: Optional[Expr] = None

    def __repr__(self) -> str:
        return f"LetStmt({self.name}, {self.initializer!r})"


@dataclass
class PrintStmt(Stmt):
    expr: Expr

    def __repr__(self) -> str:
        return f"PrintStmt({self.expr!r})"


@dataclass
class BlockStmt(Stmt):
    body: List[Stmt]

    def __repr__(self) -> str:
        return f"BlockStmt([{', '.join(repr(s) for s in self.body)}])"


@dataclass
class IfStmt(Stmt):
    condition: Expr
    then_branch: Stmt
    else_branch: Optional[Stmt] = None

    def __repr__(self) -> str:
        return f"IfStmt(cond={self.condition!r}, then={self.then_branch!r}, else={self.else_branch!r})"


@dataclass
class WhileStmt(Stmt):
    condition: Expr
    body: Stmt

    def __repr__(self) -> str:
        return f"WhileStmt(cond={self.condition!r}, body={self.body!r})"


# ---------------------
# Utility / future nodes
# ---------------------
@dataclass
class FunctionStmt(Stmt):
    """
    Function declaration statement: function name(params) { ... }
    """
    name: str
    params: List[str]
    body: BlockStmt

    def __repr__(self) -> str:
        return f"FunctionStmt({self.name}({', '.join(self.params)}), {self.body!r})"


@dataclass
class ReturnStmt(Stmt):
    value: Optional[Expr] = None

    def __repr__(self) -> str:
        return f"ReturnStmt({self.value!r})"
