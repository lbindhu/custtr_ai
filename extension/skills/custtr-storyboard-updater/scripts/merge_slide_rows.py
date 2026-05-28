#!/usr/bin/env python3
"""Assemble verification_report.json from per-slide sidecar and batch files.

During Phase 3 the LLM writes audited slides to:
  <work_dir>/slide_rows/batch_NN.json  (JSON array of slide rows, preferred)
  <work_dir>/slide_rows/sNN_verification.json  (single slide row, legacy)

This script reads all sources, sorts by slide_number, and writes
verification_report.json.  Idempotent: if verification_report.json
already exists and is newer than every source file, it is left unchanged.
"""
import argparse
import json
import sys
from pathlib import Path


def merge(work_dir: Path, output: Path) -> int:
    rows_dir = work_dir / "slide_rows"
    if not rows_dir.exists():
        output.write_text(json.dumps({"slides": []}, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[merge_slide_rows] No slide_rows/ directory found. Wrote empty report to {output}")
        return 0

    per_slide = sorted(rows_dir.glob("s*_verification.json"))
    batches = sorted(rows_dir.glob("batch_*.json"))
    all_files = per_slide + batches
    if not all_files:
        output.write_text(json.dumps({"slides": []}, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[merge_slide_rows] No sidecars or batch files found. Wrote empty report to {output}")
        return 0

    # Idempotency: skip if output is newer than every source file
    if output.exists():
        output_mtime = output.stat().st_mtime
        newest = max(f.stat().st_mtime for f in all_files)
        if output_mtime >= newest:
            print(f"[merge_slide_rows] {output.name} is up-to-date; skipping merge.")
            return 0

    rows = []
    errors = []
    for src_file in all_files:
        try:
            data = json.loads(src_file.read_text(encoding="utf-8"))
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        rows.append(item)
                    else:
                        errors.append(f"{src_file.name}: array item is {type(item).__name__}, expected object")
            elif isinstance(data, dict):
                rows.append(data)
            else:
                errors.append(f"{src_file.name}: expected JSON object or array, got {type(data).__name__}")
        except Exception as exc:
            errors.append(f"{src_file.name}: {exc}")

    if errors:
        for e in errors:
            print(f"[merge_slide_rows] WARNING: {e}", file=sys.stderr)

    rows.sort(key=lambda r: int(r.get("slide_number") or 0))
    report = {"slides": rows}
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[merge_slide_rows] Merged {len(rows)} slide rows → {output}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Merge per-slide sidecar rows into verification_report.json")
    ap.add_argument("--work-dir", required=True, help="Work directory containing slide_rows/")
    ap.add_argument("--output", help="Output path (default: <work-dir>/verification_report.json)")
    args = ap.parse_args(argv)

    wd = Path(args.work_dir)
    out = Path(args.output) if args.output else wd / "verification_report.json"
    return merge(wd, out)


if __name__ == "__main__":
    sys.exit(main())
