# file: src/falcon/parser.py
"""
Recursive-descent parser for Falcon.

Produces a list of Stmt AST nodes from a token stream produced by lexer.Lexer.

Grammar highlights handled here:
  - var / const declarations (var NAME := expr or var NAME = expr)
  - function declarations: function name(params) { ... }
  - function expressions: function (name?) (params) { ... }
  - for-loops: for var i := START to END [step STEP] { ... }
  - infinite loops: loop { ... }
  - if / while / return
  - assignment expressions (right-associative)
  - member access and calls (postfix)
"""

from __future__ import annotations
from typing import List, Optional

from .tokens import Token, TokenType
from .ast_nodes import (
    Expr, Literal, Variable, Binary, Unary, Grouping, Call, Member, FunctionExpr, Assign,
    Stmt, ExprStmt, LetStmt, PrintStmt, BlockStmt, IfStmt, WhileStmt,
    FunctionStmt, ReturnStmt, ForStmt, LoopStmt, BreakStmt
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

    # ---------------- top-level ----------------
    def _declaration(self) -> Stmt:
        # handle explicit keywords first
        if self._match(TokenType.VAR):
            return self._var_or_const_declaration(is_const=False)
        if self._match(TokenType.CONST):
            return self._var_or_const_declaration(is_const=True)
        if self._match(TokenType.FUNCTION):
            return self._function_declaration()
        if self._match(TokenType.LET):
            return self._var_or_const_declaration(is_const=False)
        # We only treat this as a declaration when the current token is IDENT and
        # the next token is DECL. Don't consume anything unless we're sure.
        if self._check(TokenType.IDENT) and self._peek_next().type == TokenType.DECL:
            # consume IDENT and DECL then parse initializer expression
            name_tok = self._advance()   # consume IDENT
            self._advance()              # consume DECL (':=')
            initializer = self._expression()
            self._optional_semicolon()
            return LetStmt(name_tok.lexeme, initializer, is_const=False, is_var=True)

        return self._statement()

    def _var_or_const_declaration(self, is_const: bool) -> Stmt:
        name_tok = self._consume(TokenType.IDENT, "Expect variable name after declaration")
        name = name_tok.lexeme
        initializer: Optional[Expr] = None

        # Prefer ':=' (DECL) new syntax, but accept '=' as fallback
        if self._match(TokenType.DECL):
            initializer = self._expression()
        elif self._match(TokenType.EQ):
            initializer = self._expression()

        self._optional_semicolon()
        return LetStmt(name, initializer, is_const=is_const, is_var=False)

    def _function_declaration(self) -> Stmt:
        name_tok = self._consume(TokenType.IDENT, "Expect function name after 'function'")
        name = name_tok.lexeme
        params = self._parse_params()
        body = self._parse_block()
        return FunctionStmt(name, params, body)

    # ---------------- statements ----------------
    def _statement(self) -> Stmt:
        # return
        if self._match(TokenType.RETURN):
            val: Optional[Expr] = None
            if not self._check(TokenType.SEMI) and not self._check(TokenType.RBRACE) and not self._is_at_end():
                val = self._expression()
            self._optional_semicolon()
            return ReturnStmt(val)

        # if
        if self._match(TokenType.IF):
            return self._if_statement()

        # while
        if self._match(TokenType.WHILE):
            return self._while_statement()

        # for-loop (Falcon style)
        if self._match(TokenType.FOR):
            return self._for_statement()

        # loop (infinite)
        if self._match(TokenType.LOOP):
            self._consume(TokenType.LBRACE, "Expect '{' after 'loop'")
            body_stmts = self._block()
            return LoopStmt(BlockStmt(body_stmts))

        # break
        if self._match(TokenType.BREAK):
            # consume optional semicolon/newline and return BreakStmt
            token = self._previous()
            self._optional_semicolon()
            return BreakStmt(token)

        # block
        if self._match(TokenType.LBRACE):
            return BlockStmt(self._block())

        # expression statement (calls, assignments, etc.)
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

    def _for_statement(self) -> Stmt:
        """
        Parse Falcon-style for:
          for var i := START to END [step STEP] { ... }
        """
        # require 'var' in header (design choice); accept IDENT if user omitted
        if self._match(TokenType.VAR):
            name_tok = self._consume(TokenType.IDENT, "Expect iterator name in for-loop")
        else:
            # allow 'for i := ...' as permissive alternative
            name_tok = self._consume(TokenType.IDENT, "Expect iterator name in for-loop")
        iter_name = name_tok.lexeme

        # expect declaration operator ':=' or '='
        if self._match(TokenType.DECL):
            start_expr = self._expression()
        elif self._match(TokenType.EQ):
            start_expr = self._expression()
        else:
            raise ParseError("Expect ':=' or '=' after iterator name in for-loop")

        # expect 'to' keyword
        self._consume(TokenType.TO, "Expect 'to' in for-loop header")
        end_expr = self._expression()

        # optional 'step' clause
        step_expr: Optional[Expr] = None
        if self._match(TokenType.STEP):
            step_expr = self._expression()

        # require block body
        body = self._parse_block()
        return ForStmt(iter_name, start_expr, end_expr, step_expr, body)

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

    # ---------------- expressions ----------------
    def _expression(self) -> Expr:
        return self._assignment()

    def _assignment(self) -> Expr:
        expr = self._binary_expression(0)
        if self._match(TokenType.EQ):
            value = self._assignment()
            if isinstance(expr, Variable) or isinstance(expr, Member):
                return Assign(expr, value)
            raise ParseError(f"Invalid assignment target at {self._previous()}")
        return expr

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
            # parse right with precedence
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
        return self._postfix()

    def _postfix(self) -> Expr:
        """
        Handle primary expressions and chained postfix operations:
         - call: (...) 
         - member: .ident
        """
        expr = self._primary()
        while True:
            if self._match(TokenType.LPAREN):
                args: List[Expr] = []
                if not self._check(TokenType.RPAREN):
                    while True:
                        args.append(self._expression())
                        if self._match(TokenType.COMMA):
                            continue
                        break
                self._consume(TokenType.RPAREN, "Expect ')' after arguments")
                expr = Call(expr, args)
                continue

            if self._match(TokenType.DOT):
                name_tok = self._consume(TokenType.IDENT, "Expect property name after '.'")
                expr = Member(expr, name_tok.lexeme)
                continue

            break
        return expr

    def _primary(self) -> Expr:
        # function expression
        if self._match(TokenType.FUNCTION):
            name: Optional[str] = None
            if self._check(TokenType.IDENT):
                name = self._advance().lexeme
            params = self._parse_params()
            body = self._parse_block()
            return FunctionExpr(name, params, body)

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
            return Grouping(expr)

        raise ParseError(f"Unexpected token: {self._peek()}")

    # ---------------- helpers ----------------
    def _parse_params(self) -> List[str]:
        self._consume(TokenType.LPAREN, "Expect '(' before parameter list")
        params: List[str] = []
        if not self._check(TokenType.RPAREN):
            while True:
                tok = self._consume(TokenType.IDENT, "Expect parameter name")
                params.append(tok.lexeme)
                if self._match(TokenType.COMMA):
                    continue
                break
        self._consume(TokenType.RPAREN, "Expect ')' after parameter list")
        return params

    def _parse_block(self) -> BlockStmt:
        if not self._match(TokenType.LBRACE):
            raise ParseError("Expect '{' before function body")
        body_stmts = self._block()
        return BlockStmt(body_stmts)

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
        # Accept semicolon if present; optional otherwise.
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

    def _peek_next(self) -> Token:
        idx = self.current + 1
        if idx >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[idx]


    def _previous(self) -> Token:
        return self.tokens[self.current - 1]
