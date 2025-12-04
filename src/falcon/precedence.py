"""
Operator precedence table for Falcon (JS-like).

Higher number == higher precedence.

This file exports:
- PREC : dict[str, int]  # mapping operator string -> precedence level
- LEFT_ASSOC : set[str]  # operators that are left-associative (most of them)
- RIGHT_ASSOC : set[str] # operators that are right-associative (e.g. assignment if added)

The parser uses PREC to decide how to climb-precedence when parsing binary expressions.
"""
from __future__ import annotations

# Precedence levels inspired by C/JS operator precedence,
# but simplified for the Falcon prototype.
# Larger number means the operator binds tighter.
PREC: dict[str, int] = {
    "||": 1,

    "&&": 2,

    "==": 3, "!=": 3,

    "<": 4, "<=": 4, ">": 4, ">=": 4,

    "+": 5, "-": 5,

    "*": 6, "/": 6, "%": 6,

    # power operator (if supported) would be higher and typically right-assoc:
    "**": 7,
}

# Associativity sets. Most binary ops are left-associative.
LEFT_ASSOC = {
    "||", "&&",
    "==", "!=", "<", "<=", ">", ">=",
    "+", "-", "*", "/", "%",
}

# Right-associative operators (none enabled by default here).
RIGHT_ASSOC = {
    "**",
}

__all__ = ["PREC", "LEFT_ASSOC", "RIGHT_ASSOC"]
