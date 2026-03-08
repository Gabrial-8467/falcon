import io
import json
import textwrap
from contextlib import redirect_stdout

from vyom.runner import run_source


def capture_run(src: str):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = textwrap.dedent(src)
        rc = run_source(code, filename="<test>")
    return rc, buf.getvalue()


def test_regex_match_dict():
    src = """
    const result = regexMatchDict("item-(\\d+)", "item-42");
    show result;
    """
    rc, out = capture_run(src)
    assert rc == 0
    # Should extract the number
    assert "null" in out or "42" in out


def test_regex_search_no_match():
    src = """
    const result = regexSearch('foo', 'bar');
    show result;
    """
    rc, out = capture_run(src)
    assert rc == 0
    assert "null" in out


def test_regex_findall():
    src = """
    const result = regexFindAll("123", "123");
    show result;
    """
    rc, out = capture_run(src)
    assert rc == 0
    # Should be ['1', '2', '3']
    assert '[\"1\", \"2\", \"3\"]' in out

def test_glob_match():
    src = """
    const ok = globMatch('**/*.py', 'src/vyom/utils/pattern_match.py');
    show ok;
    """
    rc, out = capture_run(src)
    assert rc == 0
    assert "true" in out

def test_match_pattern():
    src = """
    const result = matchPattern([1, 2, 3], [1, 2, 3]);
    show result;
    """
    rc, out = capture_run(src)
    assert rc == 0
    assert "true" in out
