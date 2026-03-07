"""
Vyom Code Formatter

Passive AST-based formatter that automatically normalizes Vyom code
during execution without requiring manual CLI commands.
"""

from .formatter import VyomFormatter
from .printer import Printer
from .rules import FormattingRules

__all__ = ["VyomFormatter", "Printer", "FormattingRules"]
