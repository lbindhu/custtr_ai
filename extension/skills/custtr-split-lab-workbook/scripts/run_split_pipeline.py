"""Full AMD lab workbook split pipeline: split, post-process DOCX, export PDF, post-process PDF, export combined workbook PDF."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SPLIT_SCRIPT = SCRIPT_DIR / "split_lab_workbook.py"
POSTPROCESS_SCRIPT = SCRIPT_DIR / "postprocess_lab_outputs.py"
EXPORT_SCRIPT = SCRIPT_DIR / "export_lab_pdfs.ps1"
WORKBOOK_PDF_SCRIPT = SCRIPT_DIR / "export_workbook_pdf.py"
POWERSHELL = Path(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")


def _section(title: str) -> None:
    print(f"\n=== {title} ===", flush=True)


def run_split(source: Path, output_dir: Path | None) -> Path:
    _section("Split workbook")
    cmd = [sys.executable, str(SPLIT_SCRIPT), str(source)]
    if output_dir is not None:
        cmd.extend(["-o", str(output_dir)])
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        raise RuntimeError("split_lab_workbook.py failed")
    return output_dir or source.parent


def run_postprocess_docx(folder: Path) -> None:
    _section("Post-process DOCX (remove last-page header images)")
    cmd = [sys.executable, str(POSTPROCESS_SCRIPT), str(folder), "--docx-only"]
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        raise RuntimeError("postprocess_lab_outputs.py (docx) failed")


def run_export_pdf(folder: Path) -> None:
    _section("Export PDF via Word")
    if not EXPORT_SCRIPT.exists():
        raise FileNotFoundError(f"Missing export script: {EXPORT_SCRIPT}")
    if not POWERSHELL.exists():
        raise FileNotFoundError("Word PDF export requires powershell.exe on Windows")

    cmd = [
        str(POWERSHELL),
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(EXPORT_SCRIPT),
        "-Folder",
        str(folder),
    ]
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        raise RuntimeError("export_lab_pdfs.ps1 failed")


def run_postprocess_pdf(folder: Path) -> None:
    _section("Post-process PDF (trim blanks, set metadata)")
    cmd = [sys.executable, str(POSTPROCESS_SCRIPT), str(folder), "--pdf-only"]
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        raise RuntimeError("postprocess_lab_outputs.py (pdf) failed")


def run_export_workbook_pdf(source: Path, output_dir: Path) -> None:
    _section("Export combined workbook PDF (metadata, bookmarks, blank pages)")
    pdf_path = output_dir / f"{source.stem}.pdf"
    cmd = [sys.executable, str(WORKBOOK_PDF_SCRIPT), str(source), "-o", str(pdf_path)]
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        raise RuntimeError("export_workbook_pdf.py failed")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Split an AMD lab workbook and run full post-processing pipeline."
    )
    parser.add_argument("source", type=Path, help="Combined lab workbook .docx")
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=None,
        help="Output folder (default: same folder as source)",
    )
    parser.add_argument(
        "--split-only",
        action="store_true",
        help="Only split; skip post-processing and PDF export",
    )
    parser.add_argument(
        "--no-pdf",
        action="store_true",
        help="Split and post-process DOCX only; skip PDF export and PDF post-processing",
    )
    parser.add_argument(
        "--inspect",
        action="store_true",
        help="List labs that would be split; do not write files",
    )
    args = parser.parse_args()

    if args.inspect:
        cmd = [sys.executable, str(SPLIT_SCRIPT), str(args.source), "--inspect"]
        if args.output_dir is not None:
            cmd.extend(["-o", str(args.output_dir)])
        return subprocess.run(cmd, check=False).returncode

    try:
        folder = run_split(args.source, args.output_dir)
        if args.split_only:
            print(f"\nDone. Split files written to:\n{folder}")
            return 0

        run_postprocess_docx(folder)
        if args.no_pdf:
            print(f"\nDone. DOCX files written to:\n{folder}")
            return 0

        run_export_pdf(folder)
        run_postprocess_pdf(folder)
        run_export_workbook_pdf(args.source, folder)
    except (FileNotFoundError, RuntimeError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    docx_count = len(list(folder.glob("[0-9][0-9] *.docx")))
    pdf_count = len(list(folder.glob("[0-9][0-9] *.pdf")))
    workbook_pdf = folder / f"{args.source.stem}.pdf"
    workbook_note = f"\nCombined workbook PDF: {workbook_pdf.name}" if workbook_pdf.exists() else ""
    print(f"\nDone. {docx_count} DOCX and {pdf_count} split-lab PDF files written to:\n{folder}{workbook_note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
