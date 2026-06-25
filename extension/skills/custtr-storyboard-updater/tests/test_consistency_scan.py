"""Tests for consistency_scan.py (intra-slide term consistency, Rule 35)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from consistency_scan import (  # noqa: E402
    is_technical,
    is_internal_letter_near_miss,
    scan_intra_slide_variants,
    scan_common_typos,
)
from audit_gate import (  # noqa: E402
    run_consistency_reconciliation_sweep,
    run_proofread_review_sweep,
)


class TestIsTechnical:
    def test_alnum_identifier(self):
        assert is_technical("A78AE")
        assert is_technical("CPM5")
        assert is_technical("DDR5")
        assert is_technical("Gen6")

    def test_plain_word_excluded(self):
        assert not is_technical("Versal")
        assert not is_technical("controller")

    def test_pure_number_excluded(self):
        assert not is_technical("2026")
        assert not is_technical("256")

    def test_too_short(self):
        assert not is_technical("A1")


class TestNearMiss:
    def test_canonical_failure_a78ae_vs_a78e(self):
        # The real shipped bug: internal letter deletion.
        assert is_internal_letter_near_miss("A78AE", "A78E")
        assert is_internal_letter_near_miss("A78E", "A78AE")

    def test_generation_siblings_not_flagged(self):
        # Digit-only differences are legitimate distinct products.
        assert not is_internal_letter_near_miss("CPM5", "CPM6")
        assert not is_internal_letter_near_miss("DDR4", "DDR5")
        assert not is_internal_letter_near_miss("A72", "A78")
        assert not is_internal_letter_near_miss("Gen5", "Gen6")

    def test_prefix_variant_not_flagged(self):
        # LPDDR5 vs DDR5 — distinct memory families, prefix difference.
        assert not is_internal_letter_near_miss("LPDDR5", "DDR5")

    def test_suffix_variant_not_flagged(self):
        assert not is_internal_letter_near_miss("DDR5", "DDR5X")

    def test_identical_not_flagged(self):
        assert not is_internal_letter_near_miss("A78AE", "A78AE")

    def test_large_edit_not_flagged(self):
        assert not is_internal_letter_near_miss("A78AE", "B12XYZ")


class TestScanIntraSlideVariants:
    def _slide(self, texts, notes=""):
        return {"slides": [{"slide_number": 12, "title": "PS", "texts": texts, "notes": notes}]}

    def test_detects_callout_vs_diagram_label(self):
        deck = self._slide(
            texts=[
                {"shape_id": "20", "shape_name": "Callout", "text": "Dual-core A78AE"},
                {"shape_id": "14", "shape_name": "Diagram", "text": "A78E cluster"},
            ],
            notes="The A78AE provides lockstep operation.",
        )
        results = scan_intra_slide_variants(deck)
        assert len(results) == 1
        v = results[0]
        assert v["slide_number"] == 12
        assert set(t.lower() for t in v["tokens"]) == {"a78ae", "a78e"}
        assert not v["advisory"]
        # Locations are reported per token.
        assert "notes" in v["locations"]["A78AE"]

    def test_no_false_positive_on_gen_siblings(self):
        deck = self._slide(texts=[
            {"shape_id": "1", "shape_name": "Body", "text": "CPM5 and CPM6 both ship"},
            {"shape_id": "2", "shape_name": "Body", "text": "DDR4 and DDR5 supported"},
        ])
        assert scan_intra_slide_variants(deck) == []

    def test_each_pair_reported_once(self):
        deck = self._slide(texts=[
            {"shape_id": "1", "shape_name": "A", "text": "A78AE"},
            {"shape_id": "2", "shape_name": "B", "text": "A78E"},
            {"shape_id": "3", "shape_name": "C", "text": "A78AE again"},
        ])
        results = scan_intra_slide_variants(deck)
        assert len(results) == 1


class TestScanCommonTypos:
    def test_flags_known_typo_as_advisory(self):
        deck = {"slides": [{"slide_number": 3, "title": "T",
                            "texts": [{"shape_id": "1", "shape_name": "Body",
                                       "text": "Fully programable logic"}], "notes": ""}]}
        results = scan_common_typos(deck)
        assert len(results) == 1
        assert results[0]["advisory"] is True
        assert results[0]["suggested"] == "programmable"

    def test_clean_text_no_typos(self):
        deck = {"slides": [{"slide_number": 3, "title": "T",
                            "texts": [{"shape_id": "1", "shape_name": "Body",
                                       "text": "Fully programmable logic"}], "notes": ""}]}
        assert scan_common_typos(deck) == []


class TestReconciliationSweep:
    def _violation(self):
        return [{
            "slide_number": 12, "type": "intra_slide_variant", "advisory": False,
            "tokens": ["A78AE", "A78E"],
            "issue": "near-miss",
        }]

    def test_unaddressed_violation_is_error(self):
        errors, warnings = run_consistency_reconciliation_sweep(
            self._violation(), {"slides": []}, {}, {"actions": []},
        )
        assert len(errors) == 1
        assert "A78AE" in errors[0] or "A78E" in errors[0]

    def test_violation_addressed_by_finding(self):
        verification = {"slides": [{"slide_number": 12, "findings": [
            {"finding_id": "F1", "description": "Diagram label A78E should be A78AE"}
        ]}]}
        errors, warnings = run_consistency_reconciliation_sweep(
            self._violation(), verification, {}, {"actions": []},
        )
        assert errors == []

    def test_violation_addressed_by_action(self):
        plan = {"actions": [
            {"type": "fragment_replace", "slide_number": 12,
             "find_fragment": "A78E", "replace_fragment": "A78AE"}
        ]}
        errors, warnings = run_consistency_reconciliation_sweep(
            self._violation(), {"slides": []}, {}, plan,
        )
        assert errors == []

    def test_violation_addressed_by_clear(self):
        xval = {"slides_explicitly_cleared": [
            {"slide": 12, "reason": "A78E is an intentional shorthand alias of A78AE here",
             "source_ids": ["SRC-1"]}
        ]}
        errors, warnings = run_consistency_reconciliation_sweep(
            self._violation(), {"slides": []}, xval, {"actions": []},
        )
        assert errors == []

    def test_advisory_typo_is_warning_not_error(self):
        doc = [{"slide_number": 3, "type": "advisory_typo", "advisory": True,
                "tokens": ["programable"], "issue": "possible misspelling"}]
        errors, warnings = run_consistency_reconciliation_sweep(
            doc, {"slides": []}, {}, {"actions": []},
        )
        assert errors == []
        assert len(warnings) == 1

    def test_empty_doc_noop(self):
        errors, warnings = run_consistency_reconciliation_sweep(
            None, {"slides": []}, {}, {"actions": []},
        )
        assert errors == [] and warnings == []

    def test_proofread_dismissal_reconciles_false_positive(self):
        # LLM documented the signal as a false positive — no finding required.
        proofread = {"scan_signals_dispositioned": [
            {"slide_number": 12, "tokens": ["A78AE", "A78E"],
             "disposition": "rejected_lint", "note": "Distinct valid SKUs per SRC-1"}
        ]}
        errors, warnings = run_consistency_reconciliation_sweep(
            self._violation(), {"slides": []}, {}, {"actions": []}, proofread,
        )
        assert errors == []

    def test_proofread_confirmed_still_requires_action(self):
        # confirmed_finding does NOT dismiss — must still be represented.
        proofread = {"scan_signals_dispositioned": [
            {"slide_number": 12, "tokens": ["A78AE", "A78E"],
             "disposition": "confirmed_finding", "note": "real typo"}
        ]}
        errors, warnings = run_consistency_reconciliation_sweep(
            self._violation(), {"slides": []}, {}, {"actions": []}, proofread,
        )
        assert len(errors) == 1

    def test_proofread_dismissal_without_note_does_not_reconcile(self):
        proofread = {"scan_signals_dispositioned": [
            {"slide_number": 12, "tokens": ["A78AE", "A78E"],
             "disposition": "rejected_lint", "note": ""}
        ]}
        errors, warnings = run_consistency_reconciliation_sweep(
            self._violation(), {"slides": []}, {}, {"actions": []}, proofread,
        )
        assert len(errors) == 1


class TestProofreadReviewSweep:
    _SLIDES = [{"slide_number": 1}, {"slide_number": 2}]
    _SCAN = [{"slide_number": 2, "advisory": False, "tokens": ["A78AE", "A78E"],
              "issue": "near-miss"}]

    def _proofread(self, **extra):
        base = {
            "slides_reviewed": [1, 2],
            "scan_signals_dispositioned": [
                {"slide_number": 2, "tokens": ["A78AE", "A78E"],
                 "disposition": "confirmed_finding", "note": "typo", "finding_id": "F1"}
            ],
            "issues": [],
        }
        base.update(extra)
        return base

    def test_missing_file_is_error(self):
        errors, warnings = run_proofread_review_sweep(
            None, self._SCAN, self._SLIDES, {"slides": []}, {}, {"actions": []},
            stage="pre-plan",
        )
        assert any("proofread_review.json" in e for e in errors)

    def test_incomplete_slide_coverage_is_error(self):
        pr = self._proofread(slides_reviewed=[1])
        errors, warnings = run_proofread_review_sweep(
            pr, self._SCAN, self._SLIDES, {"slides": []}, {}, {"actions": []},
            stage="pre-plan",
        )
        assert any("slides_reviewed" in e for e in errors)

    def test_undispositioned_signal_is_error(self):
        pr = self._proofread(scan_signals_dispositioned=[])
        errors, warnings = run_proofread_review_sweep(
            pr, self._SCAN, self._SLIDES, {"slides": []}, {}, {"actions": []},
            stage="pre-plan",
        )
        assert any("not dispositioned" in e for e in errors)

    def test_clean_proofread_passes(self):
        errors, warnings = run_proofread_review_sweep(
            self._proofread(), self._SCAN, self._SLIDES, {"slides": []}, {},
            {"actions": []}, stage="pre-plan",
        )
        assert errors == []

    def test_fix_issue_unaddressed_warns_at_preplan_errors_at_preexecute(self):
        pr = self._proofread(issues=[
            {"slide_number": 1, "type": "grammar", "severity": "fix",
             "description": "awkward"}
        ])
        pre_plan_err, pre_plan_warn = run_proofread_review_sweep(
            pr, self._SCAN, self._SLIDES, {"slides": []}, {}, {"actions": []},
            stage="pre-plan",
        )
        assert any("severity 'fix'" in w for w in pre_plan_warn)
        assert not any("severity 'fix'" in e for e in pre_plan_err)

        pre_exec_err, _ = run_proofread_review_sweep(
            pr, self._SCAN, self._SLIDES, {"slides": []}, {}, {"actions": []},
            stage="pre-execute",
        )
        assert any("severity 'fix'" in e for e in pre_exec_err)

    def test_fix_issue_addressed_by_action_passes(self):
        pr = self._proofread(issues=[
            {"slide_number": 1, "type": "grammar", "severity": "fix",
             "description": "awkward"}
        ])
        plan = {"actions": [{"type": "update_existing", "slide_number": 1}]}
        errors, warnings = run_proofread_review_sweep(
            pr, self._SCAN, self._SLIDES, {"slides": []}, {}, plan,
            stage="pre-execute",
        )
        assert not any("severity 'fix'" in e for e in errors)
