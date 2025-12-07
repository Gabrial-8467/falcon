"""
Simple JS-like lexer for Falcon.

Features:
- // line comments, /* block comments */
- numbers (int, float), strings (single/double quotes)
- identifiers and keywords
- two-char operators: == != <= >= && ||
- special operators: declaration ':=' and method '::'
- produces Token objects from tokens.py
"""
from __future__ import annotations

from typing import List, Optional
from .tokens import Token, TokenType
from .utils.text_helpers import is_alpha, is_alnum


KEYWORDS = {
    "var": TokenType.VAR,
    "const": TokenType.CONST,
    "if": TokenType.IF,
    "else": TokenType.ELSE,
    "while": TokenType.WHILE,
    "for": TokenType.FOR,
    "loop": TokenType.LOOP,
    "to": TokenType.TO,
    "step": TokenType.STEP,
    "true": TokenType.TRUE,
    "false": TokenType.FALSE,
    "null": TokenType.NULL,
    "print": TokenType.PRINT,
    "function": TokenType.FUNCTION,
    "return": TokenType.RETURN,
}


class LexerError(Exception):
    pass


class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.start = 0         # index of token start
        self.current = 0       # index of current char
        self.lineno = 1
        self.col = 1           # column of next char (1-based)
        self.tokens: List[Token] = []

    def lex(self) -> List[Token]:
        while not self._is_at_end():
            self.start = self.current
            self._scan_token()
        # EOF token col set to last column
        self.tokens.append(Token(TokenType.EOF, "", None, self.lineno, self.col))
        return self.tokens

    def _is_at_end(self) -> bool:
        return self.current >= len(self.source)

    def _advance(self) -> str:
        ch = self.source[self.current]
        self.current += 1
        if ch == "\n":
            self.lineno += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def _peek(self) -> str:
        if self._is_at_end():
            return "\0"
        return self.source[self.current]

    def _peek_next(self) -> str:
        if self.current + 1 >= len(self.source):
            return "\0"
        return self.source[self.current + 1]

    def _add_token(self, type_: TokenType, literal: object = None):
        lexeme = self.source[self.start:self.current]
        # compute start column (1-based)
        start_col = self.col - (self.current - self.start)
        self.tokens.append(Token(type_, lexeme, literal, self.lineno, max(1, start_col)))

    def _match(self, expected: str) -> bool:
        if self._is_at_end():
            return False
        if self.source[self.current] != expected:
            return False
        self.current += 1
        # update column for matched char
        if expected == "\n":
            self.lineno += 1
            self.col = 1
        else:
            self.col += 1
        return True

    def _scan_token(self):
        c = self._advance()

        # skip whitespace (except newline handled in _advance)
        if c in " \r\n\t":
           return

        # Single-line and block comments
        if c == "/":
            if self._match("/"):
                # consume until newline or EOF
                while self._peek() != "\n" and not self._is_at_end():
                    self._advance()
                return
            if self._match("*"):
                # block comment: find closing */
                while not (self._peek() == "*" and self._peek_next() == "/"):
                    if self._is_at_end():
                        raise LexerError(f"Unterminated block comment at {self.lineno}:{self.col}")
                    self._advance()
                # consume '*/'
                self._advance()
                self._advance()
                return
            # regular slash token
            self._add_token(TokenType.SLASH)
            return

        # declaration ':=' and method '::' handling
        if c == ":":
            # ':=' declaration operator
            if self._match("="):
                self._add_token(TokenType.DECL)  # DECL for ':='
                return
            # '::' method-call operator
            if self._match(":"):
                self._add_token(TokenType.METHODCOLON)  # METHODCOLON for '::'
                return
            # single ':' is not used in current grammar; treat as error to avoid surprises
            raise LexerError(f"Unexpected ':' at {self.lineno}:{self.col}")

        # single-char tokens and simple two-char detection handled below
        single_map = {
            "{": TokenType.LBRACE, "}": TokenType.RBRACE,
            "(": TokenType.LPAREN, ")": TokenType.RPAREN,
            ";": TokenType.SEMI, ",": TokenType.COMMA,
            ".": TokenType.DOT, "+": TokenType.PLUS,
            "-": TokenType.MINUS, "*": TokenType.STAR,
            "%": TokenType.PERC, "!": TokenType.BANG,
            "<": TokenType.LT, ">": TokenType.GT,
            "=": TokenType.EQ, "&": None, "|": None,
        }

        if c in single_map:
            # handle two-char operators
            if c == "=":
                if self._match("="):
                    self._add_token(TokenType.EQEQ)
                    return
                self._add_token(TokenType.EQ)
                return
            if c == "!":
                if self._match("="):
                    self._add_token(TokenType.BANGEQ)
                    return
                self._add_token(TokenType.BANG)
                return
            if c == "<":
                if self._match("="):
                    self._add_token(TokenType.LTE)
                    return
                self._add_token(TokenType.LT)
                return
            if c == ">":
                if self._match("="):
                    self._add_token(TokenType.GTE)
                    return
                self._add_token(TokenType.GT)
                return
            if c == "&":
                if self._match("&"):
                    self._add_token(TokenType.ANDAND)
                    return
                raise LexerError(f"Unexpected single '&' at {self.lineno}:{self.col}")
            if c == "|":
                if self._match("|"):
                    self._add_token(TokenType.OROR)
                    return
                raise LexerError(f"Unexpected single '|' at {self.lineno}:{self.col}")
            # other single-char
            ttype = single_map[c]
            if ttype is not None:
                self._add_token(ttype)
                return

        # strings
        if c in ('"', "'"):
            self._string(c)
            return

        # numbers
        if c.isdigit():
            self._number()
            return

        # identifiers / keywords
        if is_alpha(c):
            self._identifier()
            return

        raise LexerError(f"Unexpected character '{c}' at {self.lineno}:{self.col}")

    def _string(self, quote: str):
        chars: List[str] = []
        while self._peek() != quote and not self._is_at_end():
            ch = self._advance()
            if ch == "\\":
                # escape sequence
                nxt = self._advance()
                if nxt == "n":
                    chars.append("\n")
                elif nxt == "t":
                    chars.append("\t")
                elif nxt == "r":
                    chars.append("\r")
                elif nxt == "\\":
                    chars.append("\\")
                elif nxt == quote:
                    chars.append(quote)
                else:
                    chars.append(nxt)
            else:
                chars.append(ch)
        if self._is_at_end():
            raise LexerError(f"Unterminated string at {self.lineno}:{self.col}")
        # consume closing quote
        self._advance()
        literal = "".join(chars)
        self._add_token(TokenType.STRING, literal)

    def _number(self):
        while self._peek().isdigit():
            self._advance()
        # fractional part
        if self._peek() == "." and self._peek_next().isdigit():
            self._advance()  # consume '.'
            while self._peek().isdigit():
                self._advance()
        text = self.source[self.start:self.current]
        value = float(text) if "." in text else int(text)
        self._add_token(TokenType.NUMBER, value)

    def _identifier(self):
        while is_alnum(self._peek()):
            self._advance()
        text = self.source[self.start:self.current]
        ttype = KEYWORDS.get(text, TokenType.IDENT)
        lit = None
        if ttype == TokenType.TRUE:
            lit = True
        elif ttype == TokenType.FALSE:
            lit = False
        elif ttype == TokenType.NULL:
            lit = None
        self._add_token(ttype, lit)
