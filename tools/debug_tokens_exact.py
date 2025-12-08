# tools/debug_tokens_exact.py
from src.falcon.lexer import Lexer
from src.falcon.tokens import TokenType

code = """
loop {
    if (i > 3) {
        break;
    }
}
"""

lex = Lexer(code)
tokens = lex.lex()    # <-- use .lex() (your Lexer returns a List[Token])

print("LEXER TOKENS:")
for t in tokens:
    lexeme = getattr(t, "lexeme", None)
    lit = getattr(t, "literal", None)
    print(f"{t.type!r:30}  lexeme={lexeme!r:8}  literal={lit!r}")
