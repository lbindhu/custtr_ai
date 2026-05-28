"""Tests for merge_storyboard.py helper functions."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from merge_storyboard import ranges, check_output_writable, write_merge_status


class TestRanges:
    def test_empty(self):
        assert ranges([]) == []

    def test_single(self):
        assert ranges([5]) == ["5"]

    def test_consecutive(self):
        assert ranges([1, 2, 3]) == ["1-3"]

    def test_gap(self):
        assert ranges([1, 2, 5, 6]) == ["1-2", "5-6"]

    def test_mixed(self):
        assert ranges([1, 3, 4, 5, 8]) == ["1", "3-5", "8"]

    def test_dedup_and_sort(self):
        assert ranges([5, 3, 3, 1, 2]) == ["1-3", "5"]

    def test_all_isolated(self):
        assert ranges([1, 5, 10]) == ["1", "5", "10"]

    def test_single_pair(self):
        assert ranges([7, 8]) == ["7-8"]


class TestCheckOutputWritable:
    def test_new_file_writable_dir(self, tmp_path):
        check_output_writable(tmp_path / "new_deck.pptx")

    def test_existing_file_writable(self, tmp_path):
        f = tmp_path / "deck.pptx"
        f.write_bytes(b"PK\x03\x04")
        check_output_writable(f)

    def test_nonexistent_parent_passes(self, tmp_path):
        check_output_writable(tmp_path / "no_such_dir" / "deck.pptx")

    def test_existing_readonly_file_exits(self, tmp_path):
        f = tmp_path / "locked.pptx"
        f.write_bytes(b"PK\x03\x04")
        f.chmod(0o444)
        try:
            with pytest.raises(SystemExit):
                check_output_writable(f)
        finally:
            f.chmod(0o644)


class TestWriteMergeStatus:
    def test_writes_sidecar(self, tmp_path):
        output = tmp_path / "merged.pptx"
        output.write_bytes(b"PK\x03\x04")
        write_merge_status(output, 0)
        sidecar = tmp_path / "merged.pptx.merge_status.json"
        assert sidecar.exists()
        data = json.loads(sidecar.read_text(encoding="utf-8"))
        assert data["exit_code"] == 0
        assert data["output_path"] == str(output)
        assert "completed_at" in data
        assert data["output_mtime_at_save"] is not None

    def test_nonzero_exit_code(self, tmp_path):
        output = tmp_path / "merged.pptx"
        output.write_bytes(b"PK\x03\x04")
        write_merge_status(output, 1)
        sidecar = tmp_path / "merged.pptx.merge_status.json"
        data = json.loads(sidecar.read_text(encoding="utf-8"))
        assert data["exit_code"] == 1

    def test_missing_output_file(self, tmp_path):
        output = tmp_path / "nonexistent.pptx"
        write_merge_status(output, 0)
        sidecar = tmp_path / "nonexistent.pptx.merge_status.json"
        data = json.loads(sidecar.read_text(encoding="utf-8"))
        assert data["output_mtime_at_save"] is None
