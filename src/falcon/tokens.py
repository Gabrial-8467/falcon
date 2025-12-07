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

    # --- Special multi-char operators / punctuation added for Falcon ---
    DECL = auto()         # ':=' declaration operator
    METHODCOLON = auto()  # '::' method accessor

    # --- Literals ---
    IDENT = auto()
    NUMBER = auto()
    STRING = auto()

    # --- Keywords ---
    VAR = auto()        # 'var' (mutable declaration)
    CONST = auto()      # 'const' (immutable declaration)
    IF = auto()
    ELSE = auto()
    WHILE = auto()
    FOR = auto()        # 'for' (Falcon-style for)
    LOOP = auto()       # 'loop' (infinite loop)
    TO = auto()         # 'to' (for .. to ..)
    STEP = auto()       # 'step' in for header
    TRUE = auto()
    FALSE = auto()
    NULL = auto()
    FUNCTION = auto()
    RETURN = auto()
    SHOW = auto()

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
