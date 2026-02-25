import io
import json
import textwrap
from contextlib import redirect_stdout

from falcon.runner import run_source


def capture_run(src: str):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = textwrap.dedent(src)
        rc = run_source(code, filename="<test>")
    return rc, buf.getvalue()


def test_regex_match():
    src = """
    let result = regexMatch('^(\\w+)-(\\d+)$', 'item-42');
    print result;
    """
    rc, out = capture_run(src)
    assert rc == 0
    # Expect output like ['item', '42']
    assert "['item', '42']" in out


def test_regex_search_no_match():
    src = """
    let result = regexSearch('foo', 'bar');
    print result;
    """
    rc, out = capture_run(src)
    assert rc == 0
    assert "None" in out


def test_regex_findall():
    src = """
    let result = regexFindAll('\\d+', 'a1b2c3');
    print result;
    """
    rc, out = capture_run(src)
    assert rc == 0
    # Should be ['1', '2', '3']
    assert "['1', '2', '3']" in out
