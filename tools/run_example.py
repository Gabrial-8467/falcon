"""
Small helper tool to run Falcon example programs easily.

Usage:
    python tools/run_example.py examples/hello.fn
    python tools/run_example.py hello

If a bare name is given (e.g., "hello"), it automatically looks for:
    examples/hello.fn
"""

from __future__ import annotations

import sys
import pathlib

# Allow importing the local falcon package without installing
ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from falcon.runner import run_file


def resolve_example(name: str) -> pathlib.Path:
    """
    Resolve input into an actual example path.
    Accepts either:
      - full path: examples/hello.fn
      - bare name: hello  -> examples/hello.fn
    """
    p = pathlib.Path(name)

    # If full path exists, use it
    if p.exists():
        return p

    # Try "examples/<name>.fn"
    example_dir = ROOT / "examples"
    candidate = example_dir / f"{name}.fn"
    if candidate.exists():
        return candidate

    raise FileNotFoundError(f"Could not find example '{name}'")


def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/run_example.py <example.fn | name>")
        sys.exit(1)

    target = sys.argv[1]

    try:
        example_path = resolve_example(target)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(2)

    print(f"Running example: {example_path}")
    result = run_file(example_path.as_posix())
    sys.exit(result)


if __name__ == "__main__":
    main()
