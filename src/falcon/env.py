"""
Environment (variable scope) system for the Falcon language.

Each Environment holds:
- a dictionary of variable bindings
- a reference to an optional parent environment (lexical outer scope)

This enables:
- var-scoped variables
- block scoping
- nested functions (closures)
- proper variable shadowing
- const protection (no reassignment)
"""

from __future__ import annotations
from typing import Any, Dict, Optional, Set


class Environment:
    def __init__(self, parent: Optional["Environment"] = None):
        # store values in a simple dict
        self.values: Dict[str, Any] = {}
        # track which names are const in this environment
        self.consts: Set[str] = set()
        self.parent = parent

    # -------------------------
    # Variable Definition: var x := value
    # -------------------------
    def define(self, name: str, value: Any, is_const: bool = False):
        """
        Define a name in the current environment.
        If is_const=True, the name cannot be reassigned (in this env or children will still respect).
        """
        self.values[name] = value
        if is_const:
            self.consts.add(name)
        else:
            # if redefining a previously-const here, keep const unless explicitly changed
            if name in self.consts:
                # keep existing const flag (do not silently remove)
                pass

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
        # If variable exists in current env, check const and assign
        if name in self.values:
            if name in self.consts:
                raise NameError(f"Attempt to assign to constant '{name}'")
            self.values[name] = value
            return

        # Otherwise look up in parent chain
        if self.parent is not None:
            return self.parent.assign(name, value)

        # If not found anywhere:
        raise NameError(f"Attempt to assign to undefined variable '{name}'")

    # -------------------------
    # Snapshot helpers (for closures)
    # -------------------------
    def snapshot(self) -> Dict[str, Any]:
        """
        Return a shallow copy mapping of this environment's current bindings.
        Does NOT include parent scopes. Intended for closures: the compiler/VM
        can capture just the local bindings in effect at function definition time.
        """
        return dict(self.values)

    @classmethod
    def from_mapping(cls, mapping: Dict[str, Any], parent: Optional["Environment"] = None) -> "Environment":
        """
        Create a new Environment pre-populated from a mapping.
        Useful when converting a compiled/VM closure snapshot into a real Environment
        that the interpreter can use as the function closure.
        """
        env = cls(parent=parent)
        env.values.update(mapping)
        return env

    # -------------------------
    # Debug Helper
    # -------------------------
    def __repr__(self):
        parent = "None" if self.parent is None else "Env(...)"
        return f"Environment(values={self.values}, consts={self.consts}, parent={parent})"
