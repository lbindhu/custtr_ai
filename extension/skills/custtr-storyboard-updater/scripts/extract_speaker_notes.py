#!/usr/bin/env python3
"""Dump verbatim speaker notes from every slide of a .pptx to a JSON file.

The output is keyed by slide_number (1-based) and is intended to provide
verbatim source text for `notes_changes[].match_fragment` in update_plan.json.

Use exact fragments from this file when authoring any existing-slide notes
update. Existing-slide notes must use `notes_changes`, not wholesale
`speaker_notes` replacement.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

# Match every <a:t ...>text</a:t> run, preserving newlines as the OOXML
# notes XML expresses them via separate paragraphs / line breaks.
_RUN_RE = re.compile(r"<a:t[^>]*>([^<]*)</a:t>")
_BR_RE = re.compile(r"<a:br\b[^/]*/>")
_P_END_RE = re.compile(r"</a:p>")


def _xml_to_text(xml: str) -> str:
    """Best-effort flatten of notesSlideN.xml to plain text.

    Preserves paragraph breaks (one <a:p> per line) and explicit <a:br/> as
    newlines. Multiple consecutive whitespaces are collapsed inside a line
    but line boundaries are kept.
    """
    # Substitute <a:br/> with a literal newline marker
    xml = _BR_RE.sub("\u0001", xml)
    # Mark paragraph boundaries
    xml = _P_END_RE.sub("\u0002", xml)
    runs = _RUN_RE.findall(xml)
    text = "".join(runs)
    # restore markers
    text = text.replace("\u0001", "\n")
    # paragraph marker already implicit because runs are concatenated; we
    # only want a single break between paragraphs
    return text.strip("\n")


def extract_notes(deck_path: Path) -> dict[int, str]:
    """Return {slide_number: verbatim_notes_text} for every slide that has notes."""
    result: dict[int, str] = {}
    with zipfile.ZipFile(deck_path, "r") as z:
        names = z.namelist()
        for name in names:
            m = re.match(r"ppt/notesSlides/notesSlide(\d+)\.xml$", name)
            if not m:
                continue
            slide_no = int(m.group(1))
            xml = z.read(name).decode("utf-8", errors="ignore")
            text = _xml_to_text(xml)
            result[slide_no] = text
    return result


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--deck", required=True, help="Path to source .pptx")
    p.add_argument("--output", required=True, help="Path to write original_notes.json")
    args = p.parse_args(argv)

    deck = Path(args.deck)
    if not deck.is_file():
        print(f"ERROR: deck not found: {deck}", file=sys.stderr)
        return 2

    notes = extract_notes(deck)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    # Keys sorted numerically but stored as strings for JSON compatibility
    serialized = {str(k): notes[k] for k in sorted(notes)}
    out.write_text(json.dumps(serialized, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {len(serialized)} slide notes -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
