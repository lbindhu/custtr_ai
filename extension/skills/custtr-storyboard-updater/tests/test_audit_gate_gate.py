"""Smoke tests for audit_gate.py infrastructure gates."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from audit_gate import (
    main as gate_main,
    run_generational_analysis_sweep,
    run_original_notes_sweep,
    run_scope_depth_checks,
    run_scope_consistency_sweep,
    run_structural_checks,
    run_verification_sweep,
)
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


class TestRequiredSourceMinimums:
    def test_require_sources_uses_coverage_not_fixed_channel_counts(self):
        source_inventory = {
            "queries": [
                {"source_id": "N1", "server": "nabu", "query": "authoritative source", "summary": "covers the verified claim"},
            ]
        }
        errors, *_ = run_structural_checks(
            _DECK,
            source_inventory,
            _REF,
            _VER,
            {"slides_examined": [1]},
            None,
            [],
            require_sources=True,
        )
        joined = "\n".join(errors)
        assert "NABU queries" not in joined
        assert "Confluence queries" not in joined
        assert "JIRA queries" not in joined
        assert "Web Search queries" not in joined
        assert "Vivado Doc Search queries" not in joined


class TestScopeDepthGate:
    def test_shallow_counts_are_warnings_not_hard_errors_when_evidence_exists(self, tmp_path):
        deck = {
            "slides": [
                {"slide_number": i, "texts": [{"text": f"Slide {i}", "placeholder_type": "title"}], "notes": ""}
                for i in range(1, 18)
            ]
        }
        plan = {"actions": []}
        stale_terms_doc = {"stale_terms": [], "product_variants": ["CPM5", "CPM6"]}
        concept_decomp = {"source_deltas": []}
        src = {"queries": [{"source_id": "S1", "server": "nabu", "results_count": 1}]}
        stale_scan_doc = [{"slide_number": i, "hits": []} for i in range(1, 18)]

        errors, warnings = run_scope_depth_checks(
            deck,
            plan,
            stale_terms_doc,
            concept_decomp,
            tmp_path / "missing_parity_matrix.json",
            src,
            stale_scan_doc,
        )

        assert errors == []
        joined_warnings = "\n".join(warnings)
        assert "stale-term" in joined_warnings
        assert "plan action" in joined_warnings


class TestScopeConsistencyGate:
    def test_unaddressed_scope_consistency_violation_is_error(self):
        scope_doc = {
            "violations": [
                {
                    "slide_number": 7,
                    "scope_phrases": ["Versal devices"],
                    "stale_tokens": ["32 GT/sec"],
                }
            ]
        }
        errors, warnings = run_scope_consistency_sweep(
            scope_doc,
            verification_doc={"slides": []},
            xval={"findings_cleared": [], "slides_explicitly_cleared": []},
            plan={"actions": []},
        )
        assert warnings == []
        assert "scope-consistency violation" in "\n".join(errors)


class TestOriginalNotesGate:
    def test_notes_update_must_match_original_notes_file(self):
        plan = {
            "actions": [
                {
                    "type": "notes_update",
                    "slide_number": 3,
                    "old_speaker_notes": "paraphrased original",
                    "notes_changes": [
                        {
                            "match_fragment": "paraphrased",
                            "replacement_fragment": "new text",
                        }
                    ],
                }
            ]
        }
        errors = run_original_notes_sweep({"3": "The real original notes."}, plan)
        assert "old_speaker_notes" in "\n".join(errors)

    def test_notes_update_fragment_must_match_original_notes_file(self):
        plan = {
            "actions": [
                {
                    "type": "notes_update",
                    "slide_number": 3,
                    "old_speaker_notes": "The real original notes.",
                    "notes_changes": [
                        {
                            "match_fragment": "not present",
                            "replacement_fragment": "new text",
                        }
                    ],
                }
            ]
        }
        errors = run_original_notes_sweep({"3": "The real original notes."}, plan)
        assert "match_fragment" in "\n".join(errors)


class TestGenerationalAnalysisSweep:
    _CORPUS = "some authoritative content from the source inventory for verification"

    def test_rejects_passive_phrases(self):
        xval = {
            "slides_explicitly_cleared": [{
                "slide": 2,
                "reason": "no stale terms found on this slide",
                "source_ids": ["s1"],
                "generational_analysis": {
                    "content_generation": "Gen 1 Versal Premium DDR5 map",
                    "target_generation_changes": "Gen 2 adds expanded ECC (SRC-S1)",
                    "why_no_impact": "Register map unchanged per source section 4.",
                },
            }]
        }
        errors = run_generational_analysis_sweep(
            xval, corpus_blob=self._CORPUS, known_source_ids={"s1"},
        )
        assert any("passive phrase" in e for e in errors)

    def test_requires_source_ids_and_corpus_anchor(self):
        xval = {
            "slides_explicitly_cleared": [{
                "slide": 2,
                "reason": "DDR5 register layout unchanged for this slide topic.",
                "source_ids": ["s1"],
                "generational_analysis": {
                    "content_generation": "Gen 1 Versal Premium DDR5 map",
                    "target_generation_changes": "Gen 2 adds expanded ECC modes per s1 source entry",
                    "why_no_impact": "authoritative content from the source inventory for verification on this slide",
                },
            }]
        }
        errors = run_generational_analysis_sweep(
            xval, corpus_blob=self._CORPUS, known_source_ids={"s1"},
        )
        assert errors == []

    def test_rejects_padding_without_corpus_anchor(self):
        xval = {
            "slides_explicitly_cleared": [{
                "slide": 2,
                "reason": "DDR5 register layout unchanged for this slide topic.",
                "source_ids": ["s1"],
                "generational_analysis": {
                    "content_generation": "Gen 1 Versal Premium DDR5 map",
                    "target_generation_changes": "Gen 2 adds expanded ECC modes per SRC-S1",
                    "why_no_impact": "generic padding text with no source tie-in whatsoever here",
                },
            }]
        }
        errors = run_generational_analysis_sweep(
            xval, corpus_blob=self._CORPUS, known_source_ids={"s1"},
        )
        assert any("corpus anchor" in e or "reference_extract" in e for e in errors)


class TestClaimDispositionEnforcement:
    def test_claim_disposition_required_on_claims_verified(self):
        slides = _DECK["slides"]
        rows = {
            1: {
                "slide_number": 1,
                "claims_verified": [{
                    "claim": "test claim",
                    "source_id": "s1",
                    "quoted_source": "some authoritative content from the source",
                }],
                "findings": [],
            }
        }
        errors, *_ = run_verification_sweep(
            slides,
            rows,
            _XVAL,
            _PLAN,
            "some authoritative content from the source",
            {"s1"},
            require_finding_actions=False,
        )
        assert any("claim_disposition" in e for e in errors)

    def test_valid_claim_disposition_passes(self):
        slides = _DECK["slides"]
        rows = {
            1: {
                "slide_number": 1,
                "claims_verified": [{
                    "claim": "test claim",
                    "claim_disposition": "supported",
                    "source_entailment": "Source directly supports this claim with evidence.",
                    "source_id": "s1",
                    "quoted_source": "some authoritative content from the source",
                }],
                "findings": [],
            }
        }
        xval = {
            **_XVAL,
            "slides_explicitly_cleared": [{
                "slide": 1,
                "reason": "Claim verified against cited source text.",
                "source_ids": ["s1"],
                "generational_analysis": {
                    "content_generation": "Gen 1 content on title slide",
                    "target_generation_changes": "Target release unchanged for title (SRC-S1)",
                    "why_no_impact": "some authoritative content from the source applies here",
                },
            }],
        }
        errors, *_ = run_verification_sweep(
            slides,
            rows,
            xval,
            _PLAN,
            "some authoritative content from the source",
            {"s1"},
            require_finding_actions=False,
        )
        disp_errors = [e for e in errors if "claim_disposition" in e or "source_entailment" in e]
        assert disp_errors == []


class TestLegacyRequireCoverageRemoved:
    def test_legacy_flag_exits_fatal(self, tmp_path):
        _populate_work_dir(tmp_path)
        rc = gate_main(["--work-dir", str(tmp_path), "--legacy-require-zero-coverage-gaps"])
        assert rc == EXIT_FATAL
