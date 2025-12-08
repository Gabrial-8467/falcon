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
from typing import Any, Dict, List

from .lexer import Lexer, LexerError
from .parser import Parser, ParseError
from .interpreter import Interpreter, InterpreterError
from .compiler import Compiler
from .vm import VM, VMRuntimeError
from .builtins import BUILTINS


# --------------------------------------------
# Helpers
# --------------------------------------------
def read_source(path: str) -> str:
    p = pathlib.Path(path)
    if not p.exists():
        raise FileNotFoundError(path)
    return p.read_text(encoding="utf-8")


def pretty_print_compiled(code):
    try:
        print(f"Compiled module: {code.name}")
        print(f"  consts: {len(getattr(code, 'consts', []))}")
        print(f"  instructions: {len(getattr(code, 'instructions', []))}")
        print(f"  nlocals: {getattr(code, 'nlocals', '?')}, argcount: {getattr(code, 'argcount', '?')}")
    except Exception:
        print("  (unable to inspect compiled code)")


def dump_vm_debug(vm: VM):
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
    src = read_source(path)

    # Per-stage timers
    lex_time = parse_time = compile_time = vm_time = interp_time = None

    total_start = time.perf_counter()

    # ------------------ LEX ------------------
    try:
        t0 = time.perf_counter()
        tokens = Lexer(src).lex()
        t1 = time.perf_counter()
        lex_time = t1 - t0
    except LexerError as le:
        print(f"{path}: Lexer error: {le}")
        return 2

    # ------------------ PARSE ------------------
    try:
        t0 = time.perf_counter()
        ast = Parser(tokens).parse()
        t1 = time.perf_counter()
        parse_time = t1 - t0
    except ParseError as pe:
        print(f"{path}: Parse error: {pe}")
        return 2

    # ------------------ COMPILE ------------------
    compiler = Compiler()
    code_obj = None
    try:
        t0 = time.perf_counter()
        if hasattr(compiler, "compile_module"):
            code_obj = compiler.compile_module(ast, name=path)
        elif hasattr(compiler, "compile"):
            code_obj = compiler.compile(ast, name=path)
        elif hasattr(compiler, "compile_all"):
            code_obj = compiler.compile_all(ast, name=path)
        else:
            raise RuntimeError("Compiler does not expose compile/compile_module/compile_all")
        t1 = time.perf_counter()
        compile_time = t1 - t0
    except Exception as ce:
        t1 = time.perf_counter()
        compile_time = t1 - t0
        print(f"{path}: Compile error (compiler raised): {ce}")
        code_obj = None

    # --------------------------------------------
    # Prepare VM
    # --------------------------------------------
    vm = VM(verbose=False)

    for k, v in BUILTINS.items():
        vm.globals.setdefault(k, v)

    # --------------------------------------------
    # RUN ON VM IF POSSIBLE
    # --------------------------------------------
    if code_obj is not None:
        try:
            pretty_print_compiled(code_obj)
            print(f"[VM] Running compiled code for {path} ...")

            t0 = time.perf_counter()
            result = vm.run_code(code_obj)
            t1 = time.perf_counter()
            vm_time = t1 - t0

            print(f"[VM] Completed. Result: {result!r}")

            total = time.perf_counter() - total_start

            # Summary
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

    # --------------------------------------------
    # INTERPRETER FALLBACK
    # --------------------------------------------
    try:
        interp = Interpreter()
        print("[Interpreter] Running AST interpreter...")

        t0 = time.perf_counter()
        interp.interpret(ast)
        t1 = time.perf_counter()
        interp_time = t1 - t0

        print("[Interpreter] Completed.")

        total = time.perf_counter() - total_start

        print("\nTiming summary:")
        print(f"  lex      : {lex_time:.6f}s")
        print(f"  parse    : {parse_time:.6f}s")
        print(f"  compile  : {compile_time:.6f}s")
        print(f"  vm       : N/A")
        print(f"  interp   : {interp_time:.6f}s")
        print(f"  total    : {total:.6f}s")
        return 0

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
