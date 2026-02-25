"""
Utility helpers for the Falcon language.

This package contains:
- errors.py       → custom exception classes & pretty formatting
- file_loader.py  → safe file loading helpers
- text_helpers.py → small text/char utilities for lexer & parser
"""

from .text_helpers import is_alpha, is_alnum
from .text_helpers import is_alpha, is_alnum
from .file_loader import load_file
from .pattern_match import match, search, findall


__all__ = [
    "regex_match",
    "regex_search",
    "regex_findall",

    "FalconError",
    "load_file",
    "is_alpha",
    "is_alnum",
    "match",
    "search",
    "findall",
]
