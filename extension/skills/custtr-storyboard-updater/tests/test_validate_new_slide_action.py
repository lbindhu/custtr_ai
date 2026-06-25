"""Tests for the LLM-led add_new_slide plan contract."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from validate_plan import validate

_STORY = {"primary_message": "msg", "key_talking_points": ["pt1"]}

_BASE_PLAN = {
    "schema_version": "2.0",
    "deck": "test.pptx",
    "target_version": "2026.1",
    "status": "approved",
}

def _action(**overrides):
    base = {
        "type": "add_new_slide",
        "insert_after_slide": 5,
        "reason": "new content",
        "source_basis": ["SRC-01"],
        "finding_ids": ["NS-01"],
        "title": "Test Slide",
        "learning_goal": "Understand X",
        "why_this_slide_exists": "Parity gap",
        "what_customer_should_understand": "Key takeaway",
        "visible_content_summary": "A diagram-style teaching slide showing the new concept in context.",
        "visual_approach": "Reuse the nearest architecture-slide visual system and verify rendered text does not overlap or cut off.",
        "speaker_notes": " ".join(["word"] * 85),
        "qa_expectations": [
            "Rendered slide has no text cutoffs or overlaps.",
            "Slide visually matches neighboring training slides.",
        ],
    }
    base.update(overrides)
    return base

def _validate_action(action):
    return validate({**_BASE_PLAN, "actions": [action]}, _STORY)


def test_llm_led_add_new_slide_without_layout_passes():
    errors, warnings = _validate_action(_action())
    assert errors == []
    assert warnings == []


def test_layout_specific_fields_are_not_required():
    action = _action()
    for field in ("cards", "table", "diagram", "ascii_art", "columns", "statement"):
        action.pop(field, None)
    errors, _ = _validate_action(action)
    assert errors == []


def test_arbitrary_visual_approach_is_allowed():
    errors, _ = _validate_action(_action(
        visual_approach="Duplicate a nearby slide, replace visual groups manually, and run image-based QA.",
    ))
    assert errors == []


def test_missing_visual_approach_is_rejected():
    errors, _ = _validate_action(_action(visual_approach=""))
    assert any("visual_approach" in e for e in errors)


def test_missing_visible_content_summary_is_rejected():
    errors, _ = _validate_action(_action(visible_content_summary=""))
    assert any("visible_content_summary" in e for e in errors)


def test_missing_qa_expectations_is_rejected():
    errors, _ = _validate_action(_action(qa_expectations=[]))
    assert any("qa_expectations" in e for e in errors)


def test_body_field_is_allowed_as_llm_visible_content_if_summary_present():
    errors, _ = _validate_action(_action(body="LLM-authored draft body; final deck must still pass XML/package QA."))
    assert errors == []
