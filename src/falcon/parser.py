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
    ListLiteral, TupleLiteral, DictLiteral, SetLiteral, ArrayLiteral, Subscript,
    Stmt, ExprStmt, LetStmt, PrintStmt, BlockStmt, IfStmt, WhileStmt, TypeAnnotation,
    FunctionStmt, ReturnStmt, ForStmt, LoopStmt, BreakStmt, ThrowStmt, TryCatchStmt,
    # Pattern matching nodes
    Pattern, LiteralPattern, VariablePattern, TypePattern, ListPattern, TuplePattern,
    DictPattern, OrPattern, WildcardPattern, CaseArm, MatchExpr, MatchStmt
)
from .precedence import PREC


class ParseError(Exception):
    pass


class Parser:
    def __init__(self, tokens: List[Token]) -> None:
        self.tokens: List[Token] = tokens
        self.current: int = 0

    def parse(self) -> List[Stmt]:
        stmts: List[Stmt] = []
        while not self._is_at_end():
            stmts.append(self._declaration())
        return stmts

    # ---------------- top-level ----------------
    def _declaration(self) -> Stmt:
        # handle explicit keywords first
        if self._match(TokenType.VAR):
            return self._var_or_const_declaration(is_const=False, is_var=True)
        if self._check(TokenType.SET) and self._peek_next().type == TokenType.IDENT:
            self._advance()
            return self._var_or_const_declaration(is_const=False, is_var=False)
        if self._match(TokenType.CONST):
            return self._var_or_const_declaration(is_const=True, is_var=False)
        if self._match(TokenType.FUNCTION):
            return self._function_declaration()
        if self._match(TokenType.LET):
            return self._var_or_const_declaration(is_const=False, is_var=False)
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

    def _var_or_const_declaration(self, is_const: bool, is_var: bool) -> Stmt:
        declarations: List[Stmt] = []
        
        while True:
            name_tok = self._consume(TokenType.IDENT, "Expect variable name after declaration")
            name = name_tok.lexeme
            type_ann: Optional[TypeAnnotation] = None
            if self._match(TokenType.COLON):
                type_ann = self._parse_type_annotation()
            initializer: Optional[Expr] = None

            # Prefer ':=' (DECL) new syntax, but accept '=' as fallback
            if self._match(TokenType.DECL):
                initializer = self._expression()
            elif self._match(TokenType.EQ):
                initializer = self._expression()

            declarations.append(
                LetStmt(name, initializer, is_const=is_const, is_var=is_var, type_ann=type_ann)
            )
            
            # Check for comma for multiple declarations
            if not self._match(TokenType.COMMA):
                break
        
        self._optional_semicolon()
        
        # Return multiple statements as a block
        if len(declarations) == 1:
            return declarations[0]
        else:
            return BlockStmt(declarations)

    def _function_declaration(self) -> Stmt:
        name_tok = self._consume(TokenType.IDENT, "Expect function name after 'function'")
        name = name_tok.lexeme
        params, param_types = self._parse_params()
        return_type: Optional[TypeAnnotation] = None
        if self._match(TokenType.COLON):
            return_type = self._parse_type_annotation()
        elif self._match(TokenType.EQ):
            self._consume(TokenType.GT, "Expect '>' in function return annotation '=> type'")
            return_type = self._parse_type_annotation()
        body = self._parse_block()
        return FunctionStmt(name, params, body, param_types=param_types, return_type=return_type)

    # ---------------- statements ----------------
    def _statement(self) -> Stmt:
        # return
        if self._match(TokenType.RETURN):
            val: Optional[Expr] = None
            if not self._check(TokenType.SEMI) and not self._check(TokenType.RBRACE) and not self._is_at_end():
                val = self._expression()
            self._optional_semicolon()
            return ReturnStmt(val)

        if self._match(TokenType.SAY):
            val = self._expression()
            self._optional_semicolon()
            return ExprStmt(Call(Variable("show"), [val]))

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
            if self._match(TokenType.LBRACE):
                body_stmts = self._block()
                return LoopStmt(BlockStmt(body_stmts))
            cond = self._expression()
            body = self._parse_block()
            return WhileStmt(cond, body)

        # break
        if self._match(TokenType.BREAK):
            # consume optional semicolon/newline and return BreakStmt
            token = self._previous()
            self._optional_semicolon()
            return BreakStmt(token)

        # throw
        if self._match(TokenType.THROW):
            value = self._expression()
            self._optional_semicolon()
            return ThrowStmt(value)

        # try/catch
        if self._match(TokenType.TRY):
            return self._try_catch_statement()

        # match statement
        if self._match(TokenType.MATCH):
            return self._match_statement()

        # block
        if self._match(TokenType.LBRACE):
            return BlockStmt(self._block())

        # expression statement (calls, assignments, etc.)
        expr = self._expression()
        self._optional_semicolon()
        return ExprStmt(expr)

    def _if_statement(self) -> Stmt:
        if self._match(TokenType.LPAREN):
            cond = self._expression()
            self._consume(TokenType.RPAREN, "Expect ')' after if condition")
        else:
            cond = self._expression()
        then_branch = self._block_or_statement()
        else_branch: Optional[Stmt] = None
        if self._match(TokenType.ELSE):
            else_branch = self._block_or_statement()
        return IfStmt(cond, then_branch, else_branch)

    def _while_statement(self) -> Stmt:
        if self._match(TokenType.LPAREN):
            cond = self._expression()
            self._consume(TokenType.RPAREN, "Expect ')' after while condition")
        else:
            cond = self._expression()
        body = self._block_or_statement()
        return WhileStmt(cond, body)

    def _try_catch_statement(self) -> Stmt:
        try_block = self._parse_block()
        self._consume(TokenType.CATCH, "Expect 'catch' after try block")
        self._consume(TokenType.LPAREN, "Expect '(' after 'catch'")
        catch_name = self._consume(TokenType.IDENT, "Expect identifier in catch clause").lexeme
        self._consume(TokenType.RPAREN, "Expect ')' after catch identifier")
        catch_block = self._parse_block()
        return TryCatchStmt(try_block, catch_name, catch_block)

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
        if self._match(TokenType.EQ) or self._match(TokenType.DECL):
            value = self._assignment()
            if isinstance(expr, Variable) or isinstance(expr, Member) or isinstance(expr, Subscript):
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
         - subscript: [expr]
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

            if self._match(TokenType.LBRACKET):
                index_expr = self._expression()
                self._consume(TokenType.RBRACKET, "Expect ']' after subscript index")
                expr = Subscript(expr, index_expr)
                continue

            break
        return expr

    def _primary(self) -> Expr:
        # match expression
        if self._match(TokenType.MATCH):
            return self._match_expression()
        
        # function expression
        if self._match(TokenType.FUNCTION):
            name: Optional[str] = None
            if self._check(TokenType.IDENT):
                name = self._advance().lexeme
            params, param_types = self._parse_params()
            return_type: Optional[TypeAnnotation] = None
            if self._match(TokenType.COLON):
                return_type = self._parse_type_annotation()
            elif self._match(TokenType.EQ):
                self._consume(TokenType.GT, "Expect '>' in function return annotation '=> type'")
                return_type = self._parse_type_annotation()
            body = self._parse_block()
            return FunctionExpr(
                name, params, body, param_types=param_types, return_type=return_type
            )

        # collection literals
        if self._match(TokenType.LBRACKET):
            return self._list_literal()
        
        if self._match(TokenType.LPAREN):
            # Tuple literal or grouping
            if self._check(TokenType.RPAREN):
                self._advance()
                return TupleLiteral([])
            
            # Check if this is a tuple by looking ahead
            elements: List[Expr] = []
            elements.append(self._expression())
            
            if self._match(TokenType.COMMA):
                # Tuple: (expr1, expr2, ...)
                while not self._check(TokenType.RPAREN) and not self._is_at_end():
                    elements.append(self._expression())
                    if not self._match(TokenType.COMMA):
                        break
                self._consume(TokenType.RPAREN, "Expect ')' after tuple")
                return TupleLiteral(elements)
            else:
                # Grouping: (expr)
                self._consume(TokenType.RPAREN, "Expect ')' after grouping")
                return Grouping(elements[0])

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

        # set literal: set{...}
        if self._match(TokenType.SET):
            self._consume(TokenType.LBRACE, "Expect '{' after 'set'")
            return self._set_literal()
        
        # array literal: array[...]
        if self._match(TokenType.ARRAY):
            self._consume(TokenType.LBRACKET, "Expect '[' after 'array'")
            return self._array_literal()
        
        # dict literal: {...}
        if self._match(TokenType.LBRACE):
            return self._dict_literal()

        raise ParseError(f"Unexpected token: {self._peek()}")

    # ---------------- literal parsing helpers ----------------
    def _list_literal(self) -> Expr:
        elements: List[Expr] = []
        if not self._check(TokenType.RBRACKET):
            while True:
                elements.append(self._expression())
                if not self._match(TokenType.COMMA):
                    break
        self._consume(TokenType.RBRACKET, "Expect ']' after list literal")
        return ListLiteral(elements)

    def _set_literal(self) -> Expr:
        elements: List[Expr] = []
        if not self._check(TokenType.RBRACE):
            while True:
                elements.append(self._expression())
                if not self._match(TokenType.COMMA):
                    break
        self._consume(TokenType.RBRACE, "Expect '}' after set literal")
        return SetLiteral(elements)

    def _array_literal(self) -> Expr:
        size_expr = self._expression()
        self._consume(TokenType.RBRACKET, "Expect ']' after array size expression")
        return ArrayLiteral(size_expr)

    def _dict_literal(self) -> Expr:
        entries: List[tuple[Expr, Expr]] = []
        if not self._check(TokenType.RBRACE):
            while True:
                # parse key
                if self._match(TokenType.STRING):
                    key_expr = Literal(self._previous().literal)
                elif self._match(TokenType.IDENT):
                    key_expr = Literal(self._previous().lexeme)
                else:
                    raise ParseError("Expected string or identifier as dict key")
                self._consume(TokenType.COLON, "Expect ':' after dict key")
                value_expr = self._expression()
                entries.append((key_expr, value_expr))
                if not self._match(TokenType.COMMA):
                    break
        self._consume(TokenType.RBRACE, "Expect '}' after dict literal")
        return DictLiteral(entries)

    # ---------------- helpers ----------------
    def _parse_params(self) -> tuple[List[str], dict[str, TypeAnnotation]]:
        self._consume(TokenType.LPAREN, "Expect '(' before parameter list")
        params: List[str] = []
        param_types: dict[str, TypeAnnotation] = {}
        if not self._check(TokenType.RPAREN):
            while True:
                tok = self._consume(TokenType.IDENT, "Expect parameter name")
                params.append(tok.lexeme)
                if self._match(TokenType.COLON):
                    param_types[tok.lexeme] = self._parse_type_annotation()
                if self._match(TokenType.COMMA):
                    continue
                break
        self._consume(TokenType.RPAREN, "Expect ')' after parameter list")
        return params, param_types

    def _parse_type_annotation(self) -> TypeAnnotation:
        return TypeAnnotation(self._parse_type_union())

    def _parse_type_union(self) -> str:
        parts = [self._parse_type_primary()]
        while self._match(TokenType.PIPE):
            parts.append(self._parse_type_primary())
        if len(parts) == 1:
            return parts[0]
        return " | ".join(parts)

    def _parse_type_primary(self) -> str:
        tok = self._consume(TokenType.IDENT, "Expect type name after ':'")
        base = tok.lexeme
        if self._match(TokenType.LBRACKET):
            args: List[str] = []
            if not self._check(TokenType.RBRACKET):
                while True:
                    args.append(self._parse_type_union())
                    if not self._match(TokenType.COMMA):
                        break
            self._consume(TokenType.RBRACKET, "Expect ']' after generic type arguments")
            return f"{base}[{', '.join(args)}]"
        return base

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

    def _optional_semicolon(self) -> None:
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

    # ---------------- pattern matching ----------------
    
    def _match_statement(self) -> MatchStmt:
        """Parse a match statement: match expr { case pattern { statements } ... }"""
        value = self._expression()
        self._consume(TokenType.LBRACE, "Expect '{' after match value")
        
        arms: List[CaseArm] = []
        while not self._check(TokenType.RBRACE) and not self._is_at_end():
            self._consume(TokenType.CASE, "Expect 'case' in match statement")
            pattern = self._parse_pattern()
            
            # Optional guard: if condition
            guard = None
            if self._match(TokenType.IF):
                guard = self._expression()
            # Expect ':' after pattern (and guard if present)
            self._consume(TokenType.COLON, "Expect ':' after case pattern")
            
            # Check if next token is '{' for block body or expression
            if self._match(TokenType.LBRACE):
                # Block form: case pattern: guard { statements... }
                body_stmts = self._block()
                arms.append(CaseArm(pattern, guard, BlockStmt(body_stmts)))
            else:
                # Expression form: case pattern: guard expression
                expr = self._expression()
                self._optional_semicolon()
                arms.append(CaseArm(pattern, guard, BlockStmt([ExprStmt(expr)])))
        
        self._consume(TokenType.RBRACE, "Expect '}' after match statement")
        return MatchStmt(value, arms)
    
    def _match_expression(self) -> MatchExpr:
        """Parse a match expression: match expr { case pattern: expr; ... }"""
        value = self._expression()
        self._consume(TokenType.LBRACE, "Expect '{' after match value")
        
        arms: List[CaseArm] = []
        while not self._check(TokenType.RBRACE) and not self._is_at_end():
            self._consume(TokenType.CASE, "Expect 'case' in match expression")
            pattern = self._parse_pattern()
            
            # Optional guard: if condition
            guard = None
            if self._match(TokenType.IF):
                guard = self._expression()
            
            self._consume(TokenType.COLON, "Expect ':' after case pattern")
            expr = self._expression()
            self._optional_semicolon()
            
            # Create a block with just the expression
            arms.append(CaseArm(pattern, guard, BlockStmt([ExprStmt(expr)])))
        
        self._consume(TokenType.RBRACE, "Expect '}' after match expression")
        return MatchExpr(value, arms)
    
    def _parse_pattern(self) -> Pattern:
        """Parse a pattern for matching."""
        # Handle OR patterns first: pattern | pattern | pattern
        patterns = [self._parse_single_pattern()]
        while self._match(TokenType.PIPE):
            patterns.append(self._parse_single_pattern())
        
        if len(patterns) == 1:
            return patterns[0]
        else:
            return OrPattern(patterns)
    
    def _parse_single_pattern(self) -> Pattern:
        """Parse a single pattern (no OR)."""
        # Wildcard pattern: _
        if self._check(TokenType.IDENT) and self._peek().lexeme == "_":
            self._advance()
            return WildcardPattern()
        
        # Literal patterns: numbers, strings, true, false, null
        if self._match(TokenType.NUMBER):
            return LiteralPattern(self._previous().literal)
        if self._match(TokenType.STRING):
            return LiteralPattern(self._previous().literal)
        if self._match(TokenType.TRUE):
            return LiteralPattern(True)
        if self._match(TokenType.FALSE):
            return LiteralPattern(False)
        if self._match(TokenType.NULL):
            return LiteralPattern(None)
        
        # List pattern: [pattern1, pattern2, ...]
        if self._match(TokenType.LBRACKET):
            elements: List[Pattern] = []
            while not self._check(TokenType.RBRACKET) and not self._is_at_end():
                elements.append(self._parse_pattern())
                if not self._match(TokenType.COMMA):
                    break
            self._consume(TokenType.RBRACKET, "Expect ']' after list pattern")
            return ListPattern(elements)
        
        # Tuple pattern: (pattern1, pattern2, ...)
        if self._match(TokenType.LPAREN):
            elements: List[Pattern] = []
            while not self._check(TokenType.RPAREN) and not self._is_at_end():
                elements.append(self._parse_pattern())
                if not self._match(TokenType.COMMA):
                    break
            self._consume(TokenType.RPAREN, "Expect ')' after tuple pattern")
            return TuplePattern(elements)
        
        # Dict pattern: {key1: pattern1, key2: pattern2, ...}
        if self._match(TokenType.LBRACE):
            entries: List[tuple[str, Pattern]] = []
            while not self._check(TokenType.RBRACE) and not self._is_at_end():
                # Parse key (must be string or identifier)
                if self._match(TokenType.STRING):
                    key = self._previous().literal
                elif self._match(TokenType.IDENT):
                    key = self._previous().lexeme
                else:
                    raise ParseError("Expect string or identifier as dict pattern key")
                
                self._consume(TokenType.COLON, "Expect ':' after dict pattern key")
                pattern = self._parse_pattern()
                entries.append((key, pattern))
                
                if not self._match(TokenType.COMMA):
                    break
            self._consume(TokenType.RBRACE, "Expect '}' after dict pattern")
            return DictPattern(entries)
        
        # Type pattern: int, str, etc. (identifiers that are types)
        if self._check(TokenType.IDENT) and self._is_type_name(self._peek().lexeme):
            type_name = self._advance().lexeme
            return TypePattern(Variable(type_name))
        
        # Variable pattern: any other identifier
        if self._match(TokenType.IDENT):
            return VariablePattern(self._previous().lexeme)
        
        raise ParseError(f"Unexpected token in pattern: {self._peek()}")
    
    def _is_type_name(self, name: str) -> bool:
        """Check if an identifier is likely a type name."""
        # Simple heuristic: common type names
        common_types = {"int", "str", "string", "float", "bool", "list", "tuple", "dict", "object"}
        return name in common_types
