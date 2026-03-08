import io
import textwrap
from contextlib import redirect_stdout

from vyom.builtins import BUILTINS
from vyom.compiler import Compiler
from vyom.interpreter import Interpreter
from vyom.lexer import Lexer
from vyom.parser import Parser
from vyom.type_checker import TypeChecker
from vyom.vm import VM


def _run_interpreter(src: str):
    code = textwrap.dedent(src)
    ast = Parser(Lexer(code).lex()).parse()
    TypeChecker().check(ast)
    interp = Interpreter()
    buf = io.StringIO()
    with redirect_stdout(buf):
        interp.interpret(ast)
    return buf.getvalue()


def _run_vm(src: str):
    code = textwrap.dedent(src)
    ast = Parser(Lexer(code).lex()).parse()
    TypeChecker().check(ast)
    compiler = Compiler()
    mod = compiler.compile_module(ast, name="<parity>")
    vm = VM(verbose=False)
    for k, v in BUILTINS.items():
        vm.globals.setdefault(k, v)
    buf = io.StringIO()
    with redirect_stdout(buf):
        vm.run_code(mod)
    return buf.getvalue()


def _assert_parity(src: str):
    interp_out = _run_interpreter(src)
    vm_out = _run_vm(src)
    assert vm_out == interp_out


def test_parity_arithmetic_and_assignment():
    _assert_parity(
        """
        set x = 2;
        x = x + 5;
        show(x);
        """
    )


def test_parity_if_else_branching():
    _assert_parity(
        """
        const x = 10;
        when (x > 5) {
            show("big");
        } else {
            show("small");
        }
        """
    )


def test_parity_while_loop():
    _assert_parity(
        """
        set i = 0;
        set s = 0;
        while (i < 4) {
            s = s + i;
            i = i + 1;
        }
        show(s);
        """
    )


def test_parity_function_call_and_return():
    _assert_parity(
        """
        function add(a: int, b: int) {
            give a + b;
        }
        show(add(7, 8));
        """
    )
