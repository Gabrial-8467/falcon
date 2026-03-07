# tools/debug_parse.py
from src.vyom.lexer import Lexer
from src.vyom.parser import Parser
from src.vyom.tokens import TokenType

code = """
var i := 1;
loop {
    if (i > 3) {
        break;
    }
}
"""

lex = Lexer(code)
tokens = lex.lex()
print("TOKENS SENT TO PARSER:")
for idx, t in enumerate(tokens):
    print(idx, t.type, getattr(t, "lexeme", None))

print("\nPARSING -> AST:")
parser = Parser(tokens)
try:
    stmts = parser.parse()
    for s in stmts:
        print(repr(s))
except Exception as e:
    print("Parser error:", e)
