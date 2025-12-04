"""
Falcon Programming Language Package
-----------------------------------

This package contains the JS-like Falcon language implementation (prototype).
It exposes a small top-level API and is defensive so older prototypes that
use ``main.py`` still work.

Importing this package does NOT execute user code.
"""

__version__ = "0.3.0"

__all__ = [
    "run_file",
    "start_repl",
]


def _import_runner_funcs():
    """
    Try to import runner.start/run style API (preferred).
    Fall back to legacy .main.run_file / .main.start_repl if runner/repl are absent.
    Returns a tuple: (run_file_callable, start_repl_callable)
    """
    try:
        from .runner import run_file as _run_file
        from .repl import start_repl as _start_repl
        return _run_file, _start_repl
    except Exception:
        # Fallback to legacy single-file runtime (main.py) if present
        try:
            from .main import run_file as _run_file, start_repl as _start_repl
            return _run_file, _start_repl
        except Exception:
            # If neither is available, provide stubs that raise helpful errors when called.
            def _missing_run_file(path: str) -> int:
                raise RuntimeError("No runner available: 'falcon.runner' or 'falcon.main' not found.")
            def _missing_start_repl() -> None:
                raise RuntimeError("No repl available: 'falcon.repl' or 'falcon.main' not found.")
            return _missing_run_file, _missing_start_repl


_run_file_impl, _start_repl_impl = _import_runner_funcs()


def run_file(path: str) -> int:
    """Run a .fn file and return an exit code (0 on success)."""
    return _run_file_impl(path)


def start_repl() -> None:
    """Start the interactive Falcon REPL (blocks until exit)."""
    return _start_repl_impl()
