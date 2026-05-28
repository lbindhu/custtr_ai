"""Tests for json_helpers.safe_load_json and try_load_json."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from json_helpers import safe_load_json, try_load_json


class TestSafeLoadJson:
    def test_valid_json(self, tmp_path):
        f = tmp_path / "ok.json"
        f.write_text('{"key": "value"}', encoding="utf-8")
        result = safe_load_json(f)
        assert result == {"key": "value"}

    def test_missing_file_exits(self, tmp_path):
        with pytest.raises(SystemExit):
            safe_load_json(tmp_path / "nope.json")

    def test_malformed_json_exits(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("{invalid json", encoding="utf-8")
        with pytest.raises(SystemExit):
            safe_load_json(f)

    def test_label_in_error(self, tmp_path, capsys):
        f = tmp_path / "bad.json"
        f.write_text("{nope}", encoding="utf-8")
        with pytest.raises(SystemExit):
            safe_load_json(f, "my_artifact")
        captured = capsys.readouterr()
        assert "my_artifact" in captured.err


class TestTryLoadJson:
    def test_missing_returns_none(self, tmp_path):
        assert try_load_json(tmp_path / "nope.json") is None

    def test_valid_json(self, tmp_path):
        f = tmp_path / "ok.json"
        f.write_text("[1, 2, 3]", encoding="utf-8")
        assert try_load_json(f) == [1, 2, 3]

    def test_malformed_json_exits(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("not json!", encoding="utf-8")
        with pytest.raises(SystemExit):
            try_load_json(f)
