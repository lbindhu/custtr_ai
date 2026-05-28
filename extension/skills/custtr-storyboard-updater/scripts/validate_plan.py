#!/usr/bin/env python3
"""Validate update_plan.json against the v2.0 schema before execution."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from json_helpers import safe_load_json  # noqa: E402
from constants import (  # noqa: E402
    DIAGRAM_ONLY_LAYOUTS,
    EXIT_ERROR,
    EXIT_OK,
    LAYOUT_DATA_FIELDS,
    MARP_ELIGIBLE_LAYOUTS,
    VALID_ACTION_TYPES,
    VALID_SLIDE_LAYOUTS,
)

REQUIRED_TOP_LEVEL = ["schema_version", "deck", "target_version", "status", "actions"]

# Known wrong field names the LLM commonly uses — mapped to the correct name.
_FIELD_ALIASES: dict[str, str] = {
    "slide": "slide_number",
    "action_type": "type",
    "finding_id": "finding_ids",
    "old_text": "match_text",
    "new_text": "replacement_text",
    "match": "match_text",
    "replacement": "replacement_text",
    "find": "find_fragment",
    "search": "find_fragment",
    "replace": "replace_fragment",
    "notes": "notes_changes",
    "speaker_notes": "notes_changes",  # wrong on notes_update; valid on add_new_slide
    "old": "match_fragment",
    "new": "replacement_fragment",
}

TYPE_REQUIRED_FIELDS = {
    # apply_existing_updates.py uses find_fragment/replace_fragment, no shape_id needed
    "fragment_replace": ["find_fragment", "replace_fragment"],
    # apply_existing_updates.py matches by match_text, not shape_id
    "update_existing": ["match_text", "replacement_text"],
    "add_new_slide": [
        "slide_layout", "title", "learning_goal",
        "why_this_slide_exists", "what_customer_should_understand", "speaker_notes",
    ],
    # notes_update must carry notes_changes for existing slides.
    "notes_update": [],
}

VALID_OST_REVIEWED_VALUES = {"consistent", "companion_action_added"}
OST_COMPANION_TYPES = {"update_existing", "fragment_replace"}


def validate(plan: dict, story: dict) -> tuple[list[str], list[str]]:
    errors = []
    warnings = []

    for key in REQUIRED_TOP_LEVEL:
        if key not in plan:
            errors.append(f"Missing required top-level key: '{key}'")

    if plan.get("status") != "approved":
        warnings.append(f"Plan status is '{plan.get('status')}', expected 'approved'")

    actions = plan.get("actions", [])
    if not actions:
        warnings.append("Plan has no actions")

    for i, action in enumerate(actions):
        prefix = f"Action {i+1}"
        atype = action.get("type")

        # add_new_slide uses insert_after_slide; all other types use slide_number
        location_field = "insert_after_slide" if atype == "add_new_slide" else "slide_number"
        for req in ["type", location_field, "reason", "source_basis"]:
            if req not in action:
                errors.append(f"{prefix}: missing required field '{req}'")

        if atype and atype not in VALID_ACTION_TYPES:
            errors.append(f"{prefix}: invalid type '{atype}' — must be one of {sorted(VALID_ACTION_TYPES)}")

        sb = action.get("source_basis")
        if isinstance(sb, list) and len(sb) == 0:
            errors.append(f"{prefix}: 'source_basis' is empty — every action must cite at least one source")

        if atype in TYPE_REQUIRED_FIELDS:
            for field in TYPE_REQUIRED_FIELDS[atype]:
                if field not in action:
                    errors.append(f"{prefix} ({atype}): missing required field '{field}'")

        # Alias detection — catch wrong field names and tell the LLM exactly what to rename.
        for wrong_name, correct_name in _FIELD_ALIASES.items():
            if wrong_name == "speaker_notes" and atype == "add_new_slide":
                continue  # speaker_notes is a valid required field on add_new_slide
            if wrong_name in action:
                errors.append(
                    f"{prefix}: field '{wrong_name}' should be '{correct_name}' "
                    f"(rename it — do not add a second field)"
                )

        if atype == "add_new_slide":
            sl = action.get("slide_layout")
            if sl and sl not in VALID_SLIDE_LAYOUTS:
                errors.append(
                    f"{prefix} (add_new_slide): invalid slide_layout '{sl}' — "
                    f"must be one of {sorted(VALID_SLIDE_LAYOUTS)}"
                )
            if sl in LAYOUT_DATA_FIELDS:
                data_field = LAYOUT_DATA_FIELDS[sl]
                if not action.get(data_field):
                    errors.append(
                        f"{prefix} (add_new_slide): layout '{sl}' requires "
                        f"non-empty '{data_field}' field"
                    )
            if action.get("body"):
                errors.append(
                    f"{prefix} (add_new_slide): 'body' is not a valid field; "
                    f"use the layout-specific data field (cards, table, columns, "
                    f"diagram, ascii_art, statement)"
                )

        if atype in {"notes_update", "update_existing", "knowledge_check_update"} and action.get("speaker_notes"):
            errors.append(
                f"{prefix} ({atype}): speaker_notes is forbidden for existing slides; "
                "use notes_changes with verbatim match_fragment/replacement_fragment"
            )

        if atype == "notes_update" and not action.get("notes_changes"):
            errors.append(f"{prefix} (notes_update): requires notes_changes")

        for j, change in enumerate(action.get("notes_changes") or []):
            if not change.get("match_fragment") or not change.get("replacement_fragment"):
                errors.append(
                    f"{prefix}: notes_changes[{j}] requires non-empty match_fragment and replacement_fragment"
                )

        if atype == "notes_update":
            ost_reviewed = action.get("ost_reviewed")
            if ost_reviewed is None:
                errors.append(
                    f"{prefix} (notes_update): missing required field 'ost_reviewed' — "
                    "must be 'consistent' or 'companion_action_added'"
                )
            elif ost_reviewed not in VALID_OST_REVIEWED_VALUES:
                errors.append(
                    f"{prefix} (notes_update): 'ost_reviewed' value '{ost_reviewed}' is invalid — "
                    f"must be one of {sorted(VALID_OST_REVIEWED_VALUES)}"
                )
            elif ost_reviewed == "consistent":
                note = action.get("ost_review_note")
                if not note or not isinstance(note, str) or not note.strip():
                    errors.append(
                        f"{prefix} (notes_update): 'ost_reviewed' is 'consistent' but "
                        "'ost_review_note' is missing or empty — provide a brief rationale"
                    )
            elif ost_reviewed == "companion_action_added":
                slide_no = action.get("slide_number")
                if slide_no is not None:
                    companion_found = any(
                        a is not action
                        and a.get("type") in OST_COMPANION_TYPES
                        and a.get("slide_number") == slide_no
                        for a in actions
                    )
                    if not companion_found:
                        errors.append(
                            f"{prefix} (notes_update): 'ost_reviewed' is 'companion_action_added' "
                            f"but no 'update_existing' or 'fragment_replace' action targeting "
                            f"slide {slide_no} was found in the plan"
                        )

        if atype == "add_new_slide" and sl in MARP_ELIGIBLE_LAYOUTS:
            if not action.get("speaker_notes"):
                warnings.append(
                    f"{prefix} (add_new_slide): MARP-eligible layout '{sl}' has no "
                    f"speaker_notes; notes will be empty in the exported PPTX"
                )

        if atype == "add_new_slide" and not (action.get("verification_ids") or action.get("finding_ids")):
            errors.append(f"{prefix} (add_new_slide): must reference a new_slide_candidate via verification_ids/finding_ids")

    if not story.get("primary_message"):
        errors.append("story_model.primary_message is missing or empty")
    if not story.get("key_talking_points"):
        errors.append("story_model.key_talking_points is missing or empty")

    return errors, warnings


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plan", required=True, help="Path to update_plan.json")
    ap.add_argument("--story-model", required=True, help="Path to story_model.json")
    args = ap.parse_args()

    plan_path = Path(args.plan)
    sm_path = Path(args.story_model)

    plan = safe_load_json(plan_path, "update_plan.json")
    story = safe_load_json(sm_path, "story_model.json")

    errors, warnings = validate(plan, story)

    for w in warnings:
        print(f"  WARNING: {w}")
    for e in errors:
        print(f"  ERROR: {e}")

    if errors:
        print(f"\nPlan validation FAILED with {len(errors)} error(s)")
        sys.exit(EXIT_ERROR)
    else:
        print(f"\nPlan validation PASSED ({len(warnings)} warning(s))")
        sys.exit(EXIT_OK)


if __name__ == "__main__":
    main()
