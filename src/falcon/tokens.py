# file: src/falcon/tokens.py
from enum import Enum, auto
from dataclasses import dataclass

class TokenType(Enum):
    # --- Single-character tokens ---
    LBRACE = auto()    # {
    RBRACE = auto()    # }
    LPAREN = auto()    # (
    RPAREN = auto()    # )
    SEMI = auto()      # ;
    COMMA = auto()     # ,
    DOT = auto()       # .
    PLUS = auto()      # +
    MINUS = auto()     # -
    STAR = auto()      # *
    SLASH = auto()     # /
    PERC = auto()      # %
    BANG = auto()      # !
    EQ = auto()        # =
    LT = auto()        # <
    GT = auto()        # >

    # --- Two-character operators ---
    EQEQ = auto()      # ==
    BANGEQ = auto()    # !=
    LTE = auto()       # <=
    GTE = auto()       # >=
    ANDAND = auto()    # &&
    OROR = auto()      # ||

    # --- Declaration / method operators (language-specific) ---
    DECL = auto()          # :=  (declaration)
    METHODCOLON = auto()   # ::  (method colon / custom operator)

    # --- Literals ---
    IDENT = auto()
    NUMBER = auto()
    STRING = auto()

    # --- Keywords (language) ---
    VAR = auto()        # var
    LET = auto()        # let (block‑scoped)
    CONST = auto()      # const
    IF = auto()
    ELSE = auto()
    WHILE = auto()
    FOR = auto()
    LOOP = auto()
    TO = auto()         # to (for .. to ..)
    STEP = auto()       # step (for .. step)
    TRUE = auto()
    FALSE = auto()
    NULL = auto()
    FUNCTION = auto()
    RETURN = auto()
    BREAK = auto()
    # --- End of File ---
    EOF = auto()


@dataclass
class Token:
    type: TokenType
    lexeme: str
    literal: object
    lineno: int
    col: int

    def __repr__(self) -> str:
        return (
            f"Token({self.type.name}, "
            f"{self.lexeme!r}, {self.literal!r}, "
            f"line={self.lineno}, col={self.col})"
        )
