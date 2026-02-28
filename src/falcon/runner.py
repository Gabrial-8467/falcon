# src/falcon/runner.py
"""
Runner: compile or interpret a Falcon source file, attempt VM first then fallback.

Usage:
    python -m falcon.runner path/to/file.fn
"""
from __future__ import annotations

import sys
import pathlib
import traceback
import time
from typing import Any, Dict, List, Optional, Tuple

from .lexer import Lexer, LexerError
from .parser import Parser, ParseError
from .interpreter import Interpreter, InterpreterError
from .compiler import Compiler, Code, CompileError
from .vm import VM, VMRuntimeError
from .builtins import BUILTINS
from .type_checker import TypeChecker, TypeCheckError


# --------------------------------------------
# Helpers
# --------------------------------------------
# module‑level cache for compiled code (path > (mtime, Code))
_compile_cache: Dict[str, Tuple[float, Code]] = {}

def read_source(path: str) -> str:
    """Read source file text, ensuring .fn extension is handled by caller."""
    p = pathlib.Path(path)
    if not p.exists():
        raise FileNotFoundError(path)
    return p.read_text(encoding="utf-8")



def pretty_print_compiled(code: Code) -> None:
    try:
        print(f"Compiled module: {code.name}")
        print(f"  consts: {len(getattr(code, 'consts', []))}")
        print(f"  instructions: {len(getattr(code, 'instructions', []))}")
        print(f"  nlocals: {getattr(code, 'nlocals', '?')}, argcount: {getattr(code, 'argcount', '?')}")
    except Exception:
        print("  (unable to inspect compiled code)")


def dump_vm_debug(vm: VM) -> None:
    print("=== VM DEBUG SNAPSHOT ===")
    try:
        print("VM globals (sample):")
        items = list(vm.globals.items())
        for k, v in items[:60]:
            try:
                print(f"  {k!s}: {repr(v)[:200]}")
            except Exception:
                print(f"  {k!s}: <unrepresentable>")
    except Exception as e:
        print("Failed to print vm.globals:", e)

    try:
        if getattr(vm, "frames", None):
            top = vm.frames[-1]
            print("Top frame:", top)
            print("  ip:", top.ip)
            print("  stack (len):", len(top.stack))
            print("  locals (len):", len(top.locals))
            print("  globals (len):", len(top.globals))
    except Exception as e:
        print("Failed to print frames:", e)

    print("=== END VM DEBUG ===")


# --------------------------------------------
# MAIN EXECUTION LOGIC
# --------------------------------------------
def run_file(path: str) -> int:
    if not path.lower().endswith('.fn'):
        print(f"{path}: Error – only .fn files are supported.")
        return 1
    # Read source
    src = read_source(path)
    src_mtime = pathlib.Path(path).stat().st_mtime

    # Check compile cache
    cache_entry = _compile_cache.get(path)
    if cache_entry and cache_entry[0] == src_mtime:
        code_obj = cache_entry[1]
        compile_time = 0.0
        cached = True
    else:
        cached = False

    # Timers
    lex_time = parse_time = compile_time = 0.0 if not cached else 0.0
    vm_time: Optional[float] = None
    interp_time: Optional[float] = None
    total_start = time.perf_counter()

    if not cached:
        # Lexing
        t0 = time.perf_counter()
        tokens = Lexer(src).lex()
        lex_time = time.perf_counter() - t0
        # Parsing
        t0 = time.perf_counter()
        ast = Parser(tokens).parse()
        parse_time = time.perf_counter() - t0
        TypeChecker().check(ast)
        # Compilation
        compiler = Compiler()
        t0 = time.perf_counter()
        try:
            code_obj = compiler.compile_module(ast, name=path)
        except (NotImplementedError, CompileError) as e:
            # Feature not implemented in compiler, use interpreter
            print(f"[Compiler] Feature not implemented: {e}")
            print("Falling back to interpreter...")
            code_obj = None
        compile_time = time.perf_counter() - t0
        # Store in cache
        _compile_cache[path] = (src_mtime, code_obj)
    else:
        # Need AST for interpreter fallback – re‑parse without timing
        tokens = Lexer(src).lex()
        ast = Parser(tokens).parse()
        TypeChecker().check(ast)

    # Prepare VM
    vm = VM(verbose=False)
    for k, v in BUILTINS.items():
        vm.globals.setdefault(k, v)

    # Try running on VM
    if code_obj is not None:
        try:
            pretty_print_compiled(code_obj)
            print(f"[VM] Running compiled code for {path} ...")
            t0 = time.perf_counter()
            result = vm.run_code(code_obj)
            vm_time = time.perf_counter() - t0
            total = time.perf_counter() - total_start
            print(f"[VM] Completed. Result: {result!r}")
            print("\nTiming summary:")
            print(f"  lex      : {lex_time:.6f}s")
            print(f"  parse    : {parse_time:.6f}s")
            print(f"  compile  : {compile_time:.6f}s")
            print(f"  vm       : {vm_time:.6f}s")
            print(f"  interp   : N/A")
            print(f"  total    : {total:.6f}s")
            return 0
        except VMRuntimeError as ve:
            print(f"[VM ERROR] {ve}")
            traceback.print_exc(limit=1)
            dump_vm_debug(vm)
            print("Falling back to interpreter...")
        except Exception as e:
            print(f"[VM ERROR] Unexpected exception: {e}")
            traceback.print_exc(limit=1)
            dump_vm_debug(vm)
            print("Falling back to interpreter...")

    # Interpreter fallback
    try:
        interp = Interpreter()
        print("[Interpreter] Running AST interpreter...")
        t0 = time.perf_counter()
        interp.interpret(ast)
        interp_time = time.perf_counter() - t0
        total = time.perf_counter() - total_start
        print("[Interpreter] Completed.")
        print("\nTiming summary:")
        print(f"  lex      : {lex_time:.6f}s")
        print(f"  parse    : {parse_time:.6f}s")
        print(f"  compile  : {compile_time:.6f}s")
        print(f"  vm       : N/A")
        print(f"  interp   : {interp_time:.6f}s")
        print(f"  total    : {total:.6f}s")
        return 0
    except TypeCheckError as te:
        print(f"{path}: Type error: {te}")
        return 3
    except InterpreterError as ie:
        print(f"{path}: Runtime error: {ie}")
        traceback.print_exc()
        return 3
    except Exception as e:
        print(f"{path}: Unexpected runtime error: {e}")
        traceback.print_exc()
        return 3



# --------------------------------------------
# ENTRYPOINT
# --------------------------------------------
def main(argv: List[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print("Usage: python -m falcon.runner path/to/file.fn")
        return 1
    path = argv[0]
    # Enforce .fn extension – only Falcon source files are allowed
    if pathlib.Path(path).suffix.lower() != ".fn":
        print(f"Error: Only .fn files are supported. Received '{path}'.")
        return 2

    try:
        return run_file(path)
    except FileNotFoundError:
        print(f"File not found: {path}")
        return 2
    except Exception as e:
        print("Unhandled error in runner:", e)
        traceback.print_exc()
        return 4


if __name__ == "__main__":
    sys.exit(main())
