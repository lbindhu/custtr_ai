"""
Single entry-point extractor for source-finding.
Auto-detects file type and dispatches to the right extractor.

Usage:
    python extract.py <path_to_file>

Supported formats:
    .pptx  — PowerPoint (per slide)
    .docx  — Word       (per heading section)
    .pdf   — PDF        (per page)

Output: JSON array printed to stdout.
Each element has a common "type" field plus format-specific fields:
  - PPTX: { type, slide, title, text, images, searchable }
  - DOCX: { type, section, heading, level, text, has_images, searchable }
  - PDF:  { type, page, text, has_images, searchable }

The "searchable" field is False when a slide/section/page has no usable
text content (e.g. image-only or blank) — the skill uses this to skip
search and mark the row as "Image-only" instead of "No source found".
"""

import sys
import os
import re
import json

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))

# Titles that indicate non-content items (training scaffolding, not sourced material).
_NON_CONTENT_TITLES = re.compile(
    r"^("
    r"objectives?|summary|disclaimer|attribution|apply your knowledge"
    r"|quiz|knowledge check|review questions?|agenda|table of contents"
    r"|introduction$|about this (course|module)|what you('ll| will) learn"
    r"|learning objectives?|module overview|course overview"
    r"|lab\s+\d+|exercise\s+\d+|part\s+\d+|chapter\s+\d+|unit\s+\d+"
    r"|q\s*&\s*a|faq|pre-?test|post-?test|hands-?on|.*\(continued\)"
    r"|congratulations|thank\s+you|questions\?"
    r")\s*$",
    re.IGNORECASE,
)


def is_non_content(title):
    return bool(_NON_CONTENT_TITLES.match(title.strip())) if title else False


def annotate(items, item_type):
    for item in items:
        item["type"] = item_type
        title = item.get("title") or item.get("heading") or ""
        meaningful = [t for t in item["text"] if len(t.split()) > 2]
        has_img = bool(item.get("images")) or item.get("has_images", False)
        is_blank = item.get("is_blank", False)

        if is_non_content(title):
            item["searchable"] = False
            item["skip_reason"] = "non-content slide"
        elif is_blank or (not meaningful and not has_img):
            item["searchable"] = False
            item["skip_reason"] = "image-only or blank"
        else:
            item["searchable"] = True
            item["skip_reason"] = None
    return items


def dispatch(file_path):
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pptx":
        sys.path.insert(0, SCRIPTS_DIR)
        from extract_slides import extract
        return annotate(extract(file_path), "slide")

    elif ext == ".docx":
        sys.path.insert(0, SCRIPTS_DIR)
        from extract_docx import extract
        return annotate(extract(file_path), "section")

    elif ext == ".pdf":
        sys.path.insert(0, SCRIPTS_DIR)
        from extract_pdf import extract
        return annotate(extract(file_path), "page")

    else:
        print(f"Unsupported file type: '{ext}'. Supported: .pptx, .docx, .pdf", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract.py <path_to_file>", file=sys.stderr)
        sys.exit(1)

    data = dispatch(sys.argv[1])
    sys.stdout.buffer.write(json.dumps(data, indent=2, ensure_ascii=True).encode("utf-8"))
    sys.stdout.buffer.write(b"\n")
