"""
Environment (variable scope) system for the Falcon language.

Supports:
- var declarations (mutable)
- const declarations (immutable, reassignment forbidden)
- lexical scoping
- closures
"""

from __future__ import annotations
from typing import Any, Dict, Optional


class Environment:
    def __init__(self, parent: Optional["Environment"] = None):
        self.values: Dict[str, Any] = {}
        self.consts: Dict[str, bool] = {}   # Track which names are constant
        self.parent = parent

    # -------------------------
    # Variable Definition: var / const
    # -------------------------
    def define(self, name: str, value: Any, is_const: bool = False):
        """
        Defines a new variable in THIS scope.
        If the variable already exists in this scope and is const -> error.
        """
        if name in self.values and self.consts.get(name, False):
            raise NameError(f"Cannot redefine constant '{name}' in the same scope")

        self.values[name] = value

        if is_const:
            self.consts[name] = True
        else:
            # Ensure not marked const
            if name in self.consts:
                self.consts.pop(name, None)

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
        """
        Assigns to an existing variable. Walks parent scopes.
        Fails if variable is const.
        """
        env = self
        while env is not None:
            if name in env.values:
                if env.consts.get(name, False):
                    raise NameError(f"Cannot assign to constant '{name}'")
                env.values[name] = value
                return
            env = env.parent

        raise NameError(f"Attempt to assign to undefined variable '{name}'")

    # -------------------------
    # Debug Helper
    # -------------------------
    def __repr__(self):
        parent = "None" if self.parent is None else "Env(...)"
        return f"Environment(values={self.values}, consts={self.consts}, parent={parent})"
