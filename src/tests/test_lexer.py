import textwrap
from falcon.lexer import Lexer, LexerError
from falcon.tokens import TokenType

def test_basic_tokens():
    src = 'let x = 42; print "hi"; // comment\n/* block */'
    lexer = Lexer(src)
    tokens = lexer.lex()
    # find token types sequence (ignore EOF at end)
    types = [t.type for t in tokens if t.type != TokenType.EOF]
    # Expect LET IDENT EQ NUMBER SEMI PRINT STRING SEMI (comments produce no tokens)
    assert types[0] == TokenType.LET
    assert types[1] == TokenType.IDENT
    assert types[2] in (TokenType.EQ, TokenType.EQEQ)  # EQ expected
    assert TokenType.NUMBER in types
    assert TokenType.PRINT in types
    assert TokenType.STRING in types

def test_comments_and_strings():
    src = textwrap.dedent("""
        // whole-line comment
        let s = "line\\nwith\\nnew";
        let t = 'single\\'quote';
        /* block comment
           still comment */
        print s;
    """)
    lexer = Lexer(src)
    tokens = lexer.lex()
    # must have two LETs and a PRINT and two STRING tokens
    types = [t.type for t in tokens if t.type != TokenType.EOF]
    assert types.count(TokenType.LET) >= 2
    assert TokenType.PRINT in types
    assert types.count(TokenType.STRING) >= 2

def test_unterminated_block_comment_raises():
    src = "/* not closed "
    lexer = Lexer(src)
    try:
        lexer.lex()
        assert False, "expected LexerError on unterminated block comment"
    except LexerError:
        pass
