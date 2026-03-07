"""
Formatting rules for Vyom code formatter.

Defines opinionated formatting standards for consistent code structure.
"""

from dataclasses import dataclass
from typing import Dict, Set


@dataclass
class FormattingRules:
    """Configuration for Vyom code formatting rules."""
    
    # Indentation
    indent_size: int = 4
    use_tabs: bool = False
    
    # Spacing
    space_around_operators: bool = True
    space_after_comma: bool = True
    space_before_paren: bool = False
    space_inside_parens: bool = False
    
    # Line length
    max_line_length: int = 100
    
    # Brace style (K&R)
    opening_brace_same_line: bool = True
    closing_brace_newline: bool = True
    
    # Collection formatting
    trailing_comma: bool = False
    space_inside_brackets: bool = False
    space_inside_braces: bool = True
    
    # Function formatting
    space_before_function_paren: bool = False
    space_after_function_name: bool = False
    
    # Statement formatting
    else_on_newline: bool = True
    while_on_newline: bool = True
    
    # Pattern matching
    match_indent_body: bool = True
    
    @property
    def indent_string(self) -> str:
        """Returns the indentation string based on settings."""
        return "\t" if self.use_tabs else " " * self.indent_size
    
    @property
    def binary_operators(self) -> Set[str]:
        """Operators that should have spaces around them."""
        return {
            "+", "-", "*", "/", "%", "**",
            "==", "!=", "<", "<=", ">", ">=",
            "&&", "||", "&", "|", "^",
            "=", "+=", "-=", "*=", "/=", "%=",
            "->", "<-", "=>"
        }
    
    @property
    def unary_operators(self) -> Set[str]:
        """Operators that should not have spaces after them."""
        return {"!", "~", "++", "--"}
    
    def should_space_around_operator(self, op: str) -> bool:
        """Determine if an operator should have spaces around it."""
        return self.space_around_operators and op in self.binary_operators
    
    def should_space_after_comma(self) -> bool:
        """Determine if there should be space after commas."""
        return self.space_after_comma
