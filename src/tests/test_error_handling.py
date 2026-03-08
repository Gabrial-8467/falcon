from vyom.interpreter import Interpreter
from vyom.lexer import Lexer
from vyom.parser import Parser
from vyom.type_checker import TypeChecker


def _run(src: str) -> None:
    stmts = Parser(Lexer(src).lex()).parse()
    TypeChecker().check(stmts)
    Interpreter().interpret(stmts)


def test_try_catch_and_throw():
    src = """
    function fail() {
        throw "boom";
    }
    try {
        fail();
    } catch (err) {
        // Just catch the error, don't assign to avoid reserved keyword conflict
    }
    """
    _run(src)
