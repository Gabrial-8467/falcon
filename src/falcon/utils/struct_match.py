"""Utility module providing a lightweight structural matcher for Falcon.

The matcher can be used from Falcon scripts via the built‑in ``matchPattern``.
It supports matching against:
- type objects (e.g., ``int``)
- list/tuple patterns where each element is a type or nested pattern
- dict patterns where keys are compared and values are recursively matched
Any other pattern falls back to equality comparison.
"""

from typing import Any, Mapping, Sequence


def _match_sequence(value: Sequence, pattern: Sequence) -> bool:
    """Recursively match two sequences (list or tuple)."""
    if type(value) is not type(pattern) or len(value) != len(pattern):
        return False
    return all(match_pattern(v, p) for v, p in zip(value, pattern))


def _match_mapping(value: Mapping, pattern: Mapping) -> bool:
    """Recursively match two mappings (dict‑like)."""
    if set(value.keys()) != set(pattern.keys()):
        return False
    return all(match_pattern(value[k], pattern[k]) for k in pattern)


def match_pattern(value: Any, pattern: Any) -> bool:
    """Return ``True`` if *value* conforms to *pattern*.

    *pattern* can be:
    - a ``type`` object – ``isinstance`` check
    - a ``list`` or ``tuple`` – element‑wise structural match
    - a ``dict`` – key set equality and recursive value match
    - otherwise – direct equality ``value == pattern``
    """
    # Type check
    if isinstance(pattern, type):
        return isinstance(value, pattern)
    # Sequence (list/tuple) match
    if isinstance(pattern, (list, tuple)):
        if not isinstance(value, (list, tuple)):
            return False
        return _match_sequence(value, pattern)
    # Mapping (dict) match
    if isinstance(pattern, dict):
        if not isinstance(value, dict):
            return False
        return _match_mapping(value, pattern)
    # Fallback to equality
    return value == pattern

__all__ = ["match_pattern"]
