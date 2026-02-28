"""
Falcon Programming Language Package
-----------------------------------

This package contains the JS-like Falcon language implementation (prototype).

Design rules:
- Importing this package MUST have no side effects
- Executable modules (repl, runner) are imported lazily
- Backward compatibility with older prototypes is preserved
"""

from __future__ import annotations
from typing import Callable, Tuple

__version__ = "0.3.0"

__all__ = [
    "run_file",
    "start_repl",
]


def _import_runner_funcs() -> Tuple[Callable[[str], int], Callable[[], None]]:
    """
    Lazily resolve runtime entry points.

    Preferred:
        - falcon.runner.run_file
        - falcon.repl.start_repl

    Fallback:
        - falcon.main.run_file
        - falcon.main.start_repl

    Returns:
        (run_file_callable, start_repl_callable)
    """
    try:
        from .runner import run_file as _run_file
        from .repl import start_repl as _start_repl
        return _run_file, _start_repl
    except Exception:
        try:
            from .main import run_file as _run_file, start_repl as _start_repl
            return _run_file, _start_repl
        except Exception:
            def _missing_run_file(path: str) -> int:
                raise RuntimeError(
                    "No runner available: expected 'falcon.runner' or legacy 'falcon.main'."
                )

            def _missing_start_repl() -> None:
                raise RuntimeError(
                    "No REPL available: expected 'falcon.repl' or legacy 'falcon.main'."
                )

            return _missing_run_file, _missing_start_repl


def run_file(path: str) -> int:
    """
    Run a Falcon .fn file and return an exit code (0 on success).
    """
    run_file_impl, _ = _import_runner_funcs()
    return run_file_impl(path)


def start_repl() -> None:
    """
    Start the interactive Falcon REPL (blocks until exit).
    """
    _, start_repl_impl = _import_runner_funcs()
    return start_repl_impl()
