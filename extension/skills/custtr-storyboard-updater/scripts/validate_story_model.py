#!/usr/bin/env python3
"""Validate LLM-authored story_model.json against deck_extract.json."""

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from constants import EXIT_ERROR, EXIT_OK  # noqa: E402
from json_helpers import safe_load_json  # noqa: E402

VALID_ROLES = {
    "title",
    "objectives",
    "concept_setup",
    "architecture_walkthrough",
    "deep_dive",
    "comparison",
    "recommendation",
    "knowledge_check",
    "summary",
    "boilerplate",
    "blank",
    "transition",
    "example",
    "case_study",
    "lab",
}

VALID_SPECIFICITY = {"generation_specific", "release_specific", "release_agnostic", "unknown"}
VALID_DEPENDENCY = {"none", "low", "medium", "high"}

AUDIT_LANGUAGE = (
    "cleared by src-",
    "src-nabu",
    "src-conf",
    "src-jira",
    "src-web",
    "src-vdoc",
    "source confirms",
    "sources confirm",
    "no changes needed",
    "no findings",
    "no stale terms",
)


def _slide_numbers(deck: dict[str, Any]) -> list[int]:
    return [int(s.get("slide_number")) for s in deck.get("slides") or [] if s.get("slide_number")]


def _slides_by_number(deck: dict[str, Any]) -> dict[int, dict[str, Any]]:
    return {
        int(s.get("slide_number")): s
        for s in deck.get("slides") or []
        if s.get("slide_number")
    }


def _shape_ids(slide: dict[str, Any]) -> set[str]:
    return {
        str(item.get("shape_id"))
        for item in slide.get("texts") or []
        if item.get("shape_id") is not None
    }


def _shape_text(slide: dict[str, Any], shape_id: str) -> str:
    for item in slide.get("texts") or []:
        if str(item.get("shape_id")) == str(shape_id):
            return item.get("text") or ""
    return ""


def _all_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            out.extend(_all_strings(item))
        return out
    if isinstance(value, dict):
        out = []
        for item in value.values():
            out.extend(_all_strings(item))
        return out
    return []


def _has_audit_conclusion(text: str) -> bool:
    low = text.lower()
    return any(marker in low for marker in AUDIT_LANGUAGE)


def _require_string(errors: list[str], label: str, value: Any) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} is required")


def _validate_evidence(
    errors: list[str],
    interp: dict[str, Any],
    slides: dict[int, dict[str, Any]],
) -> None:
    slide_no = interp.get("slide_number")
    evidence = interp.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        errors.append(f"slide {slide_no}: evidence must be a non-empty array")
        return

    for idx, ref in enumerate(evidence):
        if not isinstance(ref, dict):
            errors.append(f"slide {slide_no}: evidence[{idx}] must be an object")
            continue
        ref_slide_no = int(ref.get("slide_number") or slide_no or 0)
        slide = slides.get(ref_slide_no)
        if slide is None:
            errors.append(f"slide {slide_no}: evidence[{idx}] references unknown slide {ref_slide_no}")
            continue

        ref_type = ref.get("type")
        quote = ref.get("quote") or ""
        if ref_type == "shape":
            shape_id = ref.get("shape_id")
            if shape_id is None:
                errors.append(f"slide {slide_no}: evidence[{idx}] missing shape_id")
                continue
            if str(shape_id) not in _shape_ids(slide):
                errors.append(
                    f"slide {slide_no}: evidence[{idx}] references unknown shape_id '{shape_id}'"
                )
                continue
            if quote and quote not in _shape_text(slide, str(shape_id)):
                errors.append(
                    f"slide {slide_no}: evidence[{idx}] quote is not present in shape_id '{shape_id}'"
                )
        elif ref_type == "notes":
            notes = slide.get("notes") or ""
            if quote and quote not in notes:
                errors.append(f"slide {slide_no}: evidence[{idx}] quote is not present in notes")
        else:
            errors.append(f"slide {slide_no}: evidence[{idx}] type must be 'shape' or 'notes'")


def validate(deck: dict[str, Any], story: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Return (errors, warnings) for an LLM-authored story model."""
    errors: list[str] = []
    warnings: list[str] = []

    if story.get("schema_version") != "2.0":
        errors.append("story_model.schema_version must be '2.0'")
    _require_string(errors, "story_model.primary_message", story.get("primary_message"))
    if not story.get("key_talking_points"):
        errors.append("story_model.key_talking_points is required")

    slides = _slides_by_number(deck)
    expected = _slide_numbers(deck)
    interpretations = story.get("slide_interpretations")
    if not isinstance(interpretations, list):
        errors.append("story_model.slide_interpretations must be an array")
        interpretations = []

    seen: list[int] = []
    interpreted_roles: dict[int, str] = {}
    generic_deep_dives = 0
    for interp in interpretations:
        if not isinstance(interp, dict):
            errors.append("slide_interpretations entries must be objects")
            continue
        slide_no = interp.get("slide_number")
        if slide_no not in slides:
            errors.append(f"slide_interpretations references unknown slide: {slide_no}")
            continue
        seen.append(int(slide_no))

        role = interp.get("role")
        if role not in VALID_ROLES:
            errors.append(f"slide {slide_no}: invalid role '{role}'")
        else:
            interpreted_roles[int(slide_no)] = str(role)
        if role == "deep_dive" and not interp.get("role_rationale"):
            generic_deep_dives += 1
        _require_string(errors, f"slide {slide_no}: teaching_purpose", interp.get("teaching_purpose"))
        if interp.get("generation_specificity") not in VALID_SPECIFICITY:
            errors.append(f"slide {slide_no}: invalid generation_specificity")
        if interp.get("visual_dependency") not in VALID_DEPENDENCY:
            errors.append(f"slide {slide_no}: invalid visual_dependency")
        if interp.get("notes_dependency") not in VALID_DEPENDENCY:
            errors.append(f"slide {slide_no}: invalid notes_dependency")
        _validate_evidence(errors, interp, slides)

    missing = sorted(set(expected) - set(seen))
    if missing:
        errors.append(f"missing slide_interpretations rows for slides: {missing}")
    duplicates = sorted({n for n in seen if seen.count(n) > 1})
    if duplicates:
        errors.append(f"duplicate slide_interpretations rows for slides: {duplicates}")

    if expected and generic_deep_dives > max(3, len(expected) // 3):
        warnings.append(
            "many slides use generic 'deep_dive' role without role_rationale; review story specificity"
        )

    for key in ["slide_roles", "knowledge_checks", "summary_slides", "concept_coverage"]:
        if key not in story:
            errors.append(f"story_model.{key} is required for downstream compatibility")

    legacy_roles = story.get("slide_roles")
    if isinstance(legacy_roles, list):
        legacy_map = {
            int(item.get("slide_number")): item.get("role")
            for item in legacy_roles
            if isinstance(item, dict) and item.get("slide_number")
        }
        if interpreted_roles and legacy_map != interpreted_roles:
            errors.append(
                "story_model.slide_roles conflict with slide_interpretations; "
                "update compatibility fields from the LLM-authored rows"
            )

    derived_kc = sorted(
        slide_no for slide_no, role in interpreted_roles.items() if role == "knowledge_check"
    )
    if "knowledge_checks" in story and sorted(story.get("knowledge_checks") or []) != derived_kc:
        errors.append("story_model.knowledge_checks conflict with slide_interpretations")

    derived_summary = sorted(
        slide_no for slide_no, role in interpreted_roles.items() if role == "summary"
    )
    if "summary_slides" in story and sorted(story.get("summary_slides") or []) != derived_summary:
        errors.append("story_model.summary_slides conflict with slide_interpretations")

    for text in _all_strings(story):
        if _has_audit_conclusion(text):
            errors.append(
                "story_model contains source-backed audit conclusion language; reserve source-backed clears/findings for Phase 3"
            )
            break

    objectives = story.get("learning_objectives") or []
    for i, obj in enumerate(objectives):
        if not obj.get("covered_by_slides"):
            warnings.append(f"learning_objectives[{i}] has no covered_by_slides mapping")

    kc_alignment = story.get("knowledge_check_alignment") or []
    kc_slides = story.get("knowledge_checks") or [
        i.get("slide_number") for i in interpretations if i.get("role") == "knowledge_check"
    ]
    aligned_kc = {row.get("slide_number") for row in kc_alignment if isinstance(row, dict)}
    for slide_no in kc_slides:
        if slide_no not in aligned_kc:
            warnings.append(f"knowledge check slide {slide_no} has no knowledge_check_alignment row")

    summary_alignment = story.get("summary_alignment") or []
    summary_slides = story.get("summary_slides") or [
        i.get("slide_number") for i in interpretations if i.get("role") == "summary"
    ]
    aligned_summary = {row.get("slide_number") for row in summary_alignment if isinstance(row, dict)}
    for slide_no in summary_slides:
        if slide_no not in aligned_summary:
            warnings.append(f"summary slide {slide_no} has no summary_alignment row")

    return errors, warnings


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--deck-extract", required=True, help="Path to deck_extract.json")
    ap.add_argument("--story-model", required=True, help="Path to story_model.json")
    args = ap.parse_args(argv)

    deck = safe_load_json(args.deck_extract, "deck_extract.json")
    story = safe_load_json(args.story_model, "story_model.json")
    errors, warnings = validate(deck, story)

    for warning in warnings:
        print(f"  WARNING: {warning}")
    for error in errors:
        print(f"  ERROR: {error}")

    if errors:
        print(f"\nStory model validation FAILED with {len(errors)} error(s)")
        return EXIT_ERROR
    print(f"\nStory model validation PASSED ({len(warnings)} warning(s))")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
