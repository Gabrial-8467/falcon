# src/falcon/builtins.py
"""
Built-in functions for the Falcon runtime (extended).

Provides:
- show(...) as the preferred output function (used by VM)
- readFile(path) and writeFile(path, content) with safety checks
- Promise stub for future async support (synchronous placeholder)
- console object with log/error methods
- toString(value) and internal _to_string_impl for coercion
- other small runtime helpers (len, range, typeOf, assert, exit)
"""

from __future__ import annotations
from typing import Any, List, Callable, Dict
import sys
import pathlib
import json
from .utils.pattern_match import match as regexMatch, search as regexSearch, findall as regexFindAll, match_dict as regexMatchDict, glob_match as globMatch
from .utils.struct_match import match_pattern as matchPattern
# --------------------
# String conversion helpers
# --------------------
def _to_string_impl(x: Any) -> str:
    """
    Canonical string conversion used by toString() and VM coercion.
    - None -> "null"
    - bool -> "true"/"false"
    - str -> unchanged
    - numbers -> str()
    - lists/dicts -> JSON via json.dumps if possible
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
        # Prefer readable JSON for lists/dicts where possible
        return json.dumps(x)
    except Exception:
        try:
            return repr(x)
        except Exception:
            return "<unrepresentable>"

def _to_display(x: Any) -> str:
    """Short helper for user-facing printing."""
    return _to_string_impl(x)

# --------------------
# Output helpers
# --------------------
def show(*args: Any) -> None:
    """Preferred Falcon output function: show(...)."""
    out = " ".join(_to_display(a) for a in args)
    print(out)

class _Console:
    @staticmethod
    def log(*args: Any) -> None:
        show(*args)

    @staticmethod
    def error(*args: Any) -> None:
        print("ERROR:", " ".join(_to_display(a) for a in args), file=sys.stderr)

# --------------------
# File I/O with safety checks
# --------------------
# Restrict file operations to the current working directory and its subdirectories
_BASE_SAFE_DIR = pathlib.Path.cwd().resolve()

def _resolve_safe_path(path: str) -> pathlib.Path:
    p = pathlib.Path(path)
    # Normalize and resolve relative paths under base dir
    p = p.resolve() if p.is_absolute() else (_BASE_SAFE_DIR / p).resolve()
    try:
        p.relative_to(_BASE_SAFE_DIR)
    except Exception:
        raise PermissionError("File operation outside safe directory is not allowed")
    return p

def readFile(path: str) -> str:
    """Read file text under the safe base directory."""
    p = _resolve_safe_path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))
    if p.is_dir():
        raise IsADirectoryError(str(p))
    return p.read_text(encoding="utf-8")

def writeFile(path: str, content: Any) -> None:
    """Write file text under the safe base directory. Content coerced to str."""
    p = _resolve_safe_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(str(content), encoding="utf-8")

# --------------------
# toString builtin
# --------------------
def toString(value: Any) -> str:
    """Built-in toString(value) available to Falcon scripts."""
    return _to_string_impl(value)

# --------------------
# Promise stub (synchronous placeholder)
# --------------------
class Promise:
    """
    Minimal Promise-like placeholder:
    - then(fn) executes fn immediately if resolved, or defers if not
    - catch(fn) executes on rejection
    This is synchronous and exists to allow promise.then(...) in user code.
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

# --------------------
# Runtime collection wrapper classes
# --------------------
class RuntimeList(list):
    def length(self) -> int:
        return len(self)

class RuntimeTuple(tuple):
    def length(self) -> int:
        return len(self)

class RuntimeDict(dict):
    def get(self, key, default=None):
        return super().get(key, default)
    def set(self, key, value):
        self[key] = value
    def keys(self):
        return list(super().keys())
    def values(self):
        return list(super().values())

class RuntimeSet(set):
    def add(self, value):
        super().add(value)
    def remove(self, value):
        super().remove(value)
    def contains(self, value):
        return value in self

class FixedArray:
    def __init__(self, size):
        self._size = int(size)
        self._data = [None] * self._size
    def __getitem__(self, idx):
        if not isinstance(idx, int):
            raise TypeError("Array index must be integer")
        if idx < 0:
            idx = self._size + idx
        if idx < 0 or idx >= self._size:
            raise IndexError("Array index out of bounds")
        return self._data[idx]
    def __setitem__(self, idx, val):
        if not isinstance(idx, int):
            raise TypeError("Array index must be integer")
        if idx < 0:
            idx = self._size + idx
        if idx < 0 or idx >= self._size:
            raise IndexError("Array index out of bounds")
        self._data[idx] = val
    def length(self) -> int:
        return self._size
    def __repr__(self):
        return f"array[{self._size}]" + repr(self._data)


def len_builtin(obj: Any) -> int:
    if obj is None:
        raise TypeError("len(null) is not supported")
    if isinstance(obj, (str, list, tuple, dict, set)):
        return len(obj)
    if hasattr(obj, "__len__"):
        return obj.__len__()  # type: ignore
    raise TypeError(f"Object of type {type(obj).__name__} has no length")

def range_builtin(start: int, stop: int | None = None, step: int = 1) -> List[int]:
    if stop is None:
        stop = int(start)
        start = 0
    start = int(start); stop = int(stop); step = int(step)
    if step == 0:
        raise ValueError("range() step argument must not be zero")
    return list(range(start, stop, step))

def typeOf(value: Any) -> str:
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

def assert_builtin(cond: Any, message: str | None = None) -> None:
    truthy = cond is not None and (cond is True or (isinstance(cond, (int, float)) and cond != 0) or bool(cond))
    if not truthy:
        raise AssertionError(message or "Assertion failed")

def exit_builtin(code: int = 0) -> None:
    raise SystemExit(int(code))

# --------------------
# Export builtins mapping (used by VM)
# --------------------
BUILTINS: Dict[str, Callable[..., Any]] = {
    "list": lambda *a: RuntimeList(a),
    "tuple": lambda *a: RuntimeTuple(a),
    "dict": lambda **kw: RuntimeDict(kw),
    "set": lambda *a: RuntimeSet(a),
    "array": lambda size: FixedArray(size),
    "len": len_builtin,
    "range": range_builtin,
    "typeOf": typeOf,
    "assert": assert_builtin,
    "exit": exit_builtin,
    "readFile": readFile,
    "writeFile": writeFile,
    "toString": toString,
    "regexMatchDict": regexMatchDict,
    "regexSearch": regexSearch,
    "regexFindAll": regexFindAll,
    "globMatch": globMatch,
    "matchPattern": matchPattern,

}

# Backwards-compatible aliases (if VM or other code expects these names)
_to_string_impl = _to_string_impl
