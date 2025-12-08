from src.falcon.lexer import Lexer
from src.falcon.tokens import TokenType

code = """
loop {
    if (i > 3) {
        break;
    }
}
"""

lexer = Lexer(code)

# Try all common token methods
tokens = None

if hasattr(lexer, "scan_tokens"):
    tokens = lexer.scan_tokens()
elif hasattr(lexer, "tokenize"):
    tokens = lexer.tokenize()
elif hasattr(lexer, "run"):
    tokens = lexer.run()
elif hasattr(lexer, "__iter__"):
    tokens = list(lexer)
else:
    raise Exception("Lexer has no usable tokenizing method")

print("Token dump:\n--------------")
for t in tokens:
    # print as much as possible without crashing
    ttype = getattr(t, "type", None)
    lex = getattr(t, "lexeme", None)
    lit = getattr(t, "literal", None)
    print(f"{ttype}   lexeme={lex}   literal={lit}")
