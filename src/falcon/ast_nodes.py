"""
AST node definitions for Falcon.

Lightweight dataclasses representing Expressions and Statements
for the Falcon language.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, List, Optional

# ================================================================
# Expression nodes
# ================================================================
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
class ListLiteral(Expr):
    elements: List[Expr]

    def __repr__(self) -> str:
        return f"ListLiteral({self.elements!r})"

@dataclass
class TupleLiteral(Expr):
    elements: List[Expr]

    def __repr__(self) -> str:
        return f"TupleLiteral({self.elements!r})"

@dataclass
class DictLiteral(Expr):
    entries: List[tuple]

    def __repr__(self) -> str:
        return f"DictLiteral({self.entries!r})"

@dataclass
class SetLiteral(Expr):
    elements: List[Expr]

    def __repr__(self) -> str:
        return f"SetLiteral({self.elements!r})"

@dataclass
class ArrayLiteral(Expr):
    size_expr: Expr

    def __repr__(self) -> str:
        return f"ArrayLiteral({self.size_expr!r})"

@dataclass
class Subscript(Expr):
    base: Expr
    index: Expr

    def __repr__(self) -> str:
        return f"Subscript({self.base!r}[{self.index!r}])"

@dataclass
class Call(Expr):
    callee: Expr
    arguments: List[Expr]

    def __repr__(self) -> str:
        args = ", ".join(repr(a) for a in self.arguments)
        return f"Call({self.callee!r}, [{args}])"


@dataclass
class Member(Expr):
    base: Expr
    name: str
    def __repr__(self) -> str:
        return f"Member({self.base!r}.{self.name})"


@dataclass
class FunctionExpr(Expr):
    name: Optional[str]
    params: List[str]
    body: "BlockStmt"
    param_types: dict[str, TypeAnnotation] = field(default_factory=dict)
    return_type: Optional[TypeAnnotation] = None
    def __repr__(self) -> str:
        return f"FunctionExpr({self.name or '<anon>'}({', '.join(self.params)}), {self.body!r})"


@dataclass
class Assign(Expr):
    target: Expr
    value: Expr
    def __repr__(self) -> str:
        return f"Assign({self.target!r} = {self.value!r})"


# ================================================================
# Statement nodes
# ================================================================
class Stmt:
    """Base class for statements."""


@dataclass
class ExprStmt(Stmt):
    expr: Expr
    def __repr__(self) -> str:
        return f"ExprStmt({self.expr!r})"


@dataclass
class TypeAnnotation:
    name: str
    # Future: could hold more info (e.g., generic parameters)


@dataclass
class LetBlockStmt(Stmt):
    """
    Block‑scoped let declaration.
    name: variable name
    initializer: optional Expr for initial value
    is_const: bool (future extension, currently always False for let)
    is_var: bool (distinguishes between var and let declarations)
    block: BlockStmt – body executed with its own environment where the variable is scoped
    """
    name: str
    initializer: Optional[Expr] = None
    is_const: bool = False
    is_var: bool = False
    type_ann: Optional[TypeAnnotation] = None
    block: "BlockStmt" = None


# Alias for backward compatibility
LetStmt = LetBlockStmt


# RESTORED — parser and interpreter require this
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


# ================================================================
# New Loop Types
# ================================================================
@dataclass
class ForStmt(Stmt):
    """
    Falcon-style For loop:

        for var i := 1 to 10 step 2 {
            ...
        }

    Step is optional.
    """
    name: str
    start: Expr
    end: Expr
    step: Optional[Expr]
    body: BlockStmt

    def __repr__(self) -> str:
        if self.step is None:
            return f"ForStmt(var {self.name} := {self.start!r} to {self.end!r}, {self.body!r})"
        return f"ForStmt(var {self.name} := {self.start!r} to {self.end!r} step {self.step!r}, {self.body!r})"


@dataclass
class LoopStmt(Stmt):
    """Infinite loop: loop { ... }"""
    body: BlockStmt
    def __repr__(self) -> str:
        return f"LoopStmt({self.body!r})"


@dataclass
class BreakStmt(Stmt):
    """
    AST node representing a `break` statement.
    Used to exit the nearest enclosing loop.
    """
    token: Optional[Any] = None

    def __repr__(self) -> str:
        return "<BreakStmt>"


# ================================================================
# Functions & Return
# ================================================================
@dataclass
class FunctionStmt(Stmt):
    name: str
    params: List[str]
    body: BlockStmt
    param_types: dict[str, TypeAnnotation] = field(default_factory=dict)
    return_type: Optional[TypeAnnotation] = None
    def __repr__(self) -> str:
        return f"FunctionStmt({self.name}({', '.join(self.params)}), {self.body!r})"


@dataclass
class ReturnStmt(Stmt):
    value: Optional[Expr] = None
    def __repr__(self) -> str:
        return f"ReturnStmt({self.value!r})"


@dataclass
class ThrowStmt(Stmt):
    value: Expr
    def __repr__(self) -> str:
        return f"ThrowStmt({self.value!r})"


@dataclass
class TryCatchStmt(Stmt):
    try_block: BlockStmt
    catch_name: str
    catch_block: BlockStmt
    def __repr__(self) -> str:
        return f"TryCatchStmt(try={self.try_block!r}, catch {self.catch_name} => {self.catch_block!r})"


# ================================================================
# Pattern Matching
# ================================================================

# Pattern nodes
class Pattern:
    """Base class for patterns."""
    pass

@dataclass
class LiteralPattern(Pattern):
    value: Any
    def __repr__(self) -> str:
        return f"LiteralPattern({self.value!r})"

@dataclass
class VariablePattern(Pattern):
    name: str
    def __repr__(self) -> str:
        return f"VariablePattern({self.name})"

@dataclass
class TypePattern(Pattern):
    type_expr: Expr
    def __repr__(self) -> str:
        return f"TypePattern({self.type_expr!r})"

@dataclass
class ListPattern(Pattern):
    elements: List[Pattern]
    def __repr__(self) -> str:
        return f"ListPattern([{', '.join(repr(e) for e in self.elements)}])"

@dataclass
class TuplePattern(Pattern):
    elements: List[Pattern]
    def __repr__(self) -> str:
        return f"TuplePattern([{', '.join(repr(e) for e in self.elements)}])"

@dataclass
class DictPattern(Pattern):
    entries: List[tuple[str, Pattern]]
    def __repr__(self) -> str:
        return f"DictPattern({self.entries!r})"

@dataclass
class OrPattern(Pattern):
    patterns: List[Pattern]
    def __repr__(self) -> str:
        return f"OrPattern({' | '.join(repr(p) for p in self.patterns)})"

@dataclass
class WildcardPattern(Pattern):
    """_ pattern that matches anything"""
    def __repr__(self) -> str:
        return "WildcardPattern()"

# Match expression and case statement
@dataclass
class CaseArm:
    pattern: Pattern
    guard: Optional[Expr]  # Optional guard condition
    body: BlockStmt
    
    def __repr__(self) -> str:
        guard_str = f" if {self.guard!r}" if self.guard else ""
        return f"CaseArm({self.pattern!r}{guard_str}, {self.body!r})"

@dataclass
class MatchExpr(Expr):
    """Match expression: match value { case pattern: expr; case pattern: expr; }"""
    value: Expr
    arms: List[CaseArm]
    
    def __repr__(self) -> str:
        arms_str = "; ".join(repr(arm) for arm in self.arms)
        return f"MatchExpr({self.value!r}, {{ {arms_str} }})"

@dataclass
class MatchStmt(Stmt):
    """Match statement: match value { case pattern { statements } }"""
    value: Expr
    arms: List[CaseArm]
    
    def __repr__(self) -> str:
        arms_str = "; ".join(repr(arm) for arm in self.arms)
        return f"MatchStmt({self.value!r}, {{ {arms_str} }})"
