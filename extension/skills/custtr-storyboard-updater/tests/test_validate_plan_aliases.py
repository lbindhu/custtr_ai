"""Tests for field-name alias detection in validate_plan.py."""
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


def _plan_with_action(action: dict) -> dict:
    return {**_BASE_PLAN, "actions": [action]}


def _clean_action(**extra) -> dict:
    return {
        "type": "update_existing",
        "slide_number": 3,
        "reason": "test",
        "source_basis": ["SRC-01"],
        "match_text": "old",
        "replacement_text": "new",
        **extra,
    }


def test_slide_alias_detected():
    action = _clean_action()
    del action["slide_number"]
    action["slide"] = 3
    errors, _ = validate(_plan_with_action(action), _STORY)
    alias_errors = [e for e in errors if "rename it" in e and "'slide'" in e and "slide_number" in e]
    assert alias_errors, f"Expected alias error for 'slide', got: {errors}"


def test_action_type_alias_detected():
    action = _clean_action()
    action["action_type"] = "update_existing"
    errors, _ = validate(_plan_with_action(action), _STORY)
    alias_errors = [e for e in errors if "action_type" in e and "'type'" in e]
    assert alias_errors, f"Expected alias error for 'action_type', got: {errors}"
    assert "rename it" in alias_errors[0]


def test_finding_id_alias_detected():
    action = _clean_action()
    action["finding_id"] = "F-01"
    errors, _ = validate(_plan_with_action(action), _STORY)
    alias_errors = [e for e in errors if "finding_id" in e and "finding_ids" in e]
    assert alias_errors, f"Expected alias error for 'finding_id', got: {errors}"
    assert "rename it" in alias_errors[0]


def test_match_alias_detected():
    action = _clean_action()
    action["match"] = "some text"
    errors, _ = validate(_plan_with_action(action), _STORY)
    alias_errors = [e for e in errors if "'match'" in e and "match_text" in e]
    assert alias_errors, f"Expected alias error for 'match', got: {errors}"
    assert "rename it" in alias_errors[0]


def test_add_new_slide_speaker_notes_not_flagged():
    action = {
        "type": "add_new_slide",
        "insert_after_slide": 5,
        "reason": "new content",
        "source_basis": ["SRC-01"],
        "title": "Takeaway",
        "learning_goal": "Learn X",
        "why_this_slide_exists": "gap",
        "what_customer_should_understand": "Y",
        "visible_content_summary": "A concise visual takeaway slide.",
        "visual_approach": "Match the nearby summary slide style and verify the rendered slide.",
        "speaker_notes": "These are the notes.",
        "qa_expectations": ["No cutoffs", "Matches deck visual flow"],
        "verification_ids": ["V-01"],
    }
    errors, _ = validate(_plan_with_action(action), _STORY)
    alias_errors = [e for e in errors if "speaker_notes" in e and "rename it" in e]
    assert not alias_errors, f"speaker_notes should be valid on add_new_slide, got: {alias_errors}"


def test_clean_action_no_alias_errors():
    action = _clean_action()
    errors, _ = validate(_plan_with_action(action), _STORY)
    alias_errors = [e for e in errors if "rename it" in e]
    assert not alias_errors, f"Unexpected alias errors on clean action: {alias_errors}"
