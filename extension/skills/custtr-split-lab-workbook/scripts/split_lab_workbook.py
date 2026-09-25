"""Split an AMD lab workbook DOCX into separate files by lab number.

Preserves formatting by copying the full DOCX and trimming word/document.xml only.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
import zipfile
from copy import deepcopy
from pathlib import Path

from lxml import etree

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NSMAP = {"w": W_NS}
LAB_HEADING_RE = re.compile(r"Lab\s*(\d+)\s*:", re.IGNORECASE)
LAB_SEQ_HEADING_RE = re.compile(r"\\n\s*(\d+)\s*:")


def paragraph_text(p: etree._Element) -> str:
    return "".join(p.itertext())


def paragraph_style(p: etree._Element) -> str | None:
    p_pr = p.find("w:pPr", NSMAP)
    if p_pr is None:
        return None
    p_style = p_pr.find("w:pStyle", NSMAP)
    if p_style is None:
        return None
    return p_style.get(f"{{{W_NS}}}val")


def find_lab_splits(body: etree._Element) -> list[tuple[int, int, str]]:
    splits: list[tuple[int, int, str]] = []
    for idx, child in enumerate(body):
        if child.tag != f"{{{W_NS}}}p":
            continue
        if paragraph_style(child) != "Heading1":
            continue
        text = paragraph_text(child).strip()
        match = LAB_HEADING_RE.search(text) or LAB_SEQ_HEADING_RE.search(text)
        if not match:
            continue
        splits.append((int(match.group(1)), idx, text))
    return splits


def extract_lab_title(text: str) -> str:
    match = re.search(r"\\n\s*\d+\s*:\s*(.+)$", text)
    if match:
        title = match.group(1)
    else:
        title = LAB_HEADING_RE.sub("", text)
    title = re.sub(r'QUOTE\s+"Lab"\s*', "", title, flags=re.IGNORECASE)
    title = re.sub(r"PAGEREF.*$", "", title, flags=re.IGNORECASE).strip()
    title = re.sub(r"\s+", " ", title).strip(" :-")
    return title


def sanitize_filename(text: str, max_len: int = 120) -> str:
    cleaned = extract_lab_title(text)
    cleaned = re.sub(r'[<>:"/\\|?*]', "-", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) > max_len:
        cleaned = cleaned[: max_len - 3].rstrip() + "..."
    return cleaned if cleaned else "Lab"


def clean_first_lab_heading(body: etree._Element) -> None:
    """Replace 'Lab N: Title' field-code heading with plain title text."""
    for child in body:
        if child.tag != f"{{{W_NS}}}p":
            continue
        if paragraph_style(child) != "Heading1":
            continue

        title = extract_lab_title(paragraph_text(child))
        preserved: list[etree._Element] = []
        for node in list(child):
            tag = node.tag.split("}")[-1]
            if tag in {"pPr", "bookmarkStart", "bookmarkEnd"}:
                preserved.append(deepcopy(node))
            child.remove(node)

        for node in preserved:
            child.append(node)

        run = etree.SubElement(child, f"{{{W_NS}}}r")
        text_node = etree.SubElement(run, f"{{{W_NS}}}t")
        text_node.text = title
        return


def trim_document_xml(document_xml: bytes, start_idx: int, end_idx: int) -> bytes:
    root = etree.fromstring(document_xml)
    body = root.find("w:body", NSMAP)
    if body is None:
        raise ValueError("document.xml has no w:body element")

    children = list(body)
    sect_pr = next((c for c in children if c.tag == f"{{{W_NS}}}sectPr"), None)
    kept_nodes = [deepcopy(c) for i, c in enumerate(children) if start_idx <= i < end_idx]

    for child in list(body):
        body.remove(child)

    for node in kept_nodes:
        body.append(node)

    if sect_pr is not None:
        body.append(deepcopy(sect_pr))

    clean_first_lab_heading(body)

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def resolve_source(source: Path) -> Path:
    if not source.exists():
        raise FileNotFoundError(source)

    temp_source = Path.home() / "AppData/Local/Temp/lab-workbook-split-source.docx"
    try:
        shutil.copy2(source, temp_source)
        return temp_source
    except OSError:
        return source


def inspect_workbook(source: Path) -> list[tuple[int, str, str]]:
    """Return planned outputs as (lab_num, title, filename) without writing files."""
    work_source = resolve_source(source)
    with zipfile.ZipFile(work_source, "r") as zin:
        document_xml = zin.read("word/document.xml")

    root = etree.fromstring(document_xml)
    body = root.find("w:body", NSMAP)
    if body is None:
        raise ValueError("document.xml has no w:body element")

    splits = find_lab_splits(body)
    if not splits:
        raise ValueError("No Lab headings (Heading1) found in document")

    planned: list[tuple[int, str, str]] = []
    for lab_num, _start_idx, raw_title in splits:
        title = extract_lab_title(raw_title)
        filename = f"{lab_num:02d} {sanitize_filename(raw_title)}.docx"
        planned.append((lab_num, title, filename))
    return planned


def print_workbook_inspection(source: Path, output_dir: Path | None = None) -> list[tuple[int, str, str]]:
    planned = inspect_workbook(source)
    out = output_dir or source.parent
    print(f"Source: {source}")
    print(f"Output folder: {out}")
    print(f"Labs found: {len(planned)}")
    for lab_num, title, filename in planned:
        print(f"  {lab_num:02d}  {title}")
        print(f"       -> {filename}")
    return planned


def split_workbook(source: Path, output_dir: Path | None = None) -> list[Path]:
    work_source = resolve_source(source)
    output_dir = output_dir or source.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(work_source, "r") as zin:
        document_xml = zin.read("word/document.xml")
        archive_files = {name: zin.read(name) for name in zin.namelist()}

    root = etree.fromstring(document_xml)
    body = root.find("w:body", NSMAP)
    if body is None:
        raise ValueError("document.xml has no w:body element")

    children = list(body)
    splits = find_lab_splits(body)
    if not splits:
        raise ValueError("No Lab headings (Heading1) found in document")

    last_content_idx = len(children) - 1
    if children[-1].tag == f"{{{W_NS}}}sectPr":
        last_content_idx = len(children) - 2

    ranges: list[tuple[int, int, int, str]] = []
    for i, (lab_num, start_idx, title) in enumerate(splits):
        range_end = splits[i + 1][1] if i + 1 < len(splits) else last_content_idx + 1
        ranges.append((lab_num, start_idx, range_end, title))

    created: list[Path] = []

    for lab_num, start_idx, end_idx, title in ranges:
        trimmed_xml = trim_document_xml(document_xml, start_idx, end_idx)
        lab_title = sanitize_filename(title)
        out_name = f"{lab_num:02d} {lab_title}.docx"
        out_path = output_dir / out_name

        if out_path.exists():
            out_path.unlink()

        temp_path = output_dir / f".tmp-{lab_num:02d}.docx"
        shutil.copy2(work_source, temp_path)

        with zipfile.ZipFile(temp_path, "r") as zin:
            names = zin.namelist()

        with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for name in names:
                data = trimmed_xml if name == "word/document.xml" else archive_files[name]
                zout.writestr(name, data)

        temp_path.replace(out_path)
        created.append(out_path)
        print(f"Created: {out_path.name}")

    return created


def main() -> int:
    parser = argparse.ArgumentParser(description="Split an AMD lab workbook DOCX by lab number.")
    parser.add_argument("source", type=Path, help="Combined lab workbook .docx")
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=None,
        help="Output folder (default: same folder as source)",
    )
    parser.add_argument(
        "--inspect",
        action="store_true",
        help="List labs that would be split; do not write files",
    )
    args = parser.parse_args()

    try:
        if args.inspect:
            print_workbook_inspection(args.source, args.output_dir)
            return 0
        outputs = split_workbook(args.source, args.output_dir)
    except (FileNotFoundError, ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"\nDone. {len(outputs)} files written to:\n{outputs[0].parent}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
