"""
Small helper functions used by the Falcon lexer and parser.

These isolate character checks so the lexer remains clean and easy to extend.
"""

from __future__ import annotations


def is_alpha(ch: str) -> bool:
    """
    True if character is a valid start of an identifier.
    Falcon follows JS-like rules:
      - letters A–Z, a–z
      - underscore _
      - dollar sign $
    """
    if not ch:
        return False
    return (
        ("a" <= ch <= "z") or
        ("A" <= ch <= "Z") or
        ch == "_" or
        ch == "$"
    )


def is_alnum(ch: str) -> bool:
    """
    True if character is a valid part of an identifier.
    Includes:
      - letters
      - digits 0–9
      - underscore _
      - dollar sign $
    """
    if not ch:
        return False
    return (
        ("a" <= ch <= "z") or
        ("A" <= ch <= "Z") or
        ("0" <= ch <= "9") or
        ch == "_" or
        ch == "$"
    )
