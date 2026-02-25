"""Utility module providing simple regex helpers for Falcon built‑ins.

The functions accept a pattern string, a target string, and optional flag integer
compatible with Python's ``re`` module (e.g., ``re.IGNORECASE``). They raise a
``ValueError`` if the pattern is invalid, which propagates as an interpreter
error.
"""

import re
import fnmatch
from typing import List, Optional, Any, Dict


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
    is included as the first element of the returned list.
    """
    regex = _compile(pattern, flags)
    m = regex.match(string)
    if not m:
        return None
    return [m.group(0)] + list(m.groups())


def search(pattern: str, string: str, flags: int = 0) -> Optional[List[Any]]:
    """Perform ``re.search`` and return a list of captured groups.

    If the pattern does not match, ``None`` is returned. The full match (group 0)
    is included as the first element of the returned list.
    """
    regex = _compile(pattern, flags)
    m = regex.search(string)
    if not m:
        return None
    return [m.group(0)] + list(m.groups())


def findall(pattern: str, string: str, flags: int = 0) -> List[List[Any]]:
    """Perform ``re.findall`` and return a list of match groups.

    Each match is represented as a list of its captured groups.
    """
    regex = _compile(pattern, flags)
    return [list(match) for match in regex.findall(string)]


def match_dict(pattern: str, string: str, flags: int = 0) -> Optional[Dict[str, str]]:
    """Perform ``re.match`` and return a dict of named capture groups.

    If the pattern has no named groups, an empty dict is returned.
    Returns ``None`` when the pattern does not match.
    """
    regex = _compile(pattern, flags)
    m = regex.match(string)
    if not m:
        return None
    return m.groupdict()


def glob_match(pattern: str, string: str, flags: int = 0) -> bool:
    """Match a shell‑style glob pattern against ``string``.

    ``flags`` is accepted for API compatibility but ignored.
    The function translates the glob to a regular expression using ``fnmatch.translate``
    and performs a full‑match.
    """
    # Convert glob pattern to regex pattern string
    regex_pat = fnmatch.translate(pattern)
    # Compile with DOTALL so ``**`` can span newlines if needed
    regex = re.compile(regex_pat, re.DOTALL)
    return bool(regex.fullmatch(string))
