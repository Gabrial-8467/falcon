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
from typing import Any, Dict, List

from .lexer import Lexer, LexerError
from .parser import Parser, ParseError
from .interpreter import Interpreter, InterpreterError
# only import Compiler; don't require a specific CompileError symbol from compiler.py
from .compiler import Compiler
from .vm import VM, VMRuntimeError
from .builtins import BUILTINS

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

    try:
        compiled = getattr(vm, "compiled_functions", None)
        if compiled:
            print("Compiled functions:")
            for fn in compiled:
                try:
                    name = getattr(fn, "name", "<anon>")
                    cs = getattr(fn, "closure_snapshot", None)
                    print(f"  - {name} closure keys: {sorted(list(cs.keys())) if isinstance(cs, dict) else cs}")
                except Exception:
                    print("  - <could not inspect function>")
    except Exception:
        pass

    print("=== END VM DEBUG ===")

def run_file(path: str):
    src = read_source(path)
    # Lex/Parse
    try:
        tokens = Lexer(src).lex()
    except LexerError as le:
        print(f"{path}: Lexer error: {le}")
        return 2

    try:
        ast = Parser(tokens).parse()
    except ParseError as pe:
        print(f"{path}: Parse error: {pe}")
        return 2

    # Attempt compile -> VM
    compiler = Compiler()
    code_obj = None
    try:
        # many compiler implementations expose compile_module or compile; adapt if needed
        if hasattr(compiler, "compile_module"):
            code_obj = compiler.compile_module(ast, name=path)
        elif hasattr(compiler, "compile"):
            code_obj = compiler.compile(ast, name=path)
        else:
            # fallback: try a generic compile_all or raise for clearer message
            if hasattr(compiler, "compile_all"):
                code_obj = compiler.compile_all(ast, name=path)
            else:
                raise RuntimeError("Compiler does not expose compile/compile_module/compile_all")
    except Exception as ce:
        print(f"{path}: Compile error (compiler raised): {ce}")
        # fall back to interpreter
        code_obj = None

    vm = VM(verbose=False)
    # ensure builtins present in VM globals
    for k, v in BUILTINS.items():
        if k not in vm.globals:
            vm.globals[k] = v

    if code_obj is not None:
        try:
            pretty_print_compiled(code_obj)
            print(f"[VM] Running compiled code for {path} ...")
            res = vm.run_code(code_obj)
            print(f"[VM] Completed. Result: {res!r}")
            return 0
        except VMRuntimeError as ve:
            print(f"[VM ERROR] {ve}")
            traceback.print_exc(limit=1, file=sys.stdout)
            dump_vm_debug(vm)
            print("Falling back to interpreter...")
        except Exception as e:
            print(f"[VM ERROR] Unexpected exception: {e}")
            traceback.print_exc(limit=1, file=sys.stdout)
            dump_vm_debug(vm)
            print("Falling back to interpreter...")

    # Interpreter fallback
    try:
        interp = Interpreter()
        print("[Interpreter] Running AST interpreter...")
        interp.interpret(ast)
        print("[Interpreter] Completed.")
        return 0
    except InterpreterError as ie:
        print(f"{path}: Runtime error: {ie}")
        traceback.print_exc()
        return 3
    except Exception as e:
        print(f"{path}: Unexpected runtime error: {e}")
        traceback.print_exc()
        return 3


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
