"""
Built-in functions for the Falcon runtime (extended).

Adds:
- readFile(path) and writeFile(path, content) with safety checks
- Promise stub for future async support (sync placeholder)
- console object with log method
- toString(value) builtin for explicit conversion
- show(...) as the preferred output function
"""

from __future__ import annotations

from typing import Any, List, Callable, Dict
import sys
import pathlib
import json

# --- helpers ---
def _to_string_impl(x: Any) -> str:
    """
    Canonical string conversion used by toString() and interpreter coercion.
    - None -> "null"
    - bool -> "true"/"false"
    - str -> unchanged
    - numbers -> str()
    - lists/dicts -> JSON-ish via json.dumps if possible
    - fallback -> repr()
    """
    if x is None:
        return "null"
    if isinstance(x, bool):
        return "true" if x else "false"
    if isinstance(x, str):
        return x
    if isinstance(x, (int, float)):
        return str(x)
    try:
        return json.dumps(x)
    except Exception:
        try:
            return repr(x)
        except Exception:
            return "<unrepresentable>"

def _to_display(x: Any) -> str:
    """
    Short helper for printing with spaces (used by builtin_show).
    """
    return _to_string_impl(x)


# --- show / console ---
def builtin_show(*args: Any) -> None:
    """Preferred Falcon output function: show(...)."""
    out = " ".join(_to_display(a) for a in args)
    # use host stdout
    print(out)

class _Console:
    @staticmethod
    def log(*args: Any) -> None:
        builtin_show(*args)

    @staticmethod
    def error(*args: Any) -> None:
        print("ERROR:", *[_to_display(a) for a in args], file=sys.stderr)


# --- file I/O with safety checks ---
# Restrict file operations to the current working directory and its subdirectories
_BASE_SAFE_DIR = pathlib.Path.cwd().resolve()

def _resolve_safe_path(path: str) -> pathlib.Path:
    p = pathlib.Path(path)
    # Normalize and resolve relative paths under base dir
    if p.is_absolute():
        p = p.resolve()
    else:
        p = (_BASE_SAFE_DIR / p).resolve()
    try:
        p.relative_to(_BASE_SAFE_DIR)
    except Exception:
        raise PermissionError("File operation outside safe directory is not allowed")
    return p

def builtin_readFile(path: str) -> str:
    p = _resolve_safe_path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))
    if p.is_dir():
        raise IsADirectoryError(str(p))
    return p.read_text(encoding="utf-8")

def builtin_writeFile(path: str, content: str) -> None:
    p = _resolve_safe_path(path)
    # create parent dirs if needed
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(str(content), encoding="utf-8")


# --- toString builtin (explicit conversion) ---
def toString(value: Any) -> str:
    """Built-in toString(value) available to Falcon scripts."""
    return _to_string_impl(value)


# --- async-friendly Promise stub (synchronous placeholder) ---
class Promise:
    """
    Very small placeholder Promise-like object.
    - then(fn) executes fn immediately with the resolved value
    - catch(fn) is a noop unless error stored
    This is synchronous and only exists so user code can call promise.then(...).
    Real async features can be integrated later.
    """
    def __init__(self, executor: Callable[[Callable[[Any], None], Callable[[Any], None]], None] | None = None):
        self._resolved = False
        self._rejected = False
        self._value = None
        self._error = None
        self._then_callbacks: List[Callable[[Any], Any]] = []
        self._catch_callbacks: List[Callable[[Any], Any]] = []
        if executor is not None:
            try:
                def resolve(v: Any):
                    self._resolved = True
                    self._value = v
                    for cb in list(self._then_callbacks):
                        try:
                            cb(self._value)
                        except Exception:
                            pass
                def reject(e: Any):
                    self._rejected = True
                    self._error = e
                    for cb in list(self._catch_callbacks):
                        try:
                            cb(self._error)
                        except Exception:
                            pass
                executor(resolve, reject)
            except Exception as e:
                self._rejected = True
                self._error = e

    def then(self, fn: Callable[[Any], Any]) -> "Promise":
        if self._resolved:
            try:
                fn(self._value)
            except Exception:
                pass
        else:
            self._then_callbacks.append(fn)
        return self

    def catch(self, fn: Callable[[Any], Any]) -> "Promise":
        if self._rejected:
            try:
                fn(self._error)
            except Exception:
                pass
        else:
            self._catch_callbacks.append(fn)
        return self

    @staticmethod
    def resolve(value: Any) -> "Promise":
        p = Promise()
        p._resolved = True
        p._value = value
        return p

    @staticmethod
    def reject(error: Any) -> "Promise":
        p = Promise()
        p._rejected = True
        p._error = error
        return p


# --- other small builtins ---
def builtin_len(obj: Any) -> int:
    if obj is None:
        raise TypeError("len(null) is not supported")
    if isinstance(obj, (str, list, tuple, dict, set)):
        return len(obj)
    if hasattr(obj, "__len__"):
        return obj.__len__()  # type: ignore
    raise TypeError(f"Object of type {type(obj).__name__} has no length")

def builtin_range(start: int, stop: int | None = None, step: int = 1) -> List[int]:
    if stop is None:
        stop = int(start)
        start = 0
    start = int(start); stop = int(stop); step = int(step)
    if step == 0:
        raise ValueError("range() step argument must not be zero")
    return list(range(start, stop, step))

def builtin_typeof(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    if callable(value):
        return "function"
    return "object"

def builtin_assert(cond: Any, message: str | None = None) -> None:
    truthy = cond is not None and (cond is True or (isinstance(cond, (int, float)) and cond != 0) or bool(cond))
    if not truthy:
        raise AssertionError(message or "Assertion failed")

def builtin_exit(code: int = 0) -> None:
    raise SystemExit(int(code))


# --- export builtins mapping ---
BUILTINS: Dict[str, Callable[..., Any]] = {
    # preferred Falcon output
    "show": builtin_show,
    "len": builtin_len,
    "range": builtin_range,
    "typeOf": builtin_typeof,
    "assert": builtin_assert,
    "exit": builtin_exit,
    # file ops
    "readFile": builtin_readFile,
    "writeFile": builtin_writeFile,
    # toString explicit conversion
    "toString": toString,
    # Promise / async helpers
    "Promise": Promise,
    # console
    "console": _Console(),
}
