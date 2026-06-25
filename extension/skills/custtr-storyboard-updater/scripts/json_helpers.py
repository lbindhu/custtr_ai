#!/usr/bin/env python3
"""Safe JSON loading with clear error messages."""

import json
import sys
from pathlib import Path


def safe_load_json(path, label=None):
    """Load and parse a JSON file, exiting with a clear message on failure.

    Returns the parsed object. Exits the process if the file is missing,
    unreadable, or contains malformed JSON — the error message names the
    file and the parse location so the user can fix it in one pass.
    """
    p = Path(path)
    if label is None:
        label = p.name
    if not p.exists():
        print(f"ERROR: {label} not found: {p}", file=sys.stderr)
        raise SystemExit(2)
    try:
        text = p.read_text(encoding="utf-8")
    except OSError as e:
        print(f"ERROR: cannot read {label} at {p}: {e}", file=sys.stderr)
        raise SystemExit(2)
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(
            f"ERROR: malformed JSON in {label} at {p}\n"
            f"       {e.msg} (line {e.lineno}, col {e.colno})",
            file=sys.stderr,
        )
        raise SystemExit(2)


def try_load_json(path):
    """Load a JSON file, returning None if it doesn't exist.

    Unlike safe_load_json, this does NOT exit on missing files — it returns
    None. It still exits on malformed JSON (a file that exists but can't be
    parsed is always an error).
    """
    p = Path(path)
    if not p.exists():
        return None
    try:
        text = p.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(
            f"ERROR: malformed JSON in {p.name} at {p}\n"
            f"       {e.msg} (line {e.lineno}, col {e.colno})",
            file=sys.stderr,
        )
        raise SystemExit(2)
