"""
Runner for the Falcon language.

Provides:
- run_file(path) -> int  : run a .fn file and return an exit code
- run_source(source, filename, env=None) : run a source string
- cli() / main()         : command-line entrypoint (used by pyproject [project.scripts])

Behavior:
- Lex -> Parse -> Interpret pipeline with pretty error messages
- Returns exit codes similar to legacy runner:
    0 : success
    1 : runtime / interpreter error
    2 : file not found
    3 : file read error
    4 : unexpected internal error
"""
from __future__ import annotations

import argparse
import sys
import pathlib
import traceback
from typing import Optional, Dict, Any

from .lexer import Lexer, LexerError
from .parser import Parser, ParseError
from .interpreter import Interpreter, InterpreterError


def _format_pipeline_error(kind: str, err: Exception, filename: str = "<input>") -> str:
    """Format errors from lexer/parser/interpreter for user display."""
    if isinstance(err, LexerError):
        return f"{filename}: Lexer error: {err}"
    if isinstance(err, ParseError):
        return f"{filename}: Parse error: {err}"
    if isinstance(err, InterpreterError):
        return f"{filename}: Runtime error: {err}"
    # Fallback
    return f"{filename}: {kind}: {err}"


def run_source(source: str, filename: str = "<input>", env: Optional[Dict[str, Any]] = None) -> int:
    """
    Run a source string through lex/parse/interpret.
    Returns 0 on success, 1 on runtime/parse/lex error, 4 on unexpected internal error.
    If env is provided it should be a mapping used as the interpreter's global bindings.
    """
    try:
        lexer = Lexer(source)
        tokens = lexer.lex()
        parser = Parser(tokens)
        stmts = parser.parse()
        interpreter = Interpreter()
        # Optionally pre-populate interpreter globals with provided env values
        if env:
            for k, v in env.items():
                try:
                    interpreter.globals.define(k, v)
                except Exception:
                    # be resilient for weird env values
                    pass
        interpreter.interpret(stmts)
        return 0
    except (LexerError, ParseError, InterpreterError) as e:
        msg = _format_pipeline_error("error", e, filename)
        print(msg, file=sys.stderr)
        return 1
    except Exception:
        print(f"{filename}: Unexpected internal error while running source.", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return 4


def run_file(path: str) -> int:
    """
    Run a .fn file at `path`. Returns exit codes:
      0 success
      2 file not found
      3 read error
      1 runtime/parse/lex error
      4 unexpected internal error
    """
    p = pathlib.Path(path)
    if not p.exists():
        print(f"File not found: {path}", file=sys.stderr)
        return 2
    try:
        source = p.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Failed to read file {path}: {e}", file=sys.stderr)
        return 3

    return run_source(source, filename=str(p))


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="falcon", description="Falcon language runner")
    p.add_argument("file", nargs="?", help="Run a .fn source file")
    p.add_argument("-i", "--repl", action="store_true", help="Start interactive REPL")
    p.add_argument("-c", "--code", help="Execute code string and exit")
    p.add_argument("--version", action="store_true", help="Print version and exit")
    return p


def cli(argv: Optional[list[str]] = None) -> int:
    """
    Command-line entrypoint intended to be referenced by pyproject [project.scripts]:
        falcon = "falcon.runner:cli"
    """
    argv = list(sys.argv[1:]) if argv is None else list(argv)
    parser = _build_argparser()
    args = parser.parse_args(argv)

    # Lazy import to avoid circular import at package import time (if any)
    try:
        from . import __version__ as _ver  # type: ignore
    except Exception:
        _ver = "0.0.0"

    if args.version:
        print(_ver)
        return 0

    # If -c provided, run that code and exit
    if args.code is not None:
        return run_source(args.code, filename="<command>")

    # If repl requested, delegate to repl.start_repl if available
    if args.repl:
        try:
            from .repl import start_repl
            start_repl()
            return 0
        except Exception as e:
            print(f"Failed to start REPL: {e}", file=sys.stderr)
            return 4

    # If a file provided, run it
    if args.file:
        return run_file(args.file)

    # Default: start REPL
    try:
        from .repl import start_repl
        start_repl()
        return 0
    except Exception as e:
        print(f"Failed to start REPL: {e}", file=sys.stderr)
        return 4


def main() -> int:
    """Helper for calling as a module entrypoint."""
    return cli()


if __name__ == "__main__":
    raise SystemExit(main())
