from falcon.interpreter import Interpreter, InterpreterError
from falcon.lexer import Lexer
from falcon.parser import Parser
from falcon.type_checker import TypeCheckError, TypeChecker


def _parse(src: str):
    return Parser(Lexer(src).lex()).parse()


def test_typed_variable_ok():
    src = "var x: int := 10; x = x + 1;"
    stmts = _parse(src)
    TypeChecker().check(stmts)
    Interpreter().interpret(stmts)


def test_typed_variable_mismatch_fails():
    src = "var x: int := 10; x = 'bad';"
    stmts = _parse(src)
    try:
        TypeChecker().check(stmts)
        assert False, "expected type checker failure"
    except TypeCheckError:
        pass


def test_typed_function_param_and_return_ok():
    src = """
    function add(a: int, b: int): int { return a + b; }
    var z: int := add(2, 3);
    """
    stmts = _parse(src)
    TypeChecker().check(stmts)
    Interpreter().interpret(stmts)


def test_typed_function_return_mismatch_fails():
    src = "function bad(): int { return 'x'; }"
    stmts = _parse(src)
    try:
        TypeChecker().check(stmts)
        assert False, "expected return type mismatch"
    except TypeCheckError:
        pass
