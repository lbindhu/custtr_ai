"""Tests for ost_reviewed field validation on notes_update actions in validate_plan.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from validate_plan import validate  # noqa: E402

_STORY = {"primary_message": "msg", "key_talking_points": ["pt1"]}

_BASE_PLAN = {
    "schema_version": "2.0",
    "deck": "test.pptx",
    "target_version": "2026.1",
    "status": "approved",
}


def _plan_with_actions(*actions) -> dict:
    return {**_BASE_PLAN, "actions": list(actions)}


def _notes_action(**extra) -> dict:
    base = {
        "type": "notes_update",
        "slide_number": 5,
        "reason": "update notes",
        "source_basis": [{"source_id": "SRC-01"}],
        "old_speaker_notes": "original notes text here with old fragment",
        "notes_changes": [
            {"match_fragment": "old fragment", "replacement_fragment": "new fragment"}
        ],
    }
    base.update(extra)
    return base


def _ost_companion(slide_number: int = 5, action_type: str = "update_existing") -> dict:
    return {
        "type": action_type,
        "slide_number": slide_number,
        "reason": "update OST",
        "source_basis": [{"source_id": "SRC-01"}],
        "match_text": "old ost text",
        "replacement_text": "new ost text",
    }


# ---------------------------------------------------------------------------
# TestOstReviewedFieldPresence
# ---------------------------------------------------------------------------

class TestOstReviewedFieldPresence:
    def test_missing_ost_reviewed_is_error(self):
        action = _notes_action()
        errors, _ = validate(_plan_with_actions(action), _STORY)
        ost_errors = [e for e in errors if "ost_reviewed" in e and "missing" in e]
        assert ost_errors, f"Expected missing ost_reviewed error, got: {errors}"

    def test_consistent_with_note_passes(self):
        action = _notes_action(
            ost_reviewed="consistent",
            ost_review_note="OST already has the spec value in Shape 11.",
        )
        errors, _ = validate(_plan_with_actions(action), _STORY)
        ost_errors = [e for e in errors if "ost_reviewed" in e]
        assert not ost_errors, f"Unexpected ost_reviewed errors: {ost_errors}"

    def test_companion_action_added_with_companion_passes(self):
        notes = _notes_action(ost_reviewed="companion_action_added")
        companion = _ost_companion(slide_number=5)
        errors, _ = validate(_plan_with_actions(notes, companion), _STORY)
        ost_errors = [e for e in errors if "ost_reviewed" in e]
        assert not ost_errors, f"Unexpected ost_reviewed errors: {ost_errors}"


# ---------------------------------------------------------------------------
# TestOstReviewedInvalidValue
# ---------------------------------------------------------------------------

class TestOstReviewedInvalidValue:
    def test_arbitrary_string_is_error(self):
        action = _notes_action(ost_reviewed="maybe")
        errors, _ = validate(_plan_with_actions(action), _STORY)
        ost_errors = [e for e in errors if "ost_reviewed" in e and "invalid" in e]
        assert ost_errors, f"Expected invalid value error, got: {errors}"

    def test_boolean_true_is_error(self):
        action = _notes_action(ost_reviewed=True)
        errors, _ = validate(_plan_with_actions(action), _STORY)
        ost_errors = [e for e in errors if "ost_reviewed" in e and "invalid" in e]
        assert ost_errors, f"Expected invalid value error for boolean, got: {errors}"


# ---------------------------------------------------------------------------
# TestConsistentRequiresNote
# ---------------------------------------------------------------------------

class TestConsistentRequiresNote:
    def test_consistent_without_note_is_error(self):
        action = _notes_action(ost_reviewed="consistent")
        errors, _ = validate(_plan_with_actions(action), _STORY)
        ost_errors = [e for e in errors if "ost_review_note" in e]
        assert ost_errors, f"Expected ost_review_note error, got: {errors}"

    def test_consistent_with_whitespace_only_note_is_error(self):
        action = _notes_action(ost_reviewed="consistent", ost_review_note="   ")
        errors, _ = validate(_plan_with_actions(action), _STORY)
        ost_errors = [e for e in errors if "ost_review_note" in e]
        assert ost_errors, f"Expected whitespace-only ost_review_note error, got: {errors}"

    def test_consistent_with_nonempty_note_passes(self):
        action = _notes_action(
            ost_reviewed="consistent",
            ost_review_note="Slide already shows the updated spec in the table.",
        )
        errors, _ = validate(_plan_with_actions(action), _STORY)
        ost_errors = [e for e in errors if "ost_review_note" in e]
        assert not ost_errors, f"Unexpected ost_review_note errors: {ost_errors}"


# ---------------------------------------------------------------------------
# TestCompanionActionVerification
# ---------------------------------------------------------------------------

class TestCompanionActionVerification:
    def test_update_existing_companion_passes(self):
        notes = _notes_action(ost_reviewed="companion_action_added")
        companion = _ost_companion(slide_number=5, action_type="update_existing")
        errors, _ = validate(_plan_with_actions(notes, companion), _STORY)
        ost_errors = [e for e in errors if "companion" in e.lower()]
        assert not ost_errors, f"Unexpected companion errors: {ost_errors}"

    def test_fragment_replace_companion_passes(self):
        notes = _notes_action(ost_reviewed="companion_action_added")
        companion = {
            "type": "fragment_replace",
            "slide_number": 5,
            "reason": "fix ost fragment",
            "source_basis": [{"source_id": "SRC-01"}],
            "find_fragment": "old fragment",
            "replace_fragment": "new fragment",
        }
        errors, _ = validate(_plan_with_actions(notes, companion), _STORY)
        ost_errors = [e for e in errors if "companion" in e.lower()]
        assert not ost_errors, f"Unexpected companion errors: {ost_errors}"

    def test_no_companion_is_error(self):
        notes = _notes_action(ost_reviewed="companion_action_added")
        errors, _ = validate(_plan_with_actions(notes), _STORY)
        ost_errors = [e for e in errors if "companion" in e.lower() and "not found" not in e.lower()]
        companion_errors = [e for e in errors if "companion_action_added" in e and "no" in e.lower()]
        assert companion_errors or ost_errors, f"Expected companion-missing error, got: {errors}"

    def test_companion_on_wrong_slide_is_error(self):
        notes = _notes_action(slide_number=5, ost_reviewed="companion_action_added")
        companion = _ost_companion(slide_number=99)
        errors, _ = validate(_plan_with_actions(notes, companion), _STORY)
        companion_errors = [e for e in errors if "companion_action_added" in e and "no" in e.lower()]
        assert companion_errors, f"Expected wrong-slide companion error, got: {errors}"

    def test_notes_update_on_same_slide_does_not_count_as_companion(self):
        notes1 = _notes_action(slide_number=5, ost_reviewed="companion_action_added")
        notes2 = _notes_action(slide_number=5, ost_reviewed="consistent",
                               ost_review_note="OST is fine.")
        errors, _ = validate(_plan_with_actions(notes1, notes2), _STORY)
        companion_errors = [e for e in errors if "companion_action_added" in e and "no" in e.lower()]
        assert companion_errors, f"Second notes_update should not count as OST companion, got: {errors}"

    def test_two_notes_updates_validated_independently(self):
        notes_slide5 = _notes_action(slide_number=5, ost_reviewed="companion_action_added")
        notes_slide7 = _notes_action(slide_number=7, ost_reviewed="companion_action_added")
        companion_slide5 = _ost_companion(slide_number=5)
        errors, _ = validate(_plan_with_actions(notes_slide5, notes_slide7, companion_slide5), _STORY)
        slide7_errors = [e for e in errors if "companion_action_added" in e and "slide 7" in e]
        slide5_errors = [e for e in errors if "companion_action_added" in e and "slide 5" in e]
        assert slide7_errors, f"Expected missing companion error for slide 7, got: {errors}"
        assert not slide5_errors, f"Unexpected companion error for slide 5: {slide5_errors}"


# ---------------------------------------------------------------------------
# TestNonNotesActionsUnaffected
# ---------------------------------------------------------------------------

class TestNonNotesActionsUnaffected:
    def test_update_existing_needs_no_ost_reviewed(self):
        action = {
            "type": "update_existing",
            "slide_number": 3,
            "reason": "fix stale term",
            "source_basis": [{"source_id": "SRC-01"}],
            "match_text": "old text",
            "replacement_text": "new text",
        }
        errors, _ = validate(_plan_with_actions(action), _STORY)
        ost_errors = [e for e in errors if "ost_reviewed" in e]
        assert not ost_errors, f"update_existing should not require ost_reviewed: {ost_errors}"

    def test_fragment_replace_needs_no_ost_reviewed(self):
        action = {
            "type": "fragment_replace",
            "slide_number": 8,
            "reason": "fix fragment",
            "source_basis": [{"source_id": "SRC-01"}],
            "find_fragment": "old text fragment",
            "replace_fragment": "new text fragment",
        }
        errors, _ = validate(_plan_with_actions(action), _STORY)
        ost_errors = [e for e in errors if "ost_reviewed" in e]
        assert not ost_errors, f"fragment_replace should not require ost_reviewed: {ost_errors}"


class TestSpeakerNotesGroundTruth:
    def test_notes_update_requires_old_speaker_notes(self):
        action = _notes_action(
            ost_reviewed="consistent",
            ost_review_note="OST already mentions this.",
        )
        del action["old_speaker_notes"]
        errors, _ = validate(_plan_with_actions(action), _STORY)
        assert any("old_speaker_notes" in e and "required" in e for e in errors)

    def test_notes_change_match_fragment_must_exist_in_old_speaker_notes(self):
        action = _notes_action(
            ost_reviewed="consistent",
            ost_review_note="OST already mentions this.",
            old_speaker_notes="The original paragraph is here.",
            notes_changes=[
                {
                    "match_fragment": "not in the original notes",
                    "replacement_fragment": "replacement text",
                }
            ],
        )
        errors, _ = validate(_plan_with_actions(action), _STORY)
        assert any("match_fragment" in e and "old_speaker_notes" in e for e in errors)
