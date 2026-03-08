from vyom.lexer import Lexer
from vyom.parser import Parser, ParseError
from vyom.ast_nodes import LetStmt, PrintStmt, ExprStmt, IfStmt, WhileStmt, BlockStmt, Variable, Literal

def _parse(src):
    tokens = Lexer(src).lex()
    return Parser(tokens).parse()

def test_parse_let_and_print():
    src = 'const x = 1 + 2; show x;'
    stmts = _parse(src)
    # should be two statements
    assert len(stmts) == 2
    assert isinstance(stmts[0], LetStmt)
    assert stmts[0].is_const == True
    assert isinstance(stmts[1], PrintStmt)

def test_parse_if_else_and_block():
    src = '''
    when (1 == 1) {
        show "ok";
    } else {
        show "bad";
    }
    '''
    stmts = _parse(src)
    assert len(stmts) == 1
    stmt = stmts[0]
    assert isinstance(stmt, IfStmt)
    assert isinstance(stmt.then_branch, BlockStmt)
    assert isinstance(stmt.else_branch, BlockStmt)

def test_parse_while_and_exprstmt():
    src = 'const i = 0; while (i < 3) { i = i + 1; }'
    stmts = _parse(src)
    assert any(isinstance(s, WhileStmt) for s in stmts)

def test_parse_error_unexpected_token():
    src = 'const = 1;'
    try:
        _parse(src)
        assert False, "expected ParseError"
    except ParseError:
        pass
