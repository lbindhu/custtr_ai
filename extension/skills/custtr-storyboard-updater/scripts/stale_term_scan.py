#!/usr/bin/env python3
"""Axis-B stale-term scan.

Scans every shape and speaker-notes block in deck_extract.json for stale
tokens defined in stale_terms.json, honoring skip_if_* guards and
intentionally_kept exceptions.

Writes:
  --output-json  structured findings per slide
  --output-md    human-readable summary

Exit code 2 when --enforce is set and any hit survives.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stale_terms import iter_findings, is_intentionally_kept, load_stale_terms
from json_helpers import safe_load_json  # noqa: E402


def scan_deck(deck_extract, stale_terms_doc):
    results = []
    for slide in deck_extract.get("slides", []):
        sno = slide.get("slide_number", 0)
        slide_hits = []

        for text_item in slide.get("texts", []):
            text = text_item.get("text", "")
            if not text:
                continue
            for entry, pos in iter_findings(text, stale_terms_doc):
                token = entry["token"]
                if is_intentionally_kept(token, sno, stale_terms_doc):
                    continue
                slide_hits.append({
                    "token": token,
                    "location": "OST",
                    "shape_id": text_item.get("shape_id"),
                    "shape_name": text_item.get("shape_name"),
                    "shape_text_preview": text[:120],
                    "position": pos,
                    "replace_with": entry.get("replace_with", ""),
                    "source_ids": entry.get("source_ids", []),
                })

        notes = slide.get("notes", "")
        if notes:
            for entry, pos in iter_findings(notes, stale_terms_doc):
                token = entry["token"]
                if is_intentionally_kept(token, sno, stale_terms_doc):
                    continue
                slide_hits.append({
                    "token": token,
                    "location": "notes",
                    "shape_id": None,
                    "shape_name": "speaker_notes",
                    "shape_text_preview": notes[max(0, pos - 40):pos + 60],
                    "position": pos,
                    "replace_with": entry.get("replace_with", ""),
                    "source_ids": entry.get("source_ids", []),
                })

        results.append({
            "slide_number": sno,
            "title": slide.get("title", ""),
            "hits": slide_hits,
        })

    return results


def render_md(results):
    lines = ["# Stale-Term Scan Report\n"]
    total = sum(len(r["hits"]) for r in results)
    lines.append(f"**Total hits:** {total}\n")
    for r in results:
        if not r["hits"]:
            continue
        lines.append(f"\n## Slide {r['slide_number']}: {r['title']}\n")
        for h in r["hits"]:
            loc = h["location"]
            lines.append(
                f"- **{h['token']}** ({loc}) → {h['replace_with'] or '(no replacement suggested)'}"
            )
    if total == 0:
        lines.append("\nNo stale-term hits found.\n")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deck-extract", required=True)
    ap.add_argument("--stale-terms", required=True)
    ap.add_argument("--output-json", required=True)
    ap.add_argument("--output-md", required=True)
    ap.add_argument("--enforce", action="store_true",
                    help="Exit 2 on any surviving hit.")
    args = ap.parse_args()

    deck_extract = safe_load_json(args.deck_extract, "deck_extract.json")
    stale_terms_doc = load_stale_terms(Path(args.stale_terms))

    results = scan_deck(deck_extract, stale_terms_doc)

    Path(args.output_json).write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    Path(args.output_md).write_text(render_md(results), encoding="utf-8")

    total = sum(len(r["hits"]) for r in results)
    print(f"stale_term_scan: {total} hit(s) across {sum(1 for r in results if r['hits'])} slide(s)")

    if args.enforce and total > 0:
        sys.exit(2)


if __name__ == "__main__":
    main()
