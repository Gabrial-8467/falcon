"""Utility module providing simple regex helpers for Falcon built‑ins.

The functions accept a pattern string, a target string, and optional flag integer
compatible with Python's ``re`` module (e.g., ``re.IGNORECASE``). They raise a
``ValueError`` if the pattern is invalid, which propagates as an interpreter
error.
"""

import re
from typing import List, Optional, Any


def _compile(pattern: str, flags: int = 0) -> re.Pattern:
    """Compile a regex pattern, raising ``ValueError`` on failure.

    The interpreter expects ``ValueError`` for user‑visible errors.
    """
    try:
        return re.compile(pattern, flags)
    except re.error as e:
        raise ValueError(str(e))


def match(pattern: str, string: str, flags: int = 0) -> Optional[List[Any]]:
    """Perform ``re.match`` and return a list of captured groups.

    If the pattern does not match, ``None`` is returned. The full match (group 0)
    is omitted – only the captured groups are returned, mirroring typical
    regex‑helper semantics.
    """
    regex = _compile(pattern, flags)
    m = regex.match(string)
    if not m:
        return None
    # Return captured groups; if none, return empty list
    return list(m.groups())


def search(pattern: str, string: str, flags: int = 0) -> Optional[List[Any]]:
    """Perform ``re.search`` and return a list of captured groups.

    Returns ``None`` when no match is found.
    """
    regex = _compile(pattern, flags)
    m = regex.search(string)
    if not m:
        return None
    return list(m.groups())


def findall(pattern: str, string: str, flags: int = 0) -> List[Any]:
    """Return all non‑overlapping matches.

    If the pattern contains capturing groups, a list of tuples with the groups
    is returned; otherwise a list of matching substrings.
    """
    regex = _compile(pattern, flags)
    return regex.findall(string)
