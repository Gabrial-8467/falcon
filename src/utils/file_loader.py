"""
Safe file loading utility for the Falcon language runtime.

This ensures:
- All file loads stay inside a configured base directory.
- Path traversal is blocked (`../..` cannot escape sandbox).
- Module and script loading can reuse the same secure logic.

Used by: runner, future module system, REPL load command.
"""

from __future__ import annotations

import pathlib
from typing import Optional


# By default, use current working directory as sandbox.
# Can be changed by the host application.
BASE_SAFE_DIR = pathlib.Path.cwd().resolve()


def _resolve_safe(path: str | pathlib.Path) -> pathlib.Path:
    """
    Resolve a path safely inside BASE_SAFE_DIR.
    Raises PermissionError if trying to escape the sandbox.
    """
    p = pathlib.Path(path)

    # Normalize absolute/relative paths
    if p.is_absolute():
        p = p.resolve()
    else:
        p = (BASE_SAFE_DIR / p).resolve()

    # Enforce sandbox restriction
    try:
        p.relative_to(BASE_SAFE_DIR)
    except Exception:
        raise PermissionError(f"Access outside sandbox not allowed: {p}")

    return p


def load_file(path: str, encoding: str = "utf-8") -> str:
    """
    Load file contents safely and return text.
    Raises FileNotFoundError, PermissionError, or IOError.
    """
    resolved = _resolve_safe(path)

    if not resolved.exists():
        raise FileNotFoundError(f"File not found: {resolved}")

    if resolved.is_dir():
        raise IsADirectoryError(f"Cannot load directory: {resolved}")

    try:
        return resolved.read_text(encoding=encoding)
    except Exception as e:
        raise IOError(f"Failed to read file {resolved}: {e}")
