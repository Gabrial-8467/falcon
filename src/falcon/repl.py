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
        # ignore problems with history
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
        # handle escaped quotes
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
    # balanced if no open quotes and stack empty
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
        # Catch-all to prevent REPL from dying; show traceback for debugging
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
        # print a compact repr of the AST
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
    banner = "Falcon REPL — type 'help' for commands, Ctrl-D to exit"
    print(banner)
    source_lines: List[str] = []

    try:
        while True:
            try:
                prompt = "... " if source_lines else "falcon> "
                line = input(prompt)
            except EOFError:
                print()  # newline
                break
            except KeyboardInterrupt:
                # Ctrl-C: clear current buffer and continue
                print()
                source_lines = []
                continue

            if line is None:
                continue

            stripped = line.strip()

            # REPL meta-commands
            if not source_lines and stripped in ("quit", "exit"):
                break
            if not source_lines and stripped == "help":
                print("REPL commands:")
                print("  help                 show this help")
                print("  quit / exit          exit the REPL")
                print("  .load <file>         load and run a .fn file")
                print("  .tokens <file|\"src\">   show lexer tokens for file or quoted source")
                print("  .ast <file|\"src\">      show parsed AST for file or quoted source")
                print("")
                print("Language tips: use 'var' / 'const' and end statements with ';' (optional).")
                continue

            # .load <file>
            if not source_lines and stripped.startswith(".load "):
                _, _, path = stripped.partition(" ")
                path = path.strip()
                if not path:
                    print("Usage: .load <path>", file=sys.stderr)
                    continue
                src = _read_file_text(path)
                if src is None:
                    continue
                _run_source(src, interpreter, filename=path)
                continue

            # .tokens <file|\"source\">
            if not source_lines and stripped.startswith(".tokens"):
                rest = stripped[len(".tokens"):].strip()
                if not rest:
                    print("Usage: .tokens <file> or .tokens \"source\"", file=sys.stderr)
                    continue
                # quoted string -> use as source directly
                if (rest.startswith('"') and rest.endswith('"')) or (rest.startswith("'") and rest.endswith("'")):
                    src = rest[1:-1]
                    _print_tokens_for_source(src)
                else:
                    # treat as filename
                    src = _read_file_text(rest)
                    if src is not None:
                        _print_tokens_for_source(src)
                continue

            # .ast <file|\"source\">
            if not source_lines and stripped.startswith(".ast"):
                rest = stripped[len(".ast"):].strip()
                if not rest:
                    print("Usage: .ast <file> or .ast \"source\"", file=sys.stderr)
                    continue
                if (rest.startswith('"') and rest.endswith('"')) or (rest.startswith("'") and rest.endswith("'")):
                    src = rest[1:-1]
                    _print_ast_for_source(src)
                else:
                    src = _read_file_text(rest)
                    if src is not None:
                        _print_ast_for_source(src)
                continue

            # accumulate lines until balanced (very permissive)
            source_lines.append(line)
            current_src = "\n".join(source_lines)
            if not _balanced(current_src):
                # keep reading
                continue

            # run the accumulated source
            _run_source(current_src, interpreter, filename="<repl>")
            source_lines = []

    finally:
        _save_readline()
