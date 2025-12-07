# file: src/falcon/parser.py
"""
Recursive-descent parser for Falcon (JS-like).

Produces a list of Stmt AST nodes from a token stream produced by lexer.Lexer.
Supports assignment expressions (right-associative) and var/const declarations
with the ':=' declaration operator (DECL). Backwards-compatible with 'let' and '='.
Adds Falcon-specific `for` and `loop` statements and supports METHODCOLON `::` member access.
"""
from __future__ import annotations

from typing import List, Optional
from .tokens import Token, TokenType
from .ast_nodes import (
    Expr, Literal, Variable, Binary, Unary, Grouping, Call, Member, FunctionExpr, Assign,
    Stmt, ExprStmt, LetStmt, PrintStmt, BlockStmt, IfStmt, WhileStmt,
    FunctionStmt, ReturnStmt,  # existing
    ForStmt, LoopStmt,        # NEW: loop nodes
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
        # Accept legacy 'let' for backward compatibility, plus new 'var' and 'const'
        if self._match(TokenType.VAR):
            return self._var_or_const_declaration(is_const=False)
        if self._match(TokenType.CONST):
            return self._var_or_const_declaration(is_const=True)
        if self._match(TokenType.FUNCTION):
            return self._function_declaration()
        return self._statement()

    def _var_or_const_declaration(self, is_const: bool) -> Stmt:
        """
        Parse:
          var NAME := expr ;
          const NAME := expr ;
        Backwards compatible with:
          let NAME = expr ;
          var NAME = expr ;
        """
        name_tok = self._consume(TokenType.IDENT, "Expect variable name after declaration")
        name = name_tok.lexeme
        initializer: Optional[Expr] = None

        # Prefer ':=' (DECL) for new syntax, but accept '=' as fallback for compatibility.
        if self._match(TokenType.DECL):
            initializer = self._expression()
        elif self._match(TokenType.EQ):
            initializer = self._expression()
        # semicolon optional
        self._optional_semicolon()
        return LetStmt(name, initializer, is_const=is_const)

    def _function_declaration(self) -> Stmt:
        # we've consumed 'function'
        name_tok = self._consume(TokenType.IDENT, "Expect function name after 'function'")
        name = name_tok.lexeme
        params = self._parse_params()
        body = self._parse_block()
        return FunctionStmt(name, params, body)

    # ---- statements ----
    def _statement(self) -> Stmt:
        if self._match(TokenType.SHOW):
           expr = self._expression()
           self._optional_semicolon()
           return PrintStmt(expr)  # same AST node, new keyword

        if self._match(TokenType.RETURN):
            # return statement
            val: Optional[Expr] = None
            if not self._check(TokenType.SEMI) and not self._check(TokenType.RBRACE) and not self._is_at_end():
                val = self._expression()
            self._optional_semicolon()
            return ReturnStmt(val)
        if self._match(TokenType.IF):
            return self._if_statement()
        if self._match(TokenType.WHILE):
            return self._while_statement()
        if self._match(TokenType.FOR):
            return self._for_statement()
        if self._match(TokenType.LOOP):
            return self._loop_statement()
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

    # ---- NEW: for / loop parsing ----
    def _for_statement(self) -> Stmt:
        """
        Parse Falcon for syntax:
          for var i := START to END [step STEP] { ... }
        'var' is required to declare the loop variable (keeps semantics simple).
        """
        # require 'var' keyword for loop iterator declaration
        if not self._match(TokenType.VAR):
            raise ParseError("Expect 'var' in for-loop header (e.g. for var i := 0 to 10 { ... })")

        name_tok = self._consume(TokenType.IDENT, "Expect loop variable name after 'var'")
        name = name_tok.lexeme

        # initializer: prefer ':=' (DECL) but accept '=' for compatibility
        if self._match(TokenType.DECL):
            start_expr = self._expression()
        elif self._match(TokenType.EQ):
            start_expr = self._expression()
        else:
            raise ParseError("Expect ':=' or '=' initializer in for-loop (e.g. var i := 0)")

        # require 'to' keyword
        self._consume(TokenType.TO, "Expect 'to' in for-loop header (e.g. to 10)")

        end_expr = self._expression()

        step_expr: Optional[Expr] = None
        if self._match(TokenType.STEP):
            step_expr = self._expression()

        # body
        body = self._block_or_statement()
        # body is BlockStmt or Stmt; ensure BlockStmt for uniformity
        if isinstance(body, BlockStmt):
            block = body
        else:
            block = BlockStmt([body])

        return ForStmt(name, start_expr, end_expr, step_expr, block)

    def _loop_statement(self) -> Stmt:
        """
        Parse infinite loop:
          loop { ... }
        """
        body = self._block_or_statement()
        if isinstance(body, BlockStmt):
            block = body
        else:
            block = BlockStmt([body])
        return LoopStmt(block)

    # ---- expressions (assignment + precedence climbing) ----
    def _expression(self) -> Expr:
        return self._assignment()

    def _assignment(self) -> Expr:
        # Parse left-hand side as binary/expression
        expr = self._binary_expression(0)
        # If there's an '=' token, parse right-hand side as assignment (right-associative)
        if self._match(TokenType.EQ):
            value = self._assignment()
            # Only Variables and Members are valid assignment targets
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
        return self._postfix()

    def _postfix(self) -> Expr:
        """
        Parse primary expressions then handle postfix operators:
         - member access: .ident or ::ident
         - function call: (arg, ...)
        These can be chained: obj.fn(1).other() or obj::method(1)::other()
        """
        expr = self._primary()

        while True:
            # function call
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

            # member access (dot or double-colon)
            if self._match(TokenType.DOT) or self._match(TokenType.METHODCOLON):
                name_tok = self._consume(TokenType.IDENT, "Expect property name after '.' or '::'")
                expr = Member(expr, name_tok.lexeme)
                continue

            break

        return expr

    def _primary(self) -> Expr:
        # function expression (anonymous or named)
        if self._match(TokenType.FUNCTION):
            # anonymous function expression or named function expression
            name: Optional[str] = None
            if self._check(TokenType.IDENT):
                name = self._advance().lexeme
            params = self._parse_params()
            body = self._parse_block()
            # function expression returns a FunctionExpr
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

    # ---- helpers ----
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
        # require a block for function bodies
        if not self._match(TokenType.LBRACE):
            raise ParseError("Expect '{' before function body")
        body = self._block()
        return BlockStmt(body)

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
