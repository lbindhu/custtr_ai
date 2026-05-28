"""Tests for merge_slide_rows.py."""
import json
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from merge_slide_rows import merge


def _write_sidecar(rows_dir: Path, slide_number: int, findings=None) -> Path:
    rows_dir.mkdir(parents=True, exist_ok=True)
    sidecar = rows_dir / f"s{slide_number:02d}_verification.json"
    data = {
        "slide_number": slide_number,
        "claims_verified": [f"claim for slide {slide_number}"],
        "findings": findings or [],
        "summary_review": None,
        "cleared": False,
    }
    sidecar.write_text(json.dumps(data), encoding="utf-8")
    return sidecar


class TestMergeSlideRows:
    def test_five_sidecars_assembled_in_order(self, tmp_path):
        rows_dir = tmp_path / "slide_rows"
        for n in [5, 2, 1, 4, 3]:
            _write_sidecar(rows_dir, n)
        out = tmp_path / "verification_report.json"
        rc = merge(tmp_path, out)
        assert rc == 0
        report = json.loads(out.read_text())
        numbers = [r["slide_number"] for r in report["slides"]]
        assert numbers == [1, 2, 3, 4, 5]

    def test_findings_preserved(self, tmp_path):
        rows_dir = tmp_path / "slide_rows"
        finding = {"id": "S3-F01", "axis": "A_topic", "shape": "Shape 1", "text": "old", "issue": "stale", "source_ids": ["s1"]}
        _write_sidecar(rows_dir, 3, findings=[finding])
        out = tmp_path / "verification_report.json"
        merge(tmp_path, out)
        report = json.loads(out.read_text())
        assert report["slides"][0]["findings"] == [finding]

    def test_missing_slide_rows_dir_writes_empty(self, tmp_path):
        out = tmp_path / "verification_report.json"
        rc = merge(tmp_path, out)
        assert rc == 0
        report = json.loads(out.read_text())
        assert report["slides"] == []

    def test_empty_slide_rows_dir_writes_empty(self, tmp_path):
        (tmp_path / "slide_rows").mkdir()
        out = tmp_path / "verification_report.json"
        rc = merge(tmp_path, out)
        assert rc == 0
        assert json.loads(out.read_text())["slides"] == []

    def test_single_sidecar_produces_one_element(self, tmp_path):
        rows_dir = tmp_path / "slide_rows"
        _write_sidecar(rows_dir, 7)
        out = tmp_path / "verification_report.json"
        merge(tmp_path, out)
        report = json.loads(out.read_text())
        assert len(report["slides"]) == 1
        assert report["slides"][0]["slide_number"] == 7

    def test_idempotency_newer_output_not_overwritten(self, tmp_path):
        rows_dir = tmp_path / "slide_rows"
        _write_sidecar(rows_dir, 1)
        out = tmp_path / "verification_report.json"
        # Write output with a sentinel value and a mtime in the future
        sentinel = {"slides": [{"slide_number": 99, "sentinel": True}]}
        out.write_text(json.dumps(sentinel), encoding="utf-8")
        # Bump mtime to be clearly newer than the sidecar
        future = time.time() + 10
        import os
        os.utime(out, (future, future))
        merge(tmp_path, out)
        # Should not have been overwritten
        reloaded = json.loads(out.read_text())
        assert reloaded["slides"][0].get("sentinel") is True

    def test_idempotency_older_output_is_overwritten(self, tmp_path):
        rows_dir = tmp_path / "slide_rows"
        _write_sidecar(rows_dir, 1)
        out = tmp_path / "verification_report.json"
        old = {"slides": [{"slide_number": 99, "sentinel": True}]}
        out.write_text(json.dumps(old), encoding="utf-8")
        # Set mtime to the past so sidecar is newer
        import os
        past = time.time() - 10
        os.utime(out, (past, past))
        merge(tmp_path, out)
        reloaded = json.loads(out.read_text())
        assert reloaded["slides"][0]["slide_number"] == 1
        assert not reloaded["slides"][0].get("sentinel")
