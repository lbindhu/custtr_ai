"""Export combined AMD lab workbook DOCX to PDF with metadata, bookmarks, and blank pages."""
from __future__ import annotations

import argparse
import io
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

from lxml import etree
from pypdf import PageObject, PdfReader, PdfWriter

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
CP_NS = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
NSMAP = {"w": W_NS}
LAB_HEADING_RE = re.compile(r"Lab\s*(\d+)\s*:\s*(.+)", re.IGNORECASE | re.DOTALL)
LAB_SEQ_HEADING_RE = re.compile(r"\\n\s*(\d+)\s*:\s*(.+)", re.DOTALL)
PART_NUMBER_RE = re.compile(
    r"(?:^|[\w-]+-)(?P<version>\d{4}\.\d+)-wkb-lab",
    re.IGNORECASE,
)
PDF_AUTHOR = "AMD, Inc."


def paragraph_text(p: etree._Element) -> str:
    return re.sub(r"\s+", " ", "".join(p.itertext())).strip()


def paragraph_style(p: etree._Element) -> str | None:
    p_pr = p.find("w:pPr", NSMAP)
    if p_pr is None:
        return None
    p_style = p_pr.find("w:pStyle", NSMAP)
    if p_style is None:
        return None
    return p_style.get(f"{{{W_NS}}}val")


def clean_lab_heading(text: str) -> tuple[int, str]:
    match = LAB_HEADING_RE.search(text) or LAB_SEQ_HEADING_RE.search(text)
    if not match:
        raise ValueError(f"Not a lab heading: {text!r}")
    lab_num = int(match.group(1))
    title = match.group(2)
    title = re.sub(r'QUOTE\s+"Lab"\s*', "", title, flags=re.IGNORECASE)
    title = re.sub(r"PAGEREF.*$", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\s+", " ", title).strip(" :-")
    return lab_num, title


def read_core_metadata(docx_path: Path) -> dict[str, str | None]:
    with zipfile.ZipFile(docx_path) as zin:
        if "docProps/core.xml" not in zin.namelist():
            return {"title": None, "subject": None, "creator": None}
        root = etree.fromstring(zin.read("docProps/core.xml"))
    return {
        "title": (root.find(f"{{{CP_NS}}}title").text if root.find(f"{{{CP_NS}}}title") is not None else None),
        "subject": (root.find(f"{{{CP_NS}}}subject").text if root.find(f"{{{CP_NS}}}subject") is not None else None),
        "creator": (root.find(f"{{{CP_NS}}}creator").text if root.find(f"{{{CP_NS}}}creator") is not None else None),
    }


def read_cover_info(docx_path: Path) -> tuple[str, str, str]:
    with zipfile.ZipFile(docx_path) as zin:
        doc = etree.fromstring(zin.read("word/document.xml"))

    cover_title = ""
    cover_subtitle = ""
    part_number = ""
    seen_training = False

    for p in doc.iter(f"{{{W_NS}}}p"):
        style = paragraph_style(p)
        text = paragraph_text(p)
        if not text and style not in {"CoverTitle", "CoverTitle2", "CoverPartNumber"}:
            continue
        if "AMD ADAPTIVE COMPUTING CUSTOMER TRAINING" in text.upper():
            seen_training = True
            continue
        if seen_training or style in {"CoverTitle", "CoverTitle2", "CoverPartNumber"}:
            if style == "CoverTitle" or (seen_training and not cover_title and style is None):
                if "Lab Workbook" not in text and "DISCLAIMER" not in text:
                    cover_title = text
            elif style == "CoverTitle2" or text == "Lab Workbook":
                cover_subtitle = "Lab Workbook"
            elif style == "CoverPartNumber" or PART_NUMBER_RE.search(text):
                part_number = text
        if cover_title and cover_subtitle and part_number:
            break

    if not cover_title:
        for p in doc.iter(f"{{{W_NS}}}p"):
            style = paragraph_style(p)
            text = paragraph_text(p)
            if style == "CoverTitle":
                cover_title = text
            elif style == "CoverTitle2":
                cover_subtitle = text or "Lab Workbook"
            elif style == "CoverPartNumber":
                part_number = text
            if cover_title and cover_subtitle and part_number:
                break

    if not cover_subtitle:
        cover_subtitle = "Lab Workbook"

    return cover_title, cover_subtitle, part_number


def version_from_part_number(part_number: str, docx_path: Path) -> str:
    for source in (part_number, docx_path.stem):
        match = PART_NUMBER_RE.search(source)
        if match:
            return match.group("version")
    raise ValueError(f"Could not determine version from {part_number!r} or {docx_path.name!r}")


def build_document_title(docx_path: Path) -> str:
    core = read_core_metadata(docx_path)
    cover_title, cover_subtitle, part_number = read_cover_info(docx_path)
    version = version_from_part_number(part_number, docx_path)

    meta_title = (core.get("title") or "").strip()
    cover_full = f"{cover_title} {cover_subtitle}".strip()

    if meta_title and meta_title.lower() == cover_full.lower():
        title_base = cover_full
    elif meta_title and "lab workbook" in meta_title.lower():
        if cover_title.lower() not in meta_title.lower():
            title_base = cover_full
        else:
            title_base = meta_title.removesuffix(version).strip()
            if not title_base.lower().endswith("lab workbook"):
                title_base = cover_full
    else:
        title_base = cover_full

    return f"{title_base} {version}".strip()


def find_lab_headings(docx_path: Path) -> list[tuple[int, str, str]]:
    with zipfile.ZipFile(docx_path) as zin:
        doc = etree.fromstring(zin.read("word/document.xml"))
    body = doc.find("w:body", NSMAP)
    if body is None:
        raise ValueError("document.xml has no body")

    labs: list[tuple[int, str, str]] = []
    for child in body:
        if child.tag != f"{{{W_NS}}}p":
            continue
        if paragraph_style(child) != "Heading1":
            continue
        text = paragraph_text(child)
        if not (LAB_HEADING_RE.search(text) or LAB_SEQ_HEADING_RE.search(text)):
            continue
        lab_num, title = clean_lab_heading(text)
        bookmark = f"Lab {lab_num}: {title}"
        labs.append((lab_num, title, bookmark))
    return labs


def normalize_text(text: str) -> str:
    text = text or ""
    text = text.replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def find_lab_start_pages(pdf_path: Path, labs: list[tuple[int, str, str]]) -> dict[int, int]:
    reader = PdfReader(str(pdf_path))
    starts: dict[int, int] = {}

    for lab_num, title, bookmark in labs:
        title_norm = normalize_text(title)
        title_words = [w for w in re.split(r"[^\w]+", title_norm) if len(w) > 3][:4]
        best_page: int | None = None

        for page_idx, page in enumerate(reader.pages):
            text = normalize_text(page.extract_text() or "")
            if f"lab {lab_num}:" not in text:
                continue
            if "table of contents" in text:
                continue
            if "abstract" not in text:
                continue
            if title_words and not any(word in text for word in title_words):
                continue
            best_page = page_idx
            break

        if best_page is None:
            for page_idx, page in enumerate(reader.pages):
                text = normalize_text(page.extract_text() or "")
                if f"lab {lab_num}:" in text and "table of contents" not in text:
                    best_page = page_idx
                    break

        if best_page is None:
            raise ValueError(f"Could not locate start page for {bookmark!r}")

        starts[lab_num] = best_page

    return starts


def page_is_blank(page) -> bool:
    return len((page.extract_text() or "").strip()) == 0


def find_back_cover_index(reader: PdfReader) -> int | None:
    if not reader.pages:
        return None
    last_idx = len(reader.pages) - 1
    page = reader.pages[last_idx]
    if page_is_blank(page) and len(page.images) > 0:
        return last_idx
    return None


def find_last_content_index(reader: PdfReader, back_cover_idx: int | None) -> int:
    search_end = back_cover_idx if back_cover_idx is not None else len(reader.pages)
    idx = search_end - 1
    while idx >= 0 and page_is_blank(reader.pages[idx]):
        idx -= 1
    if idx < 0:
        raise ValueError("Could not find last content page in PDF")
    return idx


def extract_printed_page_number(page) -> int | None:
    text = page.extract_text() or ""
    matches = re.findall(r"www\.amd\.com\s*(\d+)", text, re.IGNORECASE)
    if matches:
        return int(matches[-1])
    matches = re.findall(r"(\d+)\s*www\.amd\.com", text, re.IGNORECASE)
    if matches:
        return int(matches[-1])
    return None


def create_blank_page(template_page) -> PageObject:
    return PageObject.create_blank_page(
        width=float(template_page.mediabox.width),
        height=float(template_page.mediabox.height),
    )


def ensure_blank_pages_before_back_cover(reader: PdfReader) -> tuple[list, dict[str, int | bool]]:
    back_cover_idx = find_back_cover_index(reader)
    last_content_idx = find_last_content_index(reader, back_cover_idx)
    printed_page = extract_printed_page_number(reader.pages[last_content_idx])

    info: dict[str, int | bool] = {
        "last_content_pdf_page": last_content_idx + 1,
        "printed_page_number": printed_page or 0,
        "back_cover_pdf_page": (back_cover_idx + 1) if back_cover_idx is not None else 0,
        "blank_pages_inserted": 0,
        "needs_blank_pages": False,
    }

    if printed_page is None:
        raise ValueError(
            f"Could not read printed page number from PDF page {last_content_idx + 1}"
        )

    if back_cover_idx is None:
        return list(reader.pages), info

    trailing_blank_count = back_cover_idx - last_content_idx - 1
    if printed_page % 2 == 1:
        info["needs_blank_pages"] = True
        blanks_to_insert = max(0, 2 - trailing_blank_count)
        info["blank_pages_inserted"] = blanks_to_insert
    else:
        blanks_to_insert = 0

    pages = list(reader.pages)
    if blanks_to_insert:
        template = pages[0]
        blank_pages = [create_blank_page(template) for _ in range(blanks_to_insert)]
        pages = pages[: back_cover_idx] + blank_pages + pages[back_cover_idx:]

    return pages, info


def export_docx_to_pdf(docx_path: Path, pdf_path: Path) -> None:
    ps_script = f"""
$ErrorActionPreference = 'Stop'
$word = New-Object -ComObject Word.Application
$word.Visible = $false
try {{
    if (Test-Path -LiteralPath '{pdf_path}') {{
        Remove-Item -LiteralPath '{pdf_path}' -Force
    }}
    $doc = $word.Documents.Open('{docx_path}', $false, $true)
    $doc.ExportAsFixedFormat('{pdf_path}', 17)
    $doc.Close($false)
}}
finally {{
    $word.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
}}
"""
    subprocess.run(
        ["powershell.exe", "-ExecutionPolicy", "Bypass", "-NoProfile", "-Command", ps_script],
        check=True,
        capture_output=True,
        text=True,
    )
    if not pdf_path.exists():
        raise RuntimeError(f"PDF export failed: {pdf_path}")


def postprocess_pdf(
    pdf_path: Path,
    *,
    title: str,
    labs: list[tuple[int, str, str]],
    lab_pages: dict[int, int],
) -> dict[str, int | bool]:
    with pdf_path.open("rb") as fh:
        pdf_bytes = fh.read()

    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages, blank_info = ensure_blank_pages_before_back_cover(reader)
    writer = PdfWriter()
    for page in pages:
        writer.add_page(page)

    writer.add_metadata(
        {
            "/Title": title,
            "/Author": PDF_AUTHOR,
            "/Subject": title,
        }
    )
    writer.page_mode = "/UseOutlines"

    for lab_num, _title, bookmark in labs:
        writer.add_outline_item(bookmark, lab_pages[lab_num])

    temp = pdf_path.with_suffix(".tmp.pdf")
    with temp.open("wb") as fh:
        writer.write(fh)
    shutil.move(temp, pdf_path)
    return blank_info


def process_workbook(docx_path: Path, pdf_path: Path | None = None) -> dict[str, object]:
    docx_path = docx_path.resolve()
    pdf_path = (pdf_path or docx_path.with_suffix(".pdf")).resolve()

    title = build_document_title(docx_path)
    labs = find_lab_headings(docx_path)
    export_docx_to_pdf(docx_path, pdf_path)
    lab_pages = find_lab_start_pages(pdf_path, labs)
    blank_info = postprocess_pdf(pdf_path, title=title, labs=labs, lab_pages=lab_pages)

    reader = PdfReader(str(pdf_path))
    return {
        "docx": str(docx_path),
        "pdf": str(pdf_path),
        "title": title,
        "pages": len(reader.pages),
        "page_mode": reader.root_object.get("/PageMode"),
        "bookmarks": [(bookmark, lab_pages[lab_num] + 1) for lab_num, _, bookmark in labs],
        "blank_pages": blank_info,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("docx", type=Path, help="Combined lab workbook .docx")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output PDF path (default: same name as DOCX in same folder)",
    )
    args = parser.parse_args()

    if not args.docx.is_file():
        print(f"Error: file not found: {args.docx}", file=sys.stderr)
        return 1

    result = process_workbook(args.docx, args.output)
    print(f"Created: {result['pdf']}")
    print(f"Title: {result['title']}")
    print(f"Pages: {result['pages']}")
    print(f"PageMode: {result['page_mode']}")
    blank = result["blank_pages"]
    print(
        "Blank pages: "
        f"last content PDF page {blank['last_content_pdf_page']} "
        f"(printed page {blank['printed_page_number']}), "
        f"inserted {blank['blank_pages_inserted']}"
    )
    for bookmark, page in result["bookmarks"]:
        print(f"  {bookmark} -> page {page}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
