"""
Extract content from a .pdf file for source-finding.
Uses pdftotext (bundled with poppler) to extract text per page.
Outputs JSON with per-page text.

Note: pdftotext cannot detect strikethrough formatting — struck-through text will
appear in the output. For draft/review PDFs, treat extracted text with caution.

Usage:
    python extract_pdf.py <path_to_pdf>
"""

import sys
import re
import json
import subprocess
import os

_NOISE_PATTERNS = [
    re.compile(r"OST and Script", re.IGNORECASE),
    re.compile(r"Fully Shared", re.IGNORECASE),
    re.compile(r"^Course Name\s*:", re.IGNORECASE),
    re.compile(r"^Module Name\s*:", re.IGNORECASE),
    re.compile(r"The diagram is already created", re.IGNORECASE),
    re.compile(r"^VO[\s«]", re.IGNORECASE),
    re.compile(r"^local instruction & data memory", re.IGNORECASE),
    re.compile(r"^RPU$", re.IGNORECASE),
    re.compile(r"^\f$"),
    # Headers / footers / boilerplate
    re.compile(r"^(©|copyright|\(c\))\s", re.IGNORECASE),
    re.compile(r"all rights reserved", re.IGNORECASE),
    re.compile(r"^confidential\b", re.IGNORECASE),
    re.compile(r"^internal use only\b", re.IGNORECASE),
    re.compile(r"page\s+\d+\s+of\s+\d+", re.IGNORECASE),
    re.compile(r"^\d+\s*$"),   # Standalone page numbers
]


def is_noise(line):
    return any(p.search(line) for p in _NOISE_PATTERNS)


def extract(pdf_path):
    if not os.path.isfile(pdf_path):
        print(f"Error: File not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    try:
        result = subprocess.run(
            ["pdftotext", "-layout", pdf_path, "-"],
            capture_output=True,
            timeout=60,
        )
    except FileNotFoundError:
        print("Error: pdftotext not found. Ensure poppler is installed.", file=sys.stderr)
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("Error: pdftotext timed out. PDF may be too large or corrupt.", file=sys.stderr)
        sys.exit(1)

    if result.returncode not in (0, 1):
        print(f"pdftotext error: {result.stderr.decode(errors='replace')}", file=sys.stderr)
        sys.exit(1)

    raw = result.stdout.decode("utf-8", errors="replace")
    raw_pages = raw.split("\f")

    # Flag if filename suggests a draft (may contain undetectable strikethrough)
    may_have_strikethrough = bool(re.search(r"draft|review|wip", os.path.basename(pdf_path), re.IGNORECASE))

    pages = []
    for i, page_text in enumerate(raw_pages, start=1):
        lines = page_text.splitlines()
        clean_lines = [l.strip() for l in lines if l.strip() and not is_noise(l.strip())]

        # Always include every page so numbering stays correct; blank pages get is_blank=True
        pages.append({
            "page": i,
            "text": clean_lines,
            "has_images": False,
            "is_blank": len(clean_lines) == 0,
            "may_have_strikethrough": may_have_strikethrough,
        })

    # Drop trailing empty pages caused by a trailing \f in pdftotext output
    while pages and pages[-1]["is_blank"]:
        pages.pop()

    return pages


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_pdf.py <path_to_pdf>", file=sys.stderr)
        sys.exit(1)

    data = extract(sys.argv[1])
    sys.stdout.buffer.write(json.dumps(data, indent=2, ensure_ascii=True).encode("utf-8"))
    sys.stdout.buffer.write(b"\n")
