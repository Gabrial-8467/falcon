from falcon.interpreter import Interpreter
from falcon.lexer import Lexer
from falcon.parser import Parser
from falcon.type_checker import TypeChecker


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
        var msg: string := err;
    }
    """
    _run(src)
