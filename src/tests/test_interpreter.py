import io
import json
import textwrap
from contextlib import redirect_stdout
from falcon.runner import run_source
from falcon.interpreter import Interpreter, InterpreterError

def capture_run(src: str):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = textwrap.dedent(src)
        rc = run_source(code, filename="<test>")
    return rc, buf.getvalue()

def test_run_print_and_arithmetic():
    src = '''
    print 1 + 2 * 3;
    '''
    rc, out = capture_run(src)
    assert rc == 0
    assert "7" in out.strip()

def test_run_let_and_variable():
    src = '''
    let x = 10;
    print x;
    '''
    rc, out = capture_run(src)
    assert rc == 0
    assert "10" in out.strip()

def test_if_else_behavior():
    src = '''
    if (2 > 1) {
        print "yes";
    } else {
        print "no";
    }
    '''
    rc, out = capture_run(src)
    assert rc == 0
    assert "yes" in out

def test_while_loop_counts():
    src = '''
    let i = 0;
    let s = 0;
    while (i < 3) {
        s = s + i;
        i = i + 1;
    }
    print s;
    '''
    rc, out = capture_run(src)
    assert rc == 0
    assert "3" in out.strip()  # 0+1+2 = 3

def test_runtime_error_reported():
    # using undefined variable should produce non-zero exit
    src = 'print unknownVar;'
    rc, out = capture_run(src)
    # run_source prints error and returns 1 on runtime/parse/lex error
    assert rc == 1
