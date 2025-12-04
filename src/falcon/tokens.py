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

    # --- Literals ---
    IDENT = auto()
    NUMBER = auto()
    STRING = auto()

    # --- Keywords ---
    LET = auto()
    IF = auto()
    ELSE = auto()
    WHILE = auto()
    TRUE = auto()
    FALSE = auto()
    NULL = auto()
    FUNCTION = auto()
    RETURN = auto()
    PRINT = auto()

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
