"""
Environment (variable scope) system for the Falcon language.

Each Environment holds:
- a dictionary of variable bindings
- a reference to an optional parent environment (lexical outer scope)

This enables:
- let-scoped variables
- block scoping
- nested functions (closures)
- proper variable shadowing
"""

from __future__ import annotations
from typing import Any, Dict, Optional


class Environment:
    def __init__(self, parent: Optional["Environment"] = None):
        self.values: Dict[str, Any] = {}
        self.parent = parent

    # -------------------------
    # Variable Definition: let x = value
    # -------------------------
    def define(self, name: str, value: Any):
        self.values[name] = value

    # -------------------------
    # Variable Lookup: get x
    # -------------------------
    def get(self, name: str) -> Any:
        if name in self.values:
            return self.values[name]

        if self.parent is not None:
            return self.parent.get(name)

        raise NameError(f"Undefined variable '{name}'")

    # -------------------------
    # Variable Assignment: x = value
    # -------------------------
    def assign(self, name: str, value: Any):
        if name in self.values:
            self.values[name] = value
            return

        if self.parent is not None:
            return self.parent.assign(name, value)

        # If not found anywhere:
        raise NameError(f"Attempt to assign to undefined variable '{name}'")

    # -------------------------
    # Debug Helper
    # -------------------------
    def __repr__(self):
        parent = "None" if self.parent is None else "Env(...)"
        return f"Environment(values={self.values}, parent={parent})"
