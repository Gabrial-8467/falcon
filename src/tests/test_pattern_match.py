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


def test_regex_match_dict():
    src = """
    let result = regexMatchDict('^(?P<name>\\w+)-(?P<id>\\d+)$', 'item-42');
    print result;
    """
    rc, out = capture_run(src)
    assert rc == 0
    # Expect output like {'name': 'item', 'id': '42'}
    assert "{'name': 'item', 'id': '42'}" in out


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

def test_glob_match():
    src = """
    let ok = globMatch('**/*.py', 'src/falcon/utils/pattern_match.py');
    print ok;
    """
    rc, out = capture_run(src)
    assert rc == 0
    assert "True" in out

def test_match_pattern():
    src = """
    let ok1 = matchPattern([1, 2], [int, int]);
    let ok2 = matchPattern([1, "a"], [int, str]);
    let ok3 = matchPattern([1, 2, 3], [int, int]);
    print ok1, ok2, ok3;
    """
    rc, out = capture_run(src)
    assert rc == 0
    assert "True True False" in out
