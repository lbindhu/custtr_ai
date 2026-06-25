#!/usr/bin/env python3
"""Validate update_plan.json against the v2.0 schema before execution."""

import argparse
import difflib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from json_helpers import safe_load_json  # noqa: E402
from constants import (  # noqa: E402
    EXIT_ERROR,
    EXIT_OK,
    VALID_ACTION_TYPES,
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
        "title", "learning_goal",
        "why_this_slide_exists", "what_customer_should_understand",
        "visible_content_summary", "visual_approach", "speaker_notes",
        "qa_expectations",
    ],
    "knowledge_check_update": ["match_text", "replacement_text"],
    # notes_update must carry notes_changes for existing slides.
    "notes_update": [],
}

VALID_OST_REVIEWED_VALUES = {"consistent", "companion_action_added"}
OST_COMPANION_TYPES = {"update_existing", "fragment_replace"}

# Notes diff-soup guard (B-009): a LONG match_fragment rewritten into a
# dissimilar replacement produces an unreadable character-level diff. The
# preferred "short anchor + additive sentence" pattern has a short match and is
# intentionally NOT flagged.
_NOTES_SOUP_MATCH_LEN = 120
_NOTES_SOUP_SIMILARITY = 0.5


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
                if not action.get(field):
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
            qa = action.get("qa_expectations")
            if qa is not None and not isinstance(qa, list):
                errors.append(f"{prefix} (add_new_slide): 'qa_expectations' must be a list")

        if atype in {"notes_update", "update_existing", "knowledge_check_update"} and action.get("speaker_notes"):
            errors.append(
                f"{prefix} ({atype}): speaker_notes is forbidden for existing slides; "
                "use notes_changes with verbatim match_fragment/replacement_fragment"
            )

        if atype == "notes_update" and not action.get("notes_changes"):
            errors.append(f"{prefix} (notes_update): requires notes_changes")
        if atype == "notes_update":
            old_notes = action.get("old_speaker_notes")
            if not isinstance(old_notes, str) or not old_notes:
                errors.append(
                    f"{prefix} (notes_update): old_speaker_notes is required and "
                    "must be the verbatim original notes text"
                )

        for j, change in enumerate(action.get("notes_changes") or []):
            if not change.get("match_fragment") or not change.get("replacement_fragment"):
                errors.append(
                    f"{prefix}: notes_changes[{j}] requires non-empty match_fragment and replacement_fragment"
                )
            elif atype == "notes_update":
                old_notes = action.get("old_speaker_notes") or ""
                match_fragment = change.get("match_fragment") or ""
                if match_fragment not in old_notes:
                    errors.append(
                        f"{prefix}: notes_changes[{j}].match_fragment is not a "
                        "verbatim substring of old_speaker_notes"
                    )

            # Diff-soup advisory (B-009): rewriting a long fragment into a
            # dissimilar replacement corrupts the notes pane into unreadable
            # interleaved runs. Prefer a short anchor + additive sentence.
            mf = change.get("match_fragment") or ""
            rf = change.get("replacement_fragment") or ""
            if mf and rf and len(mf) >= _NOTES_SOUP_MATCH_LEN:
                ratio = difflib.SequenceMatcher(None, mf, rf).ratio()
                if ratio < _NOTES_SOUP_SIMILARITY:
                    warnings.append(
                        f"{prefix}: notes_changes[{j}] rewrites a long "
                        f"match_fragment ({len(mf)} chars) into a dissimilar "
                        f"replacement (similarity {ratio:.2f}); this often "
                        "produces unreadable char-diff 'soup'. Prefer a short "
                        "anchor + additive sentence, or split into smaller "
                        "high-similarity fragments (B-009)."
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
