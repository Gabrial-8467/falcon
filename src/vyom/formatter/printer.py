"""
Printer for Vyom formatter.

Handles structured output generation with proper indentation and line management.
"""

from typing import List, Optional, TextIO
from .rules import FormattingRules


class Printer:
    """Manages formatted output with indentation and line length control."""
    
    def __init__(self, rules: FormattingRules, output: Optional[TextIO] = None):
        self.rules = rules
        self.output = output
        self.indent_level = 0
        self.lines: List[str] = []
        self.current_line = ""
        self.needs_indent = True
    
    def indent(self) -> None:
        """Increase indentation level."""
        self.indent_level += 1
    
    def dedent(self) -> None:
        """Decrease indentation level."""
        if self.indent_level > 0:
            self.indent_level -= 1
    
    def write(self, text: str) -> None:
        """Write text to current line."""
        if self.needs_indent and text.strip():
            self.current_line += self.rules.indent_string * self.indent_level
            self.needs_indent = False
        self.current_line += text
    
    def newline(self) -> None:
        """End current line and start a new one."""
        if self.current_line.strip():
            self.lines.append(self.current_line.rstrip())
        self.current_line = ""
        self.needs_indent = True
    
    def space(self) -> None:
        """Add a space if not at line start."""
        if not self.needs_indent:
            self.write(" ")
    
    def write_with_spaces(self, text: str, space_before: bool = False, space_after: bool = False) -> None:
        """Write text with optional spacing."""
        if space_before:
            self.space()
        self.write(text)
        if space_after:
            self.space()
    
    def write_operator(self, op: str) -> None:
        """Write an operator with proper spacing."""
        if self.rules.should_space_around_operator(op):
            self.space()
            self.write(op)
            self.space()
        else:
            self.write(op)
    
    def write_comma(self) -> None:
        """Write a comma with proper spacing."""
        self.write(",")
        if self.rules.should_space_after_comma():
            self.space()
    
    def write_parenthesized(self, content_func, space_inside: bool = False) -> None:
        """Write content inside parentheses."""
        self.write("(")
        if space_inside:
            self.space()
        content_func()
        if space_inside:
            self.space()
        self.write(")")
    
    def write_bracketed(self, content_func, space_inside: bool = False) -> None:
        """Write content inside brackets."""
        self.write("[")
        if space_inside:
            self.space()
        content_func()
        if space_inside:
            self.space()
        self.write("]")
    
    def write_braced(self, content_func, space_inside: bool = True) -> None:
        """Write content inside braces."""
        self.write("{")
        if space_inside:
            self.space()
        content_func()
        if space_inside:
            self.space()
        self.write("}")
    
    def write_block(self, statements_func, same_line_open: bool = True) -> None:
        """Write a block of statements."""
        if same_line_open:
            self.space()
            self.write("{")
            self.newline()
        else:
            self.newline()
            self.write("{")
            self.newline()
        
        self.indent()
        statements_func()
        self.dedent()
        
        self.write("}")
        self.newline()
    
    def get_formatted_text(self) -> str:
        """Get the complete formatted text."""
        return "\n".join(self.lines)
    
    def reset(self) -> None:
        """Reset the printer state."""
        self.lines.clear()
        self.current_line = ""
        self.indent_level = 0
        self.needs_indent = True
