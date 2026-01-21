"""
REPL for the Falcon language (JS-like).

Provides:
- start_repl() entry point
- multiline input support (basic brace/paren matching)
- readline history (saved to ~/.falcon_history) (falls back if readline missing)
- commands: help, .load <file>, .tokens <file|source>, .ast <file|source>, quit/exit
"""
from __future__ import annotations

import os
import pathlib
import sys
import traceback
from typing import List

# try to import readline but allow platforms without it
try:
    import readline  # type: ignore
except Exception:
    readline = None  # type: ignore

from .lexer import Lexer, LexerError
from .parser import Parser, ParseError
from .interpreter import Interpreter, InterpreterError

_HISTFILE = os.path.expanduser("~/.falcon_history")


def _setup_readline() -> None:
    if readline is None:
        return
    try:
        readline.set_history_length(1000)
        if os.path.exists(_HISTFILE):
            readline.read_history_file(_HISTFILE)
    except Exception:
        pass


def _save_readline() -> None:
    if readline is None:
        return
    try:
        readline.write_history_file(_HISTFILE)
    except Exception:
        pass


def _balanced(source: str) -> bool:
    """
    Rudimentary check for balanced braces/parens/brackets and quotes.
    Lightweight: lets REPL know whether to prompt for more lines.
    """
    stack = []
    in_single = in_double = False
    i = 0
    while i < len(source):
        ch = source[i]
        if ch == "\\" and i + 1 < len(source):
            i += 2
            continue
        if ch == "'" and not in_double:
            in_single = not in_single
            i += 1
            continue
        if ch == '"' and not in_single:
            in_double = not in_double
            i += 1
            continue
        if in_single or in_double:
            i += 1
            continue
        if ch in "({[":
            stack.append(ch)
        elif ch in ")}]":
            if not stack:
                return False
            top = stack.pop()
            pairs = {"(": ")", "{": "}", "[": "]"}
            if pairs.get(top) != ch:
                return False
        i += 1
    return (not in_single) and (not in_double) and (len(stack) == 0)


def _run_source(source: str, interpreter: Interpreter, filename: str = "<repl>") -> None:
    """
    Lex -> Parse -> Interpret the given source string. Errors printed to stderr.
    """
    try:
        lexer = Lexer(source)
        tokens = lexer.lex()
        parser = Parser(tokens)
        stmts = parser.parse()
        interpreter.interpret(stmts)
    except LexerError as le:
        print(f"{filename}: Lexer error: {le}", file=sys.stderr)
    except ParseError as pe:
        print(f"{filename}: Parse error: {pe}", file=sys.stderr)
    except InterpreterError as ie:
        print(f"{filename}: Runtime error: {ie}", file=sys.stderr)
    except Exception:
        print(f"{filename}: Unhandled error during evaluation:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)


def _read_file_text(path: str) -> str | None:
    try:
        p = pathlib.Path(path)
        if not p.exists():
            print(f"File not found: {path}", file=sys.stderr)
            return None
        return p.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Failed to read {path}: {e}", file=sys.stderr)
        return None


def _print_tokens_for_source(source: str) -> None:
    try:
        lexer = Lexer(source)
        tokens = lexer.lex()
        print(tokens)
    except LexerError as le:
        print(f"Lexer error: {le}", file=sys.stderr)


def _print_ast_for_source(source: str) -> None:
    try:
        lexer = Lexer(source)
        tokens = lexer.lex()
        parser = Parser(tokens)
        stmts = parser.parse()
        for s in stmts:
            print(repr(s))
    except LexerError as le:
        print(f"Lexer error: {le}", file=sys.stderr)
    except ParseError as pe:
        print(f"Parse error: {pe}", file=sys.stderr)


def start_repl() -> None:
    """
    Start the Falcon interactive REPL. Blocks until the user exits.
    """
    interpreter = Interpreter()
    _setup_readline()
    print("Falcon REPL — type 'help' for commands, Ctrl-D to exit")
    source_lines: List[str] = []

    try:
        while True:
            try:
                prompt = "... " if source_lines else "falcon> "
                line = input(prompt)
            except EOFError:
                print()
                break
            except KeyboardInterrupt:
                print()
                source_lines = []
                continue

            if line is None:
                continue

            stripped = line.strip()

            if not source_lines and stripped in ("quit", "exit"):
                break

            if not source_lines and stripped == "help":
                print("REPL commands:")
                print("  help                 show this help")
                print("  quit / exit          exit the REPL")
                print("  .load <file>         load and run a .fn file")
                print("  .tokens <file|\"src\">   show lexer tokens")
                print("  .ast <file|\"src\">      show parsed AST")
                continue

            if not source_lines and stripped.startswith(".load "):
                _, _, path = stripped.partition(" ")
                src = _read_file_text(path.strip())
                if src is not None:
                    _run_source(src, interpreter, filename=path)
                continue

            if not source_lines and stripped.startswith(".tokens"):
                rest = stripped[len(".tokens"):].strip()
                src = rest[1:-1] if rest.startswith(("'", '"')) else _read_file_text(rest)
                if src is not None:
                    _print_tokens_for_source(src)
                continue

            if not source_lines and stripped.startswith(".ast"):
                rest = stripped[len(".ast"):].strip()
                src = rest[1:-1] if rest.startswith(("'", '"')) else _read_file_text(rest)
                if src is not None:
                    _print_ast_for_source(src)
                continue

            source_lines.append(line)
            current_src = "\n".join(source_lines)

            if not _balanced(current_src):
                continue

            _run_source(current_src, interpreter)
            source_lines = []

    finally:
        _save_readline()


# ✅ REQUIRED ENTRY POINT FOR `python -m falcon.repl`
def main() -> None:
    start_repl()


if __name__ == "__main__":
    main()
