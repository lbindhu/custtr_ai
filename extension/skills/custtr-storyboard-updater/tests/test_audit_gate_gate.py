"""Smoke tests for audit_gate.py infrastructure gates."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from audit_gate import main as gate_main
from constants import EXIT_FATAL


_DECK = {
    "slide_count": 1,
    "slides": [{"slide_number": 1, "texts": [{"text": "Title", "placeholder_type": "title"}], "notes": ""}],
}
_SRC = {"queries": [{"source_id": "s1", "server": "nabu", "query": "q", "summary": "s"}]}
_REF = {"entries": [{"source_id": "s1", "text": "some content"}]}
_VER = {"slides": [{"slide_number": 1, "claims_verified": [], "findings": [], "summary_review": "ok"}]}
_XVAL = {"slides_examined": [1], "slides_with_findings": [], "slides_explicitly_cleared": [], "findings_cleared": []}
_PLAN = {"schema_version": "2.0", "base_slide_count": 1, "actions": [], "story_model": {"primary_message": "m", "key_talking_points": ["k"]}}


def _populate_work_dir(wd: Path, include_concept_decomp: bool = True) -> None:
    (wd / "deck_extract.json").write_text(json.dumps(_DECK), encoding="utf-8")
    (wd / "source_inventory.json").write_text(json.dumps(_SRC), encoding="utf-8")
    (wd / "reference_extract.json").write_text(json.dumps(_REF), encoding="utf-8")
    (wd / "verification_report.json").write_text(json.dumps(_VER), encoding="utf-8")
    (wd / "cross_validation_report.json").write_text(json.dumps(_XVAL), encoding="utf-8")
    (wd / "update_plan.json").write_text(json.dumps(_PLAN), encoding="utf-8")
    if include_concept_decomp:
        cd = {"schema_version": "1.0", "deck": "test.pptx", "source_deltas": []}
        (wd / "concept_decomposition.json").write_text(json.dumps(cd), encoding="utf-8")


class TestConceptDecompGate:
    def test_missing_concept_decomp_returns_exit_fatal(self, tmp_path):
        _populate_work_dir(tmp_path, include_concept_decomp=False)
        rc = gate_main(["--work-dir", str(tmp_path)])
        assert rc == EXIT_FATAL

    def test_present_concept_decomp_passes_gate(self, tmp_path):
        _populate_work_dir(tmp_path, include_concept_decomp=True)
        rc = gate_main(["--work-dir", str(tmp_path)])
        # Gate passes (may return EXIT_OK or EXIT_ERROR for other reasons, but not EXIT_FATAL)
        assert rc != EXIT_FATAL
