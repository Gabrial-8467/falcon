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
        # optional language-level type annotations
        self.types: Dict[str, str] = {}
        self.parent: Optional["Environment"] = parent

    # -------------------------
    # Variable Definition: var x := value
    # -------------------------
    def define(
        self, name: str, value: Any, is_const: bool = False, type_name: Optional[str] = None
    ) -> None:
        """
        Define a name in the current environment.
        If is_const=True, the name cannot be reassigned (in this env or children will still respect).
        """
        if type_name is not None and not self._value_matches_type(value, type_name):
            got = type(value).__name__
            raise NameError(
                f"Type mismatch for '{name}': expected {type_name}, got {got}"
            )
        self.values[name] = value
        if type_name is not None:
            self.types[name] = type_name
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
    def assign(self, name: str, value: Any) -> None:
        # If variable exists in current env, check const and assign
        if name in self.values:
            if name in self.consts:
                raise NameError(f"Attempt to assign to constant '{name}'")
            if name in self.types:
                expected = self.types[name]
                if not self._value_matches_type(value, expected):
                    got = type(value).__name__
                    raise NameError(
                        f"Type mismatch for '{name}': expected {expected}, got {got}"
                    )
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
    def __repr__(self) -> str:
        parent = "None" if self.parent is None else "Env(...)"
        return (
            f"Environment(values={self.values}, consts={self.consts}, "
            f"types={self.types}, parent={parent})"
        )

    @staticmethod
    def _value_matches_type(value: Any, type_name: str) -> bool:
        normalized = type_name.strip().lower()
        union_parts = [p.strip() for p in normalized.split("|")]
        if len(union_parts) > 1:
            return any(Environment._value_matches_type(value, part) for part in union_parts)

        if normalized in ("any", "object"):
            return True
        if value is None:
            return normalized in ("null", "none")
        if normalized.startswith("list[") and normalized.endswith("]"):
            if not isinstance(value, list):
                return False
            inner = normalized[5:-1].strip()
            return all(Environment._value_matches_type(v, inner) for v in value)
        if normalized.startswith("set[") and normalized.endswith("]"):
            if not isinstance(value, set):
                return False
            inner = normalized[4:-1].strip()
            return all(Environment._value_matches_type(v, inner) for v in value)
        if normalized.startswith("tuple[") and normalized.endswith("]"):
            if not isinstance(value, tuple):
                return False
            inners = Environment._split_top_level(normalized[6:-1].strip())
            if len(inners) == 1:
                return all(Environment._value_matches_type(v, inners[0]) for v in value)
            if len(value) != len(inners):
                return False
            return all(Environment._value_matches_type(v, t) for v, t in zip(value, inners))
        if normalized.startswith("dict[") and normalized.endswith("]"):
            if not isinstance(value, dict):
                return False
            pair = Environment._split_top_level(normalized[5:-1].strip())
            if len(pair) != 2:
                return isinstance(value, dict)
            kt, vt = pair
            return all(
                Environment._value_matches_type(k, kt)
                and Environment._value_matches_type(v, vt)
                for k, v in value.items()
            )
        if normalized in ("int",):
            return isinstance(value, int) and not isinstance(value, bool)
        if normalized in ("float",):
            return isinstance(value, float)
        if normalized in ("number",):
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        if normalized in ("bool", "boolean"):
            return isinstance(value, bool)
        if normalized in ("str", "string"):
            return isinstance(value, str)
        if normalized in ("list",):
            return isinstance(value, list)
        if normalized in ("tuple",):
            return isinstance(value, tuple)
        if normalized in ("dict", "map", "objectdict"):
            return isinstance(value, dict)
        if normalized in ("set",):
            return isinstance(value, set)
        if normalized in ("function", "fn"):
            return callable(value)
        return type(value).__name__.lower() == normalized

    @staticmethod
    def _split_top_level(text: str) -> list[str]:
        parts: list[str] = []
        depth = 0
        cur: list[str] = []
        for ch in text:
            if ch == "[":
                depth += 1
            elif ch == "]" and depth > 0:
                depth -= 1
            if ch == "," and depth == 0:
                parts.append("".join(cur).strip())
                cur = []
                continue
            cur.append(ch)
        tail = "".join(cur).strip()
        if tail:
            parts.append(tail)
        return parts
