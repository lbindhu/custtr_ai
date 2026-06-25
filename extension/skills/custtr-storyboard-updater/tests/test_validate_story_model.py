"""Tests for LLM-authored story_model.json validation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from validate_story_model import validate  # noqa: E402


_DECK = {
    "deck": "deck.pptx",
    "slide_count": 2,
    "slides": [
        {
            "slide_number": 1,
            "title": "Objectives",
            "texts": [
                {"shape_id": "10", "text": "Objectives", "placeholder_type": "title"},
                {"shape_id": "11", "text": "Describe the memory controller.", "placeholder_type": "body"},
            ],
            "notes": "Instructor notes for objectives.",
        },
        {
            "slide_number": 2,
            "title": "Architecture",
            "texts": [
                {"shape_id": "20", "text": "Architecture", "placeholder_type": "title"},
                {"shape_id": "21", "text": "DDR5 controller connects to NoC.", "placeholder_type": "body"},
            ],
            "notes": "Instructor notes for architecture.",
        },
    ],
}


def _valid_model():
    return {
        "schema_version": "2.0",
        "deck_identity": {
            "title": "Memory Controller Training",
            "target_version": "2026.1",
            "audience": "AMD customer training learners",
            "module_scope": "Memory controller architecture",
        },
        "primary_message": "Teach customers how the memory controller fits into the system architecture.",
        "key_talking_points": ["memory controller", "DDR5", "NoC"],
        "slide_interpretations": [
            {
                "slide_number": 1,
                "role": "objectives",
                "teaching_purpose": "State the learning objectives for the module.",
                "core_claims": ["Learners will describe the memory controller."],
                "concepts_introduced": ["memory controller"],
                "concepts_reinforced": [],
                "generation_specificity": "release_agnostic",
                "visual_dependency": "low",
                "notes_dependency": "medium",
                "evidence": [
                    {"type": "shape", "slide_number": 1, "shape_id": "11", "quote": "Describe the memory controller."}
                ],
            },
            {
                "slide_number": 2,
                "role": "architecture_walkthrough",
                "teaching_purpose": "Explain the controller-to-NoC architecture relationship.",
                "core_claims": ["The DDR5 controller connects to the NoC."],
                "concepts_introduced": ["DDR5 controller", "NoC"],
                "concepts_reinforced": ["memory controller"],
                "generation_specificity": "generation_specific",
                "visual_dependency": "high",
                "notes_dependency": "medium",
                "evidence": [
                    {"type": "shape", "slide_number": 2, "shape_id": "21", "quote": "DDR5 controller connects to NoC."}
                ],
            },
        ],
        "learning_objectives": [
            {
                "objective": "Describe the memory controller.",
                "source_slide": 1,
                "covered_by_slides": [2],
                "assessed_by_slides": [],
            }
        ],
        "concept_flow": [
            {"concept": "memory controller", "introduced_on": 1, "reinforced_on": [2], "depends_on": []}
        ],
        "knowledge_check_alignment": [],
        "summary_alignment": [],
        "source_research_hypotheses": [
            {
                "query": "Memory controller architecture 2026.1",
                "why": "Validate controller and NoC claims in the architecture section.",
                "target_sources": ["NABU", "Vivado docs"],
            }
        ],
        "stale_terms_candidates": [
            {
                "token": "DDR5",
                "reason": "Protocol and controller claims should be checked against target sources.",
                "slides": [2],
            }
        ],
        "slide_roles": [
            {"slide_number": 1, "title": "Objectives", "role": "objectives"},
            {"slide_number": 2, "title": "Architecture", "role": "architecture_walkthrough"},
        ],
        "knowledge_checks": [],
        "summary_slides": [],
        "concept_coverage": [
            {"concept": "memory controller", "covered_on": [2], "assessed_on": []}
        ],
    }


def test_valid_llm_story_model_passes():
    errors, warnings = validate(_DECK, _valid_model())
    assert errors == []
    assert not any("missing slide" in w.lower() for w in warnings)


def test_missing_slide_interpretation_is_error():
    model = _valid_model()
    model["slide_interpretations"] = model["slide_interpretations"][:1]
    errors, _ = validate(_DECK, model)
    assert "missing slide_interpretations rows for slides: [2]" in errors


def test_bad_shape_evidence_is_error():
    model = _valid_model()
    model["slide_interpretations"][1]["evidence"][0]["shape_id"] = "999"
    errors, _ = validate(_DECK, model)
    assert any("unknown shape_id '999'" in e for e in errors)


def test_source_backed_audit_language_is_rejected():
    model = _valid_model()
    model["slide_interpretations"][1]["core_claims"] = [
        "Slide is cleared by SRC-NABU-01 and no changes are needed."
    ]
    errors, _ = validate(_DECK, model)
    assert any("source-backed audit conclusion" in e for e in errors)


def test_missing_compatibility_fields_are_errors():
    model = _valid_model()
    for key in ["slide_roles", "knowledge_checks", "summary_slides", "concept_coverage"]:
        model.pop(key)

    errors, _ = validate(_DECK, model)

    assert "story_model.slide_roles is required for downstream compatibility" in errors
    assert "story_model.knowledge_checks is required for downstream compatibility" in errors
    assert "story_model.summary_slides is required for downstream compatibility" in errors
    assert "story_model.concept_coverage is required for downstream compatibility" in errors


def test_conflicting_slide_roles_are_errors():
    model = _valid_model()
    model["slide_roles"][1]["role"] = "summary"

    errors, _ = validate(_DECK, model)

    assert any("slide_roles conflict with slide_interpretations" in e for e in errors)
