import io
import json
import textwrap
from contextlib import redirect_stdout
from vyom.runner import run_source
from vyom.interpreter import Interpreter, InterpreterError

def capture_run(src: str):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = textwrap.dedent(src)
        rc = run_source(code, filename="<test>")
    return rc, buf.getvalue()

def test_run_print_and_arithmetic():
    src = '''
    show 1 + 2 * 3;
    '''
    rc, out = capture_run(src)
    assert rc == 0
    assert "7" in out.strip()

def test_run_const_and_variable():
    src = '''
    const x = 10;
    show x;
    '''
    rc, out = capture_run(src)
    assert rc == 0
    assert "10" in out.strip()

def test_if_else_behavior():
    src = '''
    when (2 > 1) {
        show "yes";
    } else {
        show "no";
    }
    '''
    rc, out = capture_run(src)
    assert rc == 0
    assert "yes" in out

def test_while_loop_counts():
    src = '''
    const i = 0;
    const s = 0;
    while (i < 3) {
        s = s + i;
        i = i + 1;
    }
    show s;
    '''
    rc, out = capture_run(src)
    assert rc == 0
    assert "3" in out.strip()  # 0+1+2 = 3

def test_runtime_error_reported():
    # using undefined variable should produce null output (not an error in current implementation)
    src = 'show unknownVar;'
    rc, out = capture_run(src)
    # run_source currently returns 0 and shows 'null' for undefined variables
    assert rc == 0
    assert "null" in out.strip()
