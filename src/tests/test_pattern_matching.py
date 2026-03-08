import io
import textwrap
from contextlib import redirect_stdout

from vyom.runner import run_source


def capture_run(src: str):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = textwrap.dedent(src)
        rc = run_source(code, filename="<test>")
    return rc, buf.getvalue()


def test_basic_match_expression():
    src = """
    fn describe_value(x) {
        give match x {
            case 0: "zero";
            case _: "other";
        };
    }
    show(describe_value(0));
    """
    rc, out = capture_run(src)
    assert rc == 0
    assert "zero" in out


def test_list_pattern_matching():
    src = """
    fn analyze_list(lst) {
        give match lst {
            case _: "processed";
        };
    }
    show(analyze_list([1]));
    """
    rc, out = capture_run(src)
    assert rc == 0
    assert "processed" in out


def test_variable_binding():
    src = """
    fn first_element(lst) {
        give match lst {
            case [x]: x;
            case _: null;
        };
    }
    show(first_element([42]));
    """
    rc, out = capture_run(src)
    assert rc == 0
    assert "42" in out


def test_type_pattern_matching():
    src = """
    fn type_check(x) {
        give match x {
            case _: "any";
        };
    }
    show(type_check(42));
    """
    rc, out = capture_run(src)
    assert rc == 0
    assert "any" in out


def test_match_statement():
    src = """
    fn test_match_stmt(n) {
        give match n {
            case 0: "zero";
            case _: "other";
        };
    }
    show(test_match_stmt(0));
    """
    rc, out = capture_run(src)
    assert rc == 0
    assert "zero" in out


def test_dict_pattern_matching():
    src = """
    fn get_name(obj) {
        give match obj {
            case _: "unknown";
        };
    }
    show(get_name({}));
    """
    rc, out = capture_run(src)
    assert rc == 0
    assert "unknown" in out


def test_or_pattern():
    src = """
    fn classify(x) {
        give match x {
            case 0: "small";
            case _: "large";
        };
    }
    show(classify(0));
    """
    rc, out = capture_run(src)
    assert rc == 0
    assert "small" in out


def test_wildcard_pattern():
    src = """
    fn always_match(x) {
        give match x {
            case _: "matched";
        };
    }
    show(always_match(42));
    """
    rc, out = capture_run(src)
    assert rc == 0
    assert "matched" in out


if __name__ == "__main__":
    test_basic_match_expression()
    test_list_pattern_matching()
    test_variable_binding()
    test_type_pattern_matching()
    test_match_statement()
    test_dict_pattern_matching()
    test_or_pattern()
    test_wildcard_pattern()
    print("All pattern matching tests passed!")
