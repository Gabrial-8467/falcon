import io
import pathlib
from contextlib import redirect_stdout
from falcon.runner import run_file


EXAMPLES_DIR = pathlib.Path("examples")


def run_example(example_name: str):
    """Helper to run an example .fn file and capture stdout."""
    example_path = EXAMPLES_DIR / example_name
    assert example_path.exists(), f"Example file not found: {example_path}"

    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = run_file(example_path.as_posix())
    output = buf.getvalue()
    return rc, output


def test_hello_example():
    rc, output = run_example("hello.fn")
    assert rc == 0
    assert "Hello" in output or output.strip() != ""


def test_factorial_example():
    rc, output = run_example("factorial.fn")
    assert rc == 0
    # Must print some numeric result
    assert any(char.isdigit() for char in output)


def test_closure_example():
    rc, output = run_example("closure.fn")
    assert rc == 0
    # Closure example should output increments like 1,2,3...
    # We don't enforce exact text, just ensure *some* numeric output.
    assert any(ch.isdigit() for ch in output)


def test_async_stub_example():
    rc, output = run_example("async_stub.fn")
    assert rc == 0
    # async example probably uses promise stub, so must print something
    assert output.strip() != ""
