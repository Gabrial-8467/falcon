import io
import textwrap
from contextlib import redirect_stdout

from falcon.runner import run_source


def capture_run(src: str):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = textwrap.dedent(src)
        rc = run_source(code, filename="<test>")
    return rc, buf.getvalue()


def test_basic_match_expression():
    src = """
    function describe_value(x) {
        return match x {
            case 0: "zero";
            case 1: "one";
            case _: "other";
        };
    }
    show(describe_value(0));
    show(describe_value(1));
    show(describe_value(5));
    """
    rc, out = capture_run(src)
    assert rc == 0
    assert "zero" in out
    assert "one" in out
    assert "other" in out


def test_list_pattern_matching():
    src = """
    function analyze_list(lst) {
        return match lst {
            case []: "empty";
            case [x]: "single";
            case [x, y]: "double";
            case _: "longer";
        };
    }
    show(analyze_list([]));
    show(analyze_list([1]));
    show(analyze_list([1, 2]));
    show(analyze_list([1, 2, 3]));
    """
    rc, out = capture_run(src)
    assert rc == 0
    assert "empty" in out
    assert "single" in out
    assert "double" in out
    assert "longer" in out


def test_variable_binding():
    src = """
    function first_element(lst) {
        return match lst {
            case [x]: x;
            case _: null;
        };
    }
    show(first_element([42]));
    show(first_element([]));
    """
    rc, out = capture_run(src)
    assert rc == 0
    assert "42" in out
    assert "null" in out


def test_type_pattern_matching():
    src = """
    function type_check(x) {
        return match x {
            case int: "integer";
            case str: "string";
            case _: "other";
        };
    }
    show(type_check(42));
    show(type_check("hello"));
    show(type_check(true));
    """
    rc, out = capture_run(src)
    assert rc == 0
    assert "integer" in out
    assert "string" in out
    assert "other" in out


def test_match_statement():
    src = """
    function test_match_stmt(n) {
        match n {
            case 0: {
                show("zero");
            }
            case x if x > 0: {
                show("positive");
            }
            case _: {
                show("negative");
            }
        }
    }
    test_match_stmt(0);
    test_match_stmt(5);
    test_match_stmt(-3);
    """
    rc, out = capture_run(src)
    assert rc == 0
    assert "zero" in out
    assert "positive" in out
    assert "negative" in out


def test_dict_pattern_matching():
    src = """
    function get_name(obj) {
        return match obj {
            case {name: name}: name;
            case _: "unknown";
        };
    }
    show(get_name({name: "Alice"}));
    show(get_name({}));
    """
    rc, out = capture_run(src)
    assert rc == 0
    assert "Alice" in out
    assert "unknown" in out


def test_or_pattern():
    src = """
    function classify(x) {
        return match x {
            case 0 | 1: "small";
            case 2 | 3: "medium";
            case _: "large";
        };
    }
    show(classify(0));
    show(classify(2));
    show(classify(5));
    """
    rc, out = capture_run(src)
    assert rc == 0
    assert "small" in out
    assert "medium" in out
    assert "large" in out


def test_wildcard_pattern():
    src = """
    function always_match(x) {
        return match x {
            case _: "matched";
        };
    }
    show(always_match(42));
    show(always_match("hello"));
    show(always_match(null));
    """
    rc, out = capture_run(src)
    assert rc == 0
    # Should have "matched" three times
    assert out.count("matched") == 3


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
