#!/usr/bin/env python3
"""Intra-slide term consistency scan (Rule 35).

Detects near-miss variants of the same technical identifier *within a single
slide* (across all text shapes and the speaker notes). The canonical failure
this catches shipped in a real run: a callout said ``A78AE``, a diagram label
said ``A78E``, and the notes said ``A78AE`` — a one-letter typo that the
stale-term scan cannot catch because ``A78E`` != ``A78AE`` and neither is a
generation-delta token, and that the per-slide LLM audit batch-cleared because
"the topic is already the target generation".

Detection rule (high precision, low noise):

Two distinct technical tokens on the same slide are flagged as a near-miss
inconsistency when they differ ONLY by an INTERNAL inserted / deleted /
substituted LETTER within a small edit distance. Specifically, a flagged pair
must satisfy all of:

  * both tokens are "technical" (contain at least one letter AND one digit,
    length >= 3) — e.g. A78AE, A78E, CPM5, DDR5, Gen6;
  * the character-level diff begins and ends with an EQUAL block (i.e. the
    edit is internal, not a prefix or suffix change);
  * at least one differing character is a LETTER (pure-digit differences such
    as CPM5 vs CPM6, DDR4 vs DDR5, A72 vs A78 are legitimate generation
    siblings and are NOT flagged);
  * the total edit size is <= 2 characters.

Prefix/suffix variants (LPDDR5 vs DDR5, DDR5 vs DDR5X) are intentionally NOT
flagged because they are almost always legitimately distinct products.

A small curated dictionary of common technical-doc misspellings is also
scanned and emitted as ADVISORY signals (``advisory: true``); the audit gate
treats those as warnings rather than hard reconciliation requirements.

Writes consistency_scan.json — a flat JSON list of violation objects:

    [
      {
        "slide_number": 12,
        "title": "Versal Gen 2 Processing System",
        "type": "intra_slide_variant",
        "advisory": false,
        "tokens": ["A78AE", "A78E"],
        "locations": {"A78AE": ["shape 20 (callout)", "notes"],
                       "A78E": ["shape 14 (diagram)"]},
        "issue": "Slide uses near-identical technical tokens 'A78AE' and "
                 "'A78E' that differ only by an internal letter edit — likely "
                 "a typo or a label/bullet mismatch (Rule 35)."
      }
    ]
"""

import argparse
import difflib
import json
import re
import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from json_helpers import safe_load_json  # noqa: E402

# Technical identifier: starts with a letter, >= 3 chars, alphanumeric.
_TOKEN_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9]{2,}\b")

# Max internal-edit distance for a flagged near-miss pair.
_MAX_EDIT_SIZE = 2

# Common technical-documentation misspellings → correct form. Advisory only.
# Keep this list short and unambiguous to avoid false positives.
_COMMON_TYPOS = {
    "programable": "programmable",
    "programatically": "programmatically",
    "recieve": "receive",
    "recieved": "received",
    "seperate": "separate",
    "seperately": "separately",
    "occured": "occurred",
    "accross": "across",
    "compatability": "compatibility",
    "independant": "independent",
    "asynchronus": "asynchronous",
    "synchronus": "synchronous",
    "througput": "throughput",
    "lenght": "length",
    "widht": "width",
    "adress": "address",
    "paramter": "parameter",
    "paramters": "parameters",
    "configuraton": "configuration",
    "intialize": "initialize",
    "initalize": "initialize",
}


def is_technical(token: str) -> bool:
    """Return True if the token looks like a technical identifier.

    Requires at least one letter and at least one digit so plain English words
    (and pure version numbers, handled elsewhere) are excluded.
    """
    return (
        len(token) >= 3
        and any(c.isalpha() for c in token)
        and any(c.isdigit() for c in token)
    )


def is_internal_letter_near_miss(a: str, b: str) -> bool:
    """Return True if a and b differ only by a small INTERNAL letter edit.

    Pure-digit differences (generation siblings) and prefix/suffix-only
    differences (distinct product families) return False.
    """
    al, bl = a.lower(), b.lower()
    if al == bl:
        return False

    opcodes = difflib.SequenceMatcher(None, al, bl, autojunk=False).get_opcodes()

    # Internal edit ⇒ first and last opcode must be 'equal' (shared prefix and
    # suffix), with at least one non-equal opcode between them.
    if opcodes[0][0] != "equal" or opcodes[-1][0] != "equal":
        return False
    if not any(tag != "equal" for tag, *_ in opcodes):
        return False

    diff_chars: list[str] = []
    edit_size = 0
    for tag, i1, i2, j1, j2 in opcodes:
        if tag == "equal":
            continue
        diff_chars.extend(al[i1:i2])
        diff_chars.extend(bl[j1:j2])
        edit_size += (i2 - i1) + (j2 - j1)

    if edit_size > _MAX_EDIT_SIZE:
        return False
    # Pure-digit differences are legitimate generation siblings → skip.
    if all(c.isdigit() for c in diff_chars):
        return False
    # Must involve at least one letter to be a typo-style near miss.
    return any(c.isalpha() for c in diff_chars)


def _location_label(shape: dict) -> str:
    """Human-readable location for a shape, e.g. 'shape 20 (Title 3)'."""
    sid = shape.get("shape_id")
    name = shape.get("shape_name")
    if sid and name:
        return f"shape {sid} ({name})"
    if sid:
        return f"shape {sid}"
    if name:
        return name
    return "shape"


def _collect_tokens(slide: dict) -> dict[str, list[str]]:
    """Map each distinct technical token (surface form) to its locations."""
    token_locations: dict[str, list[str]] = {}

    def add(token: str, where: str) -> None:
        if not is_technical(token):
            return
        token_locations.setdefault(token, [])
        if where not in token_locations[token]:
            token_locations[token].append(where)

    for shape in slide.get("texts", []) or []:
        where = _location_label(shape)
        for m in _TOKEN_RE.finditer(shape.get("text", "") or ""):
            add(m.group(0), where)

    for m in _TOKEN_RE.finditer(slide.get("notes", "") or ""):
        add(m.group(0), "notes")

    return token_locations


def scan_intra_slide_variants(deck_extract: dict) -> list[dict]:
    """Flag near-miss technical-token variants on each slide."""
    results: list[dict] = []
    for slide in deck_extract.get("slides", []) or []:
        sno = slide.get("slide_number", 0)
        token_locations = _collect_tokens(slide)
        tokens = sorted(token_locations)

        seen_pairs: set[tuple[str, str]] = set()
        for tok_a, tok_b in combinations(tokens, 2):
            key = tuple(sorted((tok_a.lower(), tok_b.lower())))
            if key in seen_pairs:
                continue
            if is_internal_letter_near_miss(tok_a, tok_b):
                seen_pairs.add(key)
                results.append({
                    "slide_number": sno,
                    "title": slide.get("title", ""),
                    "type": "intra_slide_variant",
                    "advisory": False,
                    "tokens": [tok_a, tok_b],
                    "locations": {
                        tok_a: token_locations[tok_a],
                        tok_b: token_locations[tok_b],
                    },
                    "issue": (
                        f"Slide uses near-identical technical tokens "
                        f"'{tok_a}' and '{tok_b}' that differ only by an "
                        f"internal letter edit — likely a typo or a "
                        f"label/bullet mismatch (Rule 35)."
                    ),
                })
    return results


def scan_common_typos(deck_extract: dict) -> list[dict]:
    """Advisory scan for a curated list of common misspellings."""
    results: list[dict] = []
    word_re = re.compile(r"\b[A-Za-z]+\b")
    for slide in deck_extract.get("slides", []) or []:
        sno = slide.get("slide_number", 0)
        found: dict[str, list[str]] = {}

        def check(text: str, where: str) -> None:
            for m in word_re.finditer(text or ""):
                low = m.group(0).lower()
                if low in _COMMON_TYPOS:
                    found.setdefault(m.group(0), [])
                    if where not in found[m.group(0)]:
                        found[m.group(0)].append(where)

        for shape in slide.get("texts", []) or []:
            check(shape.get("text", "") or "", _location_label(shape))
        check(slide.get("notes", "") or "", "notes")

        for surface, locations in found.items():
            correct = _COMMON_TYPOS[surface.lower()]
            results.append({
                "slide_number": sno,
                "title": slide.get("title", ""),
                "type": "advisory_typo",
                "advisory": True,
                "tokens": [surface],
                "suggested": correct,
                "locations": {surface: locations},
                "issue": (
                    f"Possible misspelling '{surface}' (did you mean "
                    f"'{correct}'?) — advisory only (Rule 35)."
                ),
            })
    return results


def scan(deck_extract: dict) -> list[dict]:
    return scan_intra_slide_variants(deck_extract) + scan_common_typos(deck_extract)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--deck-extract", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    deck_extract = safe_load_json(args.deck_extract, "deck_extract.json")
    results = scan(deck_extract)

    Path(args.output).write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    hard = [r for r in results if not r.get("advisory")]
    advisory = [r for r in results if r.get("advisory")]
    print(
        f"consistency_scan: {len(hard)} intra-slide variant signal(s), "
        f"{len(advisory)} advisory typo signal(s)"
    )
    for r in hard:
        print(f"  slide {r['slide_number']}: {r['issue']}")
    for r in advisory:
        print(f"  [advisory] slide {r['slide_number']}: {r['issue']}")


if __name__ == "__main__":
    main()
