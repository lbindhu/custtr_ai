#!/usr/bin/env python3
"""Scan skill docs for stale architecture phrases."""

from __future__ import annotations

import re
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent

BANNED_PATTERNS = [
    (re.compile(r"minimum.*nabu", re.I), "fixed NABU minimum"),
    (re.compile(r"at least.*confluence", re.I), "fixed Confluence minimum"),
    (re.compile(r"identify uncovered factual claims", re.I), "non-advisory gap detector wording"),
    (re.compile(r"embed.*concept_decomposition.*verification_report", re.I), "embedded concept_decomposition"),
    (re.compile(r"must run in parallel", re.I), "mandatory parallelism"),
    (re.compile(r"(?<![\w-])--require-coverage\b"), "removed require-coverage flag"),
]


def _line_context(text: str, pos: int) -> str:
    start = text.rfind("\n", 0, pos) + 1
    end = text.find("\n", pos)
    if end == -1:
        end = len(text)
    return text[start:end].lower()


def scan(root: Path | None = None) -> list[str]:
    root = root or SKILL_ROOT
    violations: list[str] = []
    for path in sorted(root.rglob("*")):
        if path.suffix.lower() not in {".md", ".py"}:
            continue
        if path.name in {"lint_skill_docs.py", "test_doc_consistency.py"}:
            continue
        if "tests" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        rel = path.relative_to(root)
        for pattern, label in BANNED_PATTERNS:
            if "detect_source_gaps" in text and label == "non-advisory gap detector wording":
                if "advisory" in text.lower():
                    continue
            for match in pattern.finditer(text):
                ctx = _line_context(text, match.start())
                if label == "removed require-coverage flag" and any(
                    w in ctx for w in ("removed", "deprecated", "legacy", "do not")
                ):
                    continue
                if label == "embedded concept_decomposition" and any(
                    w in ctx for w in ("do not", "deprecated", "not nest", "standalone")
                ):
                    continue
                line = text.count("\n", 0, match.start()) + 1
                violations.append(f"{rel}:{line}: {label} -> {match.group(0)!r}")
    return violations


def main() -> int:
    violations = scan()
    if violations:
        print("Stale architecture phrase violations:")
        for v in violations:
            print(f"  {v}")
        return 1
    print("lint_skill_docs: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
