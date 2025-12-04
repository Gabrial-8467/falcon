"""
Recursive-descent parser for Falcon (JS-like syntax).

Produces a list of Stmt AST nodes from a token stream produced by lexer.Lexer.
"""
from __future__ import annotations

from typing import List, Optional
from .tokens import Token, TokenType
from .ast_nodes import (
    Expr, Literal, Variable, Binary, Unary,
    Stmt, ExprStmt, LetStmt, PrintStmt, BlockStmt, IfStmt, WhileStmt
)
from .precedence import PREC


class ParseError(Exception):
    pass


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.current = 0

    def parse(self) -> List[Stmt]:
        stmts: List[Stmt] = []
        while not self._is_at_end():
            stmts.append(self._declaration())
        return stmts

    # ---- top-level declarations ----
    def _declaration(self) -> Stmt:
        if self._match(TokenType.LET):
            return self._let_declaration()
        return self._statement()

    def _let_declaration(self) -> Stmt:
        name_tok = self._consume(TokenType.IDENT, "Expect variable name after 'let'")
        name = name_tok.lexeme
        initializer: Optional[Expr] = None
        if self._match(TokenType.EQ):
            initializer = self._expression()
        self._optional_semicolon()
        return LetStmt(name, initializer)

    # ---- statements ----
    def _statement(self) -> Stmt:
        if self._match(TokenType.PRINT):
            expr = self._expression()
            self._optional_semicolon()
            return PrintStmt(expr)
        if self._match(TokenType.IF):
            return self._if_statement()
        if self._match(TokenType.WHILE):
            return self._while_statement()
        if self._match(TokenType.LBRACE):
            return BlockStmt(self._block())
        # expression statement
        expr = self._expression()
        self._optional_semicolon()
        return ExprStmt(expr)

    def _if_statement(self) -> Stmt:
        self._consume(TokenType.LPAREN, "Expect '(' after 'if'")
        cond = self._expression()
        self._consume(TokenType.RPAREN, "Expect ')' after if condition")
        then_branch = self._block_or_statement()
        else_branch: Optional[Stmt] = None
        if self._match(TokenType.ELSE):
            else_branch = self._block_or_statement()
        return IfStmt(cond, then_branch, else_branch)

    def _while_statement(self) -> Stmt:
        self._consume(TokenType.LPAREN, "Expect '(' after 'while'")
        cond = self._expression()
        self._consume(TokenType.RPAREN, "Expect ')' after while condition")
        body = self._block_or_statement()
        return WhileStmt(cond, body)

    def _block_or_statement(self) -> Stmt:
        if self._match(TokenType.LBRACE):
            return BlockStmt(self._block())
        return self._statement()

    def _block(self) -> List[Stmt]:
        stmts: List[Stmt] = []
        while not self._check(TokenType.RBRACE) and not self._is_at_end():
            stmts.append(self._declaration())
        self._consume(TokenType.RBRACE, "Expect '}' after block")
        return stmts

    # ---- expressions (precedence climbing) ----
    def _expression(self) -> Expr:
        return self._binary_expression(0)

    def _binary_expression(self, min_prec: int) -> Expr:
        expr = self._unary()
        while True:
            op_token = self._peek()
            op_text = None
            if op_token.type in (
                TokenType.PLUS, TokenType.MINUS, TokenType.STAR, TokenType.SLASH, TokenType.PERC,
                TokenType.EQEQ, TokenType.BANGEQ, TokenType.LT, TokenType.LTE, TokenType.GT, TokenType.GTE,
                TokenType.ANDAND, TokenType.OROR
            ):
                op_text = self._token_to_op(op_token)
            if op_text is None:
                break
            prec = PREC.get(op_text, 0)
            if prec < min_prec:
                break
            # consume operator
            self._advance()
            # parse right-hand side with higher precedence for left-assoc
            right = self._binary_expression(prec + 1)
            expr = Binary(expr, op_text, right)
        return expr

    def _unary(self) -> Expr:
        if self._match(TokenType.BANG):
            operand = self._unary()
            return Unary("!", operand)
        if self._match(TokenType.MINUS):
            operand = self._unary()
            return Unary("-", operand)
        return self._primary()

    def _primary(self) -> Expr:
        if self._match(TokenType.NUMBER):
            return Literal(self._previous().literal)
        if self._match(TokenType.STRING):
            return Literal(self._previous().literal)
        if self._match(TokenType.TRUE):
            return Literal(True)
        if self._match(TokenType.FALSE):
            return Literal(False)
        if self._match(TokenType.NULL):
            return Literal(None)
        if self._match(TokenType.IDENT):
            return Variable(self._previous().lexeme)
        if self._match(TokenType.LPAREN):
            expr = self._expression()
            self._consume(TokenType.RPAREN, "Expect ')' after expression")
            return expr
        raise ParseError(f"Unexpected token: {self._peek()}")

    # ---- utilities ----
    def _token_to_op(self, token: Token) -> Optional[str]:
        mapping = {
            TokenType.PLUS: "+", TokenType.MINUS: "-", TokenType.STAR: "*", TokenType.SLASH: "/",
            TokenType.PERC: "%", TokenType.EQEQ: "==", TokenType.BANGEQ: "!=", TokenType.LT: "<",
            TokenType.LTE: "<=", TokenType.GT: ">", TokenType.GTE: ">=", TokenType.ANDAND: "&&",
            TokenType.OROR: "||",
        }
        return mapping.get(token.type)

    def _match(self, *types: TokenType) -> bool:
        for t in types:
            if self._check(t):
                self._advance()
                return True
        return False

    def _consume(self, ttype: TokenType, message: str) -> Token:
        if self._check(ttype):
            return self._advance()
        raise ParseError(message + f" at {self._peek()}")

    def _optional_semicolon(self):
        # Accept a semicolon if present; otherwise continue (semicolon optional).
        if self._match(TokenType.SEMI):
            return

    def _check(self, ttype: TokenType) -> bool:
        if self._is_at_end():
            return False
        return self._peek().type == ttype

    def _advance(self) -> Token:
        if not self._is_at_end():
            self.current += 1
        return self._previous()

    def _is_at_end(self) -> bool:
        return self._peek().type == TokenType.EOF

    def _peek(self) -> Token:
        return self.tokens[self.current]

    def _previous(self) -> Token:
        return self.tokens[self.current - 1]
