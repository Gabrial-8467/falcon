import textwrap
from vyom.lexer import Lexer, LexerError
from vyom.tokens import TokenType

def test_basic_tokens():
    src = 'const x = 42; show "hi"; // comment\n/* block */'
    lexer = Lexer(src)
    tokens = lexer.lex()
    # find token types sequence (ignore EOF at end)
    types = [t.type for t in tokens if t.type != TokenType.EOF]
    # Expect CONST IDENT EQ NUMBER SEMI SAY STRING SEMI (comments produce no tokens)
    assert types[0] == TokenType.CONST
    assert types[1] == TokenType.IDENT
    assert types[2] in (TokenType.EQ, TokenType.EQEQ)  # EQ expected
    assert TokenType.NUMBER in types
    assert TokenType.SAY in types
    assert TokenType.STRING in types

def test_comments_and_strings():
    src = textwrap.dedent("""
        // whole-line comment
        const s = "line\\nwith\\nnew";
        const t = 'single\\'quote';
        /* block comment
           still comment */
        show s;
    """)
    lexer = Lexer(src)
    tokens = lexer.lex()
    # must have two CONSTs and a SAY and two STRING tokens
    types = [t.type for t in tokens if t.type != TokenType.EOF]
    assert types.count(TokenType.CONST) >= 2
    assert TokenType.SAY in types
    assert types.count(TokenType.STRING) >= 2

def test_unterminated_block_comment_raises():
    src = "/* not closed "
    lexer = Lexer(src)
    try:
        lexer.lex()
        assert False, "expected LexerError on unterminated block comment"
    except LexerError:
        pass
