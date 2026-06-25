"""Tests for the B-009 notes diff-soup advisory guard in validate_plan.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from validate_plan import validate  # noqa: E402

_STORY = {"primary_message": "msg", "key_talking_points": ["pt1"]}

_LONG_OLD = (
    "CPM5 supports PCIe Gen 5 at 32 GT/s across the integrated block for PCI "
    "Express, providing root complex and endpoint configurations for the "
    "Versal Premium device family in production designs today."
)


def _plan(match_fragment, replacement_fragment):
    return {
        "schema_version": "2.0",
        "deck": "t.pptx",
        "target_version": "2026.1",
        "status": "approved",
        "actions": [{
            "type": "notes_update",
            "slide_number": 5,
            "reason": "update notes",
            "source_basis": [{"source_id": "SRC-01"}],
            "ost_reviewed": "consistent",
            "ost_review_note": "OST already mentions Gen 6",
            "old_speaker_notes": _LONG_OLD,
            "notes_changes": [{
                "match_fragment": match_fragment,
                "replacement_fragment": replacement_fragment,
            }],
        }],
    }


def test_long_dissimilar_rewrite_warns():
    # A whole long sentence rewritten into something dissimilar → soup risk.
    match = _LONG_OLD
    replacement = (
        "An entirely different paragraph about DDR5 memory controllers, ECC "
        "handling, refresh management, and bandwidth tuning unrelated text."
    )
    errors, warnings = validate(_plan(match, replacement), _STORY)
    assert any("soup" in w.lower() for w in warnings)
    # It is advisory only — must not be a hard error.
    assert not any("soup" in e.lower() for e in errors)


def test_short_anchor_additive_not_warned():
    # Preferred pattern: short anchor, additive sentence — must NOT warn.
    match = "production designs today."
    replacement = (
        "production designs today. CPM6 adds PCIe Gen 6 at 64 GT/s for the "
        "Gen 2 family."
    )
    errors, warnings = validate(_plan(match, replacement), _STORY)
    assert not any("soup" in w.lower() for w in warnings)


def test_small_inline_fix_not_warned():
    match = "PCIe Gen 5 at 32 GT/s"
    replacement = "PCIe Gen 6 at 64 GT/s"
    errors, warnings = validate(_plan(match, replacement), _STORY)
    assert not any("soup" in w.lower() for w in warnings)
