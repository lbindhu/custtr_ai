"""Tests for build_update_plan.py consuming v2 story models."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from build_update_plan import source_delta_actions  # noqa: E402


def test_source_delta_dependencies_derive_from_slide_interpretations():
    story = {
        "schema_version": "2.0",
        "slide_interpretations": [
            {"slide_number": 1, "role": "title", "title": "Title"},
            {"slide_number": 2, "role": "objectives", "title": "Objectives"},
            {"slide_number": 3, "role": "architecture_walkthrough", "title": "Architecture"},
            {"slide_number": 4, "role": "knowledge_check", "title": "Apply Your Knowledge"},
            {"slide_number": 5, "role": "summary", "title": "Summary"},
        ],
    }
    deltas = [
        {
            "concept": "CPM6 architecture",
            "instructional_impact": "major",
            "source_basis": ["SRC-NABU-01"],
            "insert_after_slide": 3,
        }
    ]

    actions = source_delta_actions(deltas, story)
    action_types = [a["type"] for a in actions]
    locations = {(a["type"], a.get("slide_number")) for a in actions}

    assert "add_new_slide" in action_types
    assert ("update_existing", 2) in locations
    assert ("knowledge_check_update", 4) in locations
    assert ("update_existing", 5) in locations


def test_slide_interpretations_take_precedence_over_stale_legacy_roles():
    story = {
        "schema_version": "2.0",
        "slide_interpretations": [
            {"slide_number": 1, "role": "title", "title": "Title"},
            {"slide_number": 2, "role": "objectives", "title": "Objectives"},
            {"slide_number": 3, "role": "architecture_walkthrough", "title": "Architecture"},
            {"slide_number": 4, "role": "knowledge_check", "title": "Apply Your Knowledge"},
            {"slide_number": 5, "role": "summary", "title": "Summary"},
        ],
        "slide_roles": [
            {"slide_number": 9, "role": "objectives", "title": "Stale Objectives"},
            {"slide_number": 10, "role": "summary", "title": "Stale Summary"},
        ],
        "knowledge_checks": [11],
    }
    deltas = [
        {
            "concept": "CPM6 architecture",
            "instructional_impact": "major",
            "source_basis": ["SRC-NABU-01"],
            "insert_after_slide": 3,
        }
    ]

    actions = source_delta_actions(deltas, story)
    locations = {(a["type"], a.get("slide_number")) for a in actions}

    assert ("update_existing", 2) in locations
    assert ("knowledge_check_update", 4) in locations
    assert ("update_existing", 5) in locations
    assert ("update_existing", 9) not in locations
    assert ("knowledge_check_update", 11) not in locations
