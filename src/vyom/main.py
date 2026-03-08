"""
Legacy Vyom runner (fallback).

This file provides:
- run_file(path) -> int
- start_repl() -> None

If a newer backend exists (vyom.runner / vyom.repl) the top-level
helpers will delegate to those. Otherwise this file implements a small,
safe, line-wise interpreter with a REPL.
"""
from __future__ import annotations

import ast
import argparse
import os
import pathlib
import readline
import sys
import traceback
from typing import Any, Callable, Dict, Optional, Tuple

# package version (kept in sync with __init__ ideally)
try:
    from . import __version__ as VYOM_VERSION
except Exception:
    VYOM_VERSION = "1.0.0"


# Attempt to delegate to modern backend if present
def _try_delegate() -> Tuple[
    Optional[Callable[[str], int]], Optional[Callable[[], None]]
]:
    try:
        from . import runner  # type: ignore
        from . import repl    # type: ignore
        run_file_fn = getattr(runner, "run_file", None)
        start_repl_fn = getattr(repl, "start_repl", None)
        if callable(run_file_fn) and callable(start_repl_fn):
            return run_file_fn, start_repl_fn
    except Exception:
        pass
    return None, None


_delegate_run_file, _delegate_start_repl = _try_delegate()


# ---------------- safe expression evaluator ----------------

class VyomRuntimeError(Exception):
    def __init__(self, message: str, lineno: int | None = None, col: int | None = None):
        super().__init__(message)
        self.lineno = lineno
        self.col = col


def _safe_eval_node(node: ast.AST, env: Dict[str, Any]) -> Any:
    """Evaluate a small subset of Python AST nodes safely."""
    if isinstance(node, ast.Expression):
        return _safe_eval_node(node.body, env)

    if isinstance(node, ast.Constant):
        # allow numbers, strings, booleans, None
        if isinstance(node.value, (int, float, str, bool)) or node.value is None:
            return node.value
        raise VyomRuntimeError(f"Unsupported constant type: {type(node.value).__name__}")

    if isinstance(node, ast.Num):  # py<3.8
        return node.n
    if isinstance(node, ast.Str):  # py<3.8
        return node.s

    if isinstance(node, ast.BinOp):
        left = _safe_eval_node(node.left, env)
        right = _safe_eval_node(node.right, env)
        op = node.op
        if isinstance(op, ast.Add):
            return left + right
        if isinstance(op, ast.Sub):
            return left - right
        if isinstance(op, ast.Mult):
            return left * right
        if isinstance(op, ast.Div):
            return left / right
        if isinstance(op, ast.FloorDiv):
            return left // right
        if isinstance(op, ast.Mod):
            return left % right
        if isinstance(op, ast.Pow):
            return left ** right
        raise VyomRuntimeError(f"Unsupported binary operator: {type(op).__name__}")

    if isinstance(node, ast.UnaryOp):
        operand = _safe_eval_node(node.operand, env)
        if isinstance(node.op, ast.UAdd):
            return +operand
        if isinstance(node.op, ast.USub):
            return -operand
        if isinstance(node.op, ast.Not):
            return not operand
        raise VyomRuntimeError(f"Unsupported unary operator: {type(node.op).__name__}")

    if isinstance(node, ast.BoolOp):
        # short-circuit semantics
        if isinstance(node.op, ast.And):
            for v in node.values:
                if not _safe_eval_node(v, env):
                    return False
            return True
        if isinstance(node.op, ast.Or):
            for v in node.values:
                if _safe_eval_node(v, env):
                    return True
            return False
        raise VyomRuntimeError(f"Unsupported boolean operator: {type(node.op).__name__}")

    if isinstance(node, ast.Compare):
        left = _safe_eval_node(node.left, env)
        for op, comp in zip(node.ops, node.comparators):
            right = _safe_eval_node(comp, env)
            if isinstance(op, ast.Eq):
                ok = left == right
            elif isinstance(op, ast.NotEq):
                ok = left != right
            elif isinstance(op, ast.Lt):
                ok = left < right
            elif isinstance(op, ast.LtE):
                ok = left <= right
            elif isinstance(op, ast.Gt):
                ok = left > right
            elif isinstance(op, ast.GtE):
                ok = left >= right
            else:
                raise VyomRuntimeError(f"Unsupported comparison: {type(op).__name__}")
            if not ok:
                return False
            left = right
        return True

    if isinstance(node, ast.Name):
        if node.id in env:
            return env[node.id]
        # allow literals by name
        if node.id == "true" or node.id == "True":
            return True
        if node.id == "false" or node.id == "False":
            return False
        if node.id == "null" or node.id == "None":
            return None
        raise VyomRuntimeError(f"Undefined variable '{node.id}'")

    if isinstance(node, ast.Tuple):
        return tuple(_safe_eval_node(elt, env) for elt in node.elts)
    if isinstance(node, ast.List):
        return [_safe_eval_node(elt, env) for elt in node.elts]

    # disallow: Call, Attribute, Subscript, Lambda, etc.
    if isinstance(node, (ast.Call, ast.Attribute, ast.Subscript, ast.Lambda, ast.Dict, ast.Set)):
        raise VyomRuntimeError(f"Unsupported expression construct: {type(node).__name__}")

    raise VyomRuntimeError(f"Unsupported expression node: {type(node).__name__}")


def eval_expression(expr: str, env: Dict[str, Any]) -> Any:
    try:
        parsed = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        raise VyomRuntimeError(f"Syntax error: {e.msg}", getattr(e, "lineno", None), getattr(e, "offset", None)) from e
    return _safe_eval_node(parsed, env)


# ----------- source handling (inline comments + triple quotes) -----------

def _merge_triple_quoted(source: str) -> str:
    # naive approach: keep triple quoted blocks intact by returning same source.
    # we don't transform; lexer is simple line-based so this is fine for now.
    return source


def _strip_inline_comment(line: str) -> str:
    # remove '#' comments unless inside quotes (very simple handling)
    result = []
    i = 0
    n = len(line)
    in_s = False
    in_d = False
    while i < n:
        ch = line[i]
        if ch == "'" and not in_d:
            # handle escape
            if i > 0 and line[i - 1] == "\\":
                result.append(ch)
                i += 1
                continue
            in_s = not in_s
            result.append(ch)
            i += 1
            continue
        if ch == '"' and not in_s:
            if i > 0 and line[i - 1] == "\\":
                result.append(ch)
                i += 1
                continue
            in_d = not in_d
            result.append(ch)
            i += 1
            continue
        if ch == "#" and not in_s and not in_d:
            break
        result.append(ch)
        i += 1
    return "".join(result).rstrip()


# ---------------- execution ----------------

def _format_error_context(filename: str, lineno: int, source_lines: list[str], msg: str, col: Optional[int] = None) -> str:
    out = f"{filename}:{lineno}: {msg}"
    if 1 <= lineno <= len(source_lines):
        line = source_lines[lineno - 1].rstrip("\n")
        out += f"\n  {line}"
        if col is not None and col > 0:
            caret_pos = min(col - 1, max(len(line) - 1, 0))
            out += "\n  " + " " * caret_pos + "^"
    return out


def execute_line(line: str, env: Dict[str, Any], filename: str = "<input>", lineno: int = 0) -> None:
    raw = line.strip()
    if raw == "" or raw.startswith("#"):
        return
    text = _strip_inline_comment(raw)

    # let assignment: let x = expr
    if text.startswith("let "):
        rest = text[len("let ") :].strip()
        if "=" not in rest:
            raise VyomRuntimeError("Invalid assignment (missing '=')", lineno)
        name, expr = rest.split("=", 1)
        name = name.strip()
        if not name.isidentifier():
            raise VyomRuntimeError(f"Invalid variable name '{name}'", lineno)
        try:
            val = eval_expression(expr.strip(), env)
        except VyomRuntimeError as e:
            raise VyomRuntimeError(str(e), lineno, getattr(e, "col", None)) from e
        env[name] = val
        return

    # print statement
    if text.startswith("print "):
        expr = text[len("print ") :].strip()
        val = eval_expression(expr, env)
        # Vyom-style output
        if isinstance(val, tuple) or isinstance(val, list):
            print(*val)
        else:
            print(val)
        return

    # fallback: evaluate expression and print result if not None
    try:
        res = eval_expression(text, env)
        if res is not None:
            print(res)
    except VyomRuntimeError as e:
        raise VyomRuntimeError(str(e), lineno, getattr(e, "col", None)) from e


def execute_source(source: str, env: Optional[Dict[str, Any]] = None, filename: str = "<input>") -> None:
    if env is None:
        env = {}
    source = _merge_triple_quoted(source)
    lines = source.splitlines()
    for i, line in enumerate(lines, start=1):
        try:
            execute_line(line, env, filename=filename, lineno=i)
        except VyomRuntimeError as e:
            # Attach lineno/col if present and rethrow with formatted context
            col = getattr(e, "col", None)
            raise VyomRuntimeError(
                _format_error_context(filename, getattr(e, "lineno", i) or i, lines, str(e), col)
            ) from e


# ---------------- run_file / REPL ----------------

_HISTFILE = os.path.expanduser("~/.vyom_history")


def _setup_readline() -> None:
    try:
        readline.set_history_length(1000)
        if os.path.exists(_HISTFILE):
            readline.read_history_file(_HISTFILE)
    except Exception:
        pass


def _save_readline() -> None:
    try:
        readline.write_history_file(_HISTFILE)
    except Exception:
        pass


def run_file(path: str) -> int:
    # Delegate if possible
    if callable(_delegate_run_file):
        try:
            return _delegate_run_file(path)
        except Exception:
            # fall through to legacy runner
            pass

    p = pathlib.Path(path)
    if not p.exists():
        print(f"File not found: {path}", file=sys.stderr)
        return 2
    try:
        source = p.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Failed to read file {path}: {e}", file=sys.stderr)
        return 3

    env: Dict[str, Any] = {}
    try:
        execute_source(source, env, filename=str(p))
    except VyomRuntimeError as e:
        print(f"Runtime error: {e}", file=sys.stderr)
        return 1
    except Exception:
        print("Unexpected error while running file:", file=sys.stderr)
        traceback.print_exc()
        return 4
    return 0


def start_repl() -> None:
    # Delegate if possible
    if callable(_delegate_start_repl):
        try:
            return _delegate_start_repl()
        except Exception:
            # fall back to legacy REPL
            pass

    env: Dict[str, Any] = {}
    _setup_readline()
    banner = f"Vyom (legacy REPL) {VYOM_VERSION} — type 'help', Ctrl-D to exit"
    print(banner)
    try:
        while True:
            try:
                line = input("vyom> ")
            except EOFError:
                print()
                break
            except KeyboardInterrupt:
                print()
                continue

            if not line:
                continue

            cmd = line.strip()
            if cmd in ("quit", "exit"):
                break
            if cmd == "help":
                print("Commands:")
                print("  let <name> = <expr>   assign variable")
                print("  print <expr>          print value")
                print("  <expr>                evaluate expression and print")
                print("  quit / exit           exit REPL")
                continue

            try:
                execute_line(line, env, filename="<repl>", lineno=0)
            except VyomRuntimeError as e:
                print(f"Error: {e}", file=sys.stderr)
            except Exception:
                print("Unexpected error in REPL:", file=sys.stderr)
                traceback.print_exc()
    finally:
        _save_readline()


# ---------------- CLI entrypoint ----------------

def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="vyom", description="Vyom language")
    subparsers = p.add_subparsers(dest="command", help="Available commands")
    
    # Run command (default)
    run_parser = subparsers.add_parser("run", help="Run a .vyom source file")
    run_parser.add_argument("file", help="Run a .vyom source file")
    
    # REPL command
    repl_parser = subparsers.add_parser("repl", help="Start interactive REPL")
    
    # Global options
    p.add_argument("-i", "--repl", action="store_true", help="Start interactive REPL")
    p.add_argument("--version", action="store_true", help="Print version and exit")
    
    return p


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:]) if argv is None else list(argv)
    parser = _build_argparser()
    args = parser.parse_args(argv)

    if args.version:
        print(VYOM_VERSION)
        return 0

    # Handle run command
    if args.command == "run" and hasattr(args, 'file'):
        return run_file(args.file)

    # Handle repl command
    if args.command == "repl" or args.repl:
        start_repl()
        return 0

    # Legacy behavior: if no command but file provided, run it
    if hasattr(args, 'file') and args.file:
        return run_file(args.file)

    # Default to REPL
    start_repl()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
