<<<<<<< HEAD
"""Utility module providing simple regex helpers for Falcon built‑ins.

The functions accept a pattern string, a target string, and optional flag integer
compatible with Python's ``re`` module (e.g., ``re.IGNORECASE``). They raise a
``ValueError`` if the pattern is invalid, which propagates as an interpreter
error.
"""

import re
import fnmatch
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


def match_dict(pattern: str, string: str, flags: int = 0) -> Optional[Dict[str, str]]:
    """Return a dict of named capture groups.

    If the pattern has no named groups, an empty dict is returned.
    Returns ``None`` when the pattern does not match.
    """
    regex = _compile(pattern, flags)
    m = regex.match(string)
    if not m:
        return None
    return m.groupdict()


def glob_match(pattern: str, string: str, flags: int = 0) -> bool:
    """Match *string* against a shell‑style glob *pattern*.

    Flags are accepted for signature compatibility but are ignored.
    """
    # Translate the glob to a regular expression; fnmatch.translate adds a trailing \Z(?ms)
    regex_pat = fnmatch.translate(pattern)
    # Compile with DOTALL so ** can span newlines if needed
    regex = re.compile(regex_pat, re.DOTALL)
    return bool(regex.fullmatch(string))



def match_dict(pattern: str, string: str, flags: int = 0) -> Optional[Dict[str, str]]:
    """Perform ``re.match`` and return a dict of named capture groups.

    If the pattern contains no named groups, an empty dict is returned.
    If the pattern does not match, ``None`` is returned.
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
=======
import re

def match(pattern: str, string: str, flags: int = 0):
    """Return a re.Match object if the pattern matches the start of the string, else None.
    Mirrors Python's re.match.
    """
    return re.match(pattern, string, flags)

def search(pattern: str, string: str, flags: int = 0):
    """Return a re.Match object for the first occurrence of the pattern in the string, else None.
    Mirrors Python's re.search.
    """
    return re.search(pattern, string, flags)

def findall(pattern: str, string: str, flags: int = 0):
    """Return a list of all non‑overlapping matches of the pattern in the string.
    Mirrors Python's re.findall.
    """
    return re.findall(pattern, string, flags)
>>>>>>> worktree-agent-ac3a1c25
