# src/falcon/runner.py
from __future__ import annotations
import pathlib
import sys

from .lexer import Lexer
from .parser import Parser
from .compiler import Compiler
from .vm import VM
from .interpreter import Interpreter


def run_source(src: str, filename="<source>"):
    # 1) Lex + parse
    tokens = Lexer(src).lex()
    ast = Parser(tokens).parse()

    # 2) Compile to bytecode
    compiler = Compiler()
    code = compiler.compile_module(ast)

    # 3) Run VM
    vm = VM()
    try:
        vm.run_code(code)
    except Exception as e:
        print(f"[VM ERROR] {e}")
        print("Falling back to interpreter...")
        interp = Interpreter()
        interp.interpret(ast)


def run_file(path: str):
    p = pathlib.Path(path)
    src = p.read_text(encoding="utf-8")
    print(f"Running: {p}")
    run_source(src, filename=str(p))


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("file", help="*.fn file")
    args = ap.parse_args()
    run_file(args.file)
