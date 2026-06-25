#!/usr/bin/env python3
"""Advisory validator: compare coverage_gaps.json lint signals to reconciliation dispositions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from json_helpers import try_load_json  # noqa: E402


def _claim_tokens(gap_row: dict) -> set[str]:
    tokens: set[str] = set()
    for key in ("uncovered_claims", "claim_token_lint_signals"):
        for item in gap_row.get(key) or []:
            if item:
                tokens.add(str(item).lower())
    return tokens


def validate(gaps: dict | None, recon: dict | None) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not gaps:
        warnings.append("coverage_gaps.json not found; nothing to reconcile")
        return errors, warnings
    if not recon:
        gap_rows = gaps.get("slides_with_gaps") or gaps.get("gaps") or []
        if gap_rows:
            warnings.append(
                f"coverage_gaps.json lists {len(gap_rows)} slide(s) with lint signals "
                "but coverage_gap_reconciliation.json is missing"
            )
        return errors, warnings

    reconciled: set[str] = set()
    for item in recon.get("reconciled_items") or []:
        claim = str(item.get("detector_claim") or "").lower()
        if claim:
            reconciled.add(claim)
        for c in item.get("detector_claims") or []:
            reconciled.add(str(c).lower())

    unreconciled: list[str] = []
    for row in gaps.get("slides_with_gaps") or gaps.get("gaps") or []:
        slide = row.get("slide_number")
        for token in _claim_tokens(row):
            if token not in reconciled:
                unreconciled.append(f"slide {slide}: {token}")

    if unreconciled:
        warnings.append(
            f"{len(unreconciled)} detector claim token(s) lack reconciliation entries "
            f"(first 5: {unreconciled[:5]})"
        )
    return errors, warnings


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--work-dir", required=True)
    args = ap.parse_args(argv)
    wd = Path(args.work_dir)
    gaps = try_load_json(wd / "coverage_gaps.json")
    recon = try_load_json(wd / "coverage_gap_reconciliation.json")
    errors, warnings = validate(gaps, recon)
    report = {"errors": errors, "warnings": warnings, "advisory": True}
    out = wd / "coverage_reconciliation_report.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 1 if warnings else 0


if __name__ == "__main__":
    sys.exit(main())
