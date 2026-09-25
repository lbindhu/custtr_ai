"""Post-process split AMD lab workbook outputs.

1. Remove AMD embedded images from final-section header/footer parts (DOCX)
2. Trim trailing blank PDF pages (up to 3)
3. Set PDF document metadata (Title, Author, Subject)
"""
from __future__ import annotations

import argparse
import re
import sys
import zipfile
from copy import deepcopy
from pathlib import Path

from lxml import etree
from pypdf import PdfReader, PdfWriter

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
V_NS = "urn:schemas-microsoft-com:vml"
NSMAP = {"w": W_NS, "r": R_NS, "a": A_NS, "v": V_NS}
IMAGE_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"
LAB_FILENAME_RE = re.compile(r"^\d{2}\s+(.+)\.(docx|pdf)$", re.IGNORECASE)
PDF_AUTHOR = "AMD, Inc."


def lab_title_from_filename(path: Path) -> str:
    match = LAB_FILENAME_RE.match(path.name)
    if match:
        return match.group(1).strip()
    return path.stem


def get_final_hf_parts(files: dict[str, bytes]) -> list[str]:
    root = etree.fromstring(files["word/document.xml"])
    body = root.find("w:body", NSMAP)
    if body is None:
        raise ValueError("document.xml has no body")

    sect_pr = body.find("w:sectPr", NSMAP)
    if sect_pr is None:
        for child in body.findall("w:p", NSMAP):
            p_pr = child.find("w:pPr", NSMAP)
            if p_pr is not None:
                inline = p_pr.find("w:sectPr", NSMAP)
                if inline is not None:
                    sect_pr = inline

    if sect_pr is None:
        raise ValueError("No sectPr found in document.xml")

    rel_root = etree.fromstring(files["word/_rels/document.xml.rels"])
    rel_map = {rel.get("Id"): rel.get("Target") for rel in rel_root}
    parts: list[str] = []
    for ref in sect_pr.findall("w:headerReference", NSMAP) + sect_pr.findall(
        "w:footerReference", NSMAP
    ):
        rid = ref.get(f"{{{R_NS}}}id")
        target = rel_map.get(rid or "")
        if target:
            parts.append(f"word/{target}")
    return parts


def run_has_embedded_image(run: etree._Element) -> bool:
    if run.find(".//a:blip", NSMAP) is not None:
        return True
    if run.find(".//v:imagedata", NSMAP) is not None:
        return True
    return False


def remove_image_runs_from_hf_xml(xml_bytes: bytes) -> tuple[bytes, int]:
    root = etree.fromstring(xml_bytes)
    removed = 0
    for paragraph in root.findall(".//w:p", NSMAP):
        for run in list(paragraph.findall("w:r", NSMAP)):
            if run_has_embedded_image(run):
                paragraph.remove(run)
                removed += 1
    return (
        etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True),
        removed,
    )


def cleanup_hf_image_rels(rels_bytes: bytes) -> bytes:
    root = etree.fromstring(rels_bytes)
    kept = [deepcopy(rel) for rel in root if rel.get("Type") != IMAGE_REL_TYPE]
    for rel in list(root):
        root.remove(rel)
    for rel in kept:
        root.append(rel)
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def remove_last_page_header_images(docx_path: Path) -> int:
    """Remove embedded images from final-section header/footer parts."""
    with zipfile.ZipFile(docx_path, "r") as zin:
        names = zin.namelist()
        files = {name: zin.read(name) for name in names}

    hf_parts = get_final_hf_parts(files)
    total_removed = 0

    for part in hf_parts:
        if part not in files:
            continue
        updated, removed = remove_image_runs_from_hf_xml(files[part])
        if removed:
            files[part] = updated
            total_removed += removed
            rels_part = part.replace("word/", "word/_rels/") + ".rels"
            if rels_part in files:
                files[rels_part] = cleanup_hf_image_rels(files[rels_part])

    if total_removed == 0:
        return 0

    temp = docx_path.with_suffix(".tmp.docx")
    with zipfile.ZipFile(temp, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        for name in names:
            if name in files:
                zout.writestr(name, files[name])
    temp.replace(docx_path)
    return total_removed


def page_is_blank(page) -> bool:
    return len((page.extract_text() or "").strip()) == 0


def trim_trailing_blank_pdf_pages(pdf_path: Path, max_trim: int = 3) -> int:
    reader = PdfReader(str(pdf_path))
    blank_count = 0
    for page in reversed(reader.pages):
        if blank_count >= max_trim:
            break
        if page_is_blank(page):
            blank_count += 1
        else:
            break

    if blank_count == 0:
        return 0

    writer = PdfWriter()
    for page in reader.pages[: len(reader.pages) - blank_count]:
        writer.add_page(page)

    temp = pdf_path.with_suffix(".tmp.pdf")
    with temp.open("wb") as fh:
        writer.write(fh)
    temp.replace(pdf_path)
    return blank_count


def set_pdf_metadata(pdf_path: Path, lab_title: str | None = None) -> None:
    title = lab_title or lab_title_from_filename(pdf_path)
    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)

    writer.add_metadata(
        {
            "/Title": title,
            "/Author": PDF_AUTHOR,
            "/Subject": title,
        }
    )

    temp = pdf_path.with_suffix(".tmp.pdf")
    with temp.open("wb") as fh:
        writer.write(fh)
    temp.replace(pdf_path)


def process_docx(docx_path: Path) -> int:
    return remove_last_page_header_images(docx_path)


def process_pdf(pdf_path: Path) -> tuple[int, int]:
    trimmed = trim_trailing_blank_pdf_pages(pdf_path)
    set_pdf_metadata(pdf_path)
    reader = PdfReader(str(pdf_path))
    return trimmed, len(reader.pages)


def iter_lab_docx(folder: Path) -> list[Path]:
    return sorted(folder.glob("[0-9][0-9] *.docx"))


def iter_lab_pdf(folder: Path) -> list[Path]:
    return sorted(folder.glob("[0-9][0-9] *.pdf"))


def postprocess_folder(
    folder: Path,
    *,
    docx: bool = True,
    pdf: bool = True,
) -> dict[str, list[str]]:
    """Run post-processing on all split lab files in a folder."""
    log: dict[str, list[str]] = {"docx": [], "pdf": []}

    if docx:
        for path in iter_lab_docx(folder):
            removed = process_docx(path)
            log["docx"].append(f"{path.name}: removed {removed} last-page header/footer image(s)")

    if pdf:
        for path in iter_lab_pdf(folder):
            trimmed, pages = process_pdf(path)
            title = lab_title_from_filename(path)
            log["pdf"].append(
                f"{path.name}: trimmed {trimmed} blank page(s), now {pages} pages, title={title!r}"
            )

    return log


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Post-process split AMD lab outputs (header images, PDF cleanup, metadata)."
    )
    parser.add_argument("folder", type=Path, help="Folder containing split lab files")
    parser.add_argument("--docx-only", action="store_true", help="Only process Word files")
    parser.add_argument("--pdf-only", action="store_true", help="Only process PDF files")
    args = parser.parse_args()

    if not args.folder.is_dir():
        print(f"Error: not a directory: {args.folder}", file=sys.stderr)
        return 1

    do_docx = not args.pdf_only
    do_pdf = not args.docx_only
    log = postprocess_folder(args.folder, docx=do_docx, pdf=do_pdf)

    for line in log["docx"]:
        print(line)
    for line in log["pdf"]:
        print(line)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
