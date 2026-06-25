"""Tests for stale_terms.py mandatory sweep functions."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from stale_terms import _version_sweep, _summary_recap_sweep, _notes_structure_sweep, run_sweeps


def _deck(*slides):
    return {"slides": list(slides)}


def _slide(num, *texts, is_title_idx=None):
    text_entries = []
    for i, t in enumerate(texts):
        entry = {"text": t}
        if is_title_idx is not None and i == is_title_idx:
            entry["is_title"] = True
        text_entries.append(entry)
    return {"slide_number": num, "texts": text_entries}


class TestVersionSweep:
    def test_no_target_returns_empty(self):
        deck = _deck(_slide(1, "Version 2024.2"))
        assert _version_sweep(deck, {"target_release": ""}, {}) == []

    def test_target_match_ignored(self):
        deck = _deck(_slide(1, "Version 2024.2"))
        assert _version_sweep(deck, {"target_release": "2024.2"}, {}) == []

    def test_non_target_flagged(self):
        deck = _deck(_slide(2, "Still running 2023.1"))
        errors = _version_sweep(deck, {"target_release": "2024.2"}, {})
        assert len(errors) == 1
        assert "2023.1" in errors[0]

    def test_title_slide_label(self):
        deck = _deck(_slide(1, "2023.1 Training"))
        errors = _version_sweep(deck, {"target_release": "2024.2"}, {})
        assert "title slide" in errors[0]

    def test_non_title_slide_label(self):
        deck = _deck(_slide(5, "2023.1 content"))
        errors = _version_sweep(deck, {"target_release": "2024.2"}, {})
        assert "slide 5" in errors[0]

    def test_version_exception_suppresses(self):
        deck = _deck(_slide(3, "Legacy 2023.1 support"))
        plan = {"version_exceptions": [{"token": "2023.1", "slide": 3, "reason": "historical"}]}
        assert _version_sweep(deck, {"target_release": "2024.2"}, plan) == []

    def test_multiple_versions_on_one_slide(self):
        deck = _deck(_slide(2, "Compare 2023.1 vs 2023.2"))
        errors = _version_sweep(deck, {"target_release": "2024.2"}, {})
        assert len(errors) == 2


class TestSummaryRecapSweep:
    def test_no_summary_slides(self):
        deck = _deck(_slide(1, "Architecture", is_title_idx=0))
        assert _summary_recap_sweep(deck, {"actions": []}) == []

    def test_summary_slide_no_action_flagged(self):
        deck = _deck(_slide(5, "Summary", is_title_idx=0))
        assert len(_summary_recap_sweep(deck, {"actions": []})) == 1

    def test_recap_slide_no_action_flagged(self):
        deck = _deck(_slide(5, "Module Recap", is_title_idx=0))
        assert len(_summary_recap_sweep(deck, {"actions": []})) == 1

    def test_key_takeaways_flagged(self):
        deck = _deck(_slide(5, "Key Takeaways", is_title_idx=0))
        assert len(_summary_recap_sweep(deck, {"actions": []})) == 1

    def test_summary_with_action_ok(self):
        deck = _deck(_slide(5, "Summary", is_title_idx=0))
        plan = {"actions": [{"slide_number": 5, "type": "update_existing"}]}
        assert _summary_recap_sweep(deck, plan) == []

    def test_summary_with_slide_key_ok(self):
        deck = _deck(_slide(5, "Summary", is_title_idx=0))
        plan = {"actions": [{"slide": 5, "type": "update_existing"}]}
        assert _summary_recap_sweep(deck, plan) == []

    def test_fallback_to_first_text_as_title(self):
        deck = _deck(_slide(5, "Summary"))
        assert len(_summary_recap_sweep(deck, {"actions": []})) == 1


class TestNotesStructureSweep:
    def test_clean_notes_changes(self):
        plan = {"actions": [
            {"type": "notes_update", "notes_changes": [{"match_fragment": "old", "replacement_fragment": "new"}]}
        ]}
        assert _notes_structure_sweep(plan) == []

    def test_wholesale_replacement_flagged(self):
        plan = {"actions": [
            {"type": "notes_update", "action_id": "A1",
             "old_speaker_notes": "old text", "speaker_notes": "new text"}
        ]}
        errors = _notes_structure_sweep(plan)
        assert len(errors) == 1
        assert "wholesale" in errors[0]

    def test_update_existing_wholesale_flagged(self):
        plan = {"actions": [
            {"type": "update_existing", "action_id": "A2",
             "old_speaker_notes": "old", "speaker_notes": "new"}
        ]}
        assert len(_notes_structure_sweep(plan)) == 1

    def test_with_notes_changes_ok(self):
        plan = {"actions": [
            {"type": "notes_update", "old_speaker_notes": "old", "speaker_notes": "new",
             "notes_changes": [{"match_fragment": "old", "replacement_fragment": "new"}]}
        ]}
        assert _notes_structure_sweep(plan) == []

    def test_non_notes_action_ignored(self):
        plan = {"actions": [
            {"type": "add_new_slide", "old_speaker_notes": "old", "speaker_notes": "new"}
        ]}
        assert _notes_structure_sweep(plan) == []

    def test_action_type_key_fallback(self):
        plan = {"actions": [
            {"action_type": "notes_update", "action_id": "A3",
             "old_speaker_notes": "old", "speaker_notes": "new"}
        ]}
        assert len(_notes_structure_sweep(plan)) == 1


class TestRunSweeps:
    def test_returns_all_three_keys(self):
        result = run_sweeps(
            {"slides": []},
            {"actions": []},
            {"target_release": ""},
        )
        assert "version_sweep" in result
        assert "summary_recap_sweep" in result
        assert "notes_structure_sweep" in result

    def test_aggregates_errors(self):
        deck = _deck(
            _slide(1, "2023.1 content"),
            _slide(5, "Summary", is_title_idx=0),
        )
        plan = {"actions": [
            {"type": "notes_update", "action_id": "A1",
             "old_speaker_notes": "old", "speaker_notes": "new"}
        ]}
        stale = {"target_release": "2024.2"}
        result = run_sweeps(deck, plan, stale)
        assert len(result["version_sweep"]) >= 1
        assert len(result["summary_recap_sweep"]) >= 1
        assert len(result["notes_structure_sweep"]) >= 1
