#!/usr/bin/env python3
"""Scope-consistency scan (Rule 17).

Flags slides that combine a portfolio-scope phrase (from
stale_terms.portfolio_scope_phrases) with a stale-token specific (from
stale_terms.stale_terms[].token) without an explicit Gen 1/Gen 2 qualifier.

Writes scope_consistency.json with per-slide findings.
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stale_terms import load_stale_terms
from json_helpers import safe_load_json  # noqa: E402

GEN_QUALIFIER_RE = re.compile(r"\bGen\s*[12]\b", re.I)


def scan_scope_consistency(deck_extract, stale_terms_doc):
    scope_phrases = [p.lower() for p in stale_terms_doc.get("portfolio_scope_phrases", [])]
    stale_tokens = [e.get("token", "").lower() for e in stale_terms_doc.get("stale_terms", [])]
    stale_tokens = [t for t in stale_tokens if t]

    if not scope_phrases or not stale_tokens:
        return []

    results = []
    for slide in deck_extract.get("slides", []):
        sno = slide.get("slide_number", 0)
        all_text = " ".join(t.get("text", "") for t in slide.get("texts", []))
        all_lower = all_text.lower()

        found_scope = [p for p in scope_phrases if p in all_lower]
        if not found_scope:
            continue

        has_qualifier = bool(GEN_QUALIFIER_RE.search(all_text))
        if has_qualifier:
            continue

        found_stale = [t for t in stale_tokens if t in all_lower]
        if not found_stale:
            continue

        results.append({
            "slide_number": sno,
            "title": slide.get("title", ""),
            "scope_phrases_found": found_scope,
            "stale_tokens_found": found_stale,
            "issue": (
                f"Slide uses portfolio-scope phrase(s) {found_scope} "
                f"alongside stale-token specific(s) {found_stale} "
                f"without a Gen 1/Gen 2 qualifier."
            ),
        })

    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deck-extract", required=True)
    ap.add_argument("--stale-terms", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    deck_extract = safe_load_json(args.deck_extract, "deck_extract.json")
    stale_terms_doc = load_stale_terms(Path(args.stale_terms))

    results = scan_scope_consistency(deck_extract, stale_terms_doc)

    Path(args.output).write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"scope_consistency_scan: {len(results)} violation(s)")
    if results:
        for r in results:
            print(f"  slide {r['slide_number']}: {r['issue']}")


if __name__ == "__main__":
    main()
