"""
Custom error classes and helpers for the Falcon language.

These errors are *not* the same as Python's LexerError / ParseError / InterpreterError.
They provide a unified FalconError base class + optional pretty
source highlighting that can be used in the future by runner/repl.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


class FalconError(Exception):
    """Base error for all Falcon-related issues."""
    pass


@dataclass
class SourceLocation:
    line: int
    col: int


@dataclass
class SourceContext:
    filename: str
    source: str
    location: SourceLocation


def format_error_message(msg: str, ctx: Optional[SourceContext]) -> str:
    """
    Produce a human-readable error string with optional source line highlighting.
    (Falcon's runner/repl may choose to use this.)
    """
    if ctx is None:
        return msg

    lines = ctx.source.splitlines()
    line_num = ctx.location.line
    col = ctx.location.col

    # Safe lookup
    if 1 <= line_num <= len(lines):
        line_text = lines[line_num - 1]
    else:
        line_text = ""

    pointer = " " * (col - 1) + "^"

    return (
        f"{ctx.filename}:{line_num}:{col}: {msg}\n"
        f"    {line_text}\n"
        f"    {pointer}"
    )
