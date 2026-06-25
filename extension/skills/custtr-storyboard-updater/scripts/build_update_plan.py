#!/usr/bin/env python3
"""Legacy draft-plan scaffold helper.

The primary workflow is LLM-authored plan creation from verified findings. This
script can still produce a conservative scaffold for diagnostics or migration,
but its output is not authoritative and actions marked requires_human_authored_text
must be completed by the LLM before execution.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from json_helpers import safe_load_json, try_load_json  # noqa: E402


def load_json(path, default):
    if not path:
        return default
    p = Path(path)
    if not p.exists():
        return default
    return safe_load_json(p, p.name)


def verification_rows(path):
    doc = load_json(path, None)
    if doc is None:
        return []
    if isinstance(doc, list):
        return doc
    return doc.get("slides") or doc.get("verification_rows") or []


def finding_id(slide_no, index, finding):
    return str(finding.get("id") or finding.get("finding_id") or f"S{slide_no}-F{index + 1:02d}")


def verification_actions(rows):
    """Create draft plan actions from claim-verification findings.

    These actions are intentionally conservative. If a finding lacks exact
    current/proposed text, the action is marked requires_human_authored_text so
    execute mode blocks until the plan author completes it.
    """
    actions = []
    for row in rows:
        slide_no = row.get("slide_number")
        if not slide_no:
            continue
        for index, finding in enumerate(row.get("findings") or []):
            if finding.get("action_required", True) is False:
                continue
            fid = finding_id(slide_no, index, finding)
            source_id = finding.get("source_id")
            source_basis = [source_id] if source_id else []
            ftype = finding.get("type", "")
            recommended = finding.get("recommended_action_type") or ""
            location = (finding.get("location") or "").lower()

            if ftype == "new_slide_candidate" or recommended == "add_new_slide":
                required = [
                    "concept",
                    "why_existing_slide_update_is_insufficient",
                    "insert_after_slide",
                    "learning_goal",
                    "visual_intent",
                    "qa_expectations",
                ]
                missing = [k for k in required if not finding.get(k)]
                actions.append({
                    "type": "add_new_slide",
                    "title": finding.get("title") or finding.get("concept") or "Source-Backed Addition",
                    "insert_after_slide": finding.get("insert_after_slide") or slide_no,
                    "reason": finding.get("why_existing_slide_update_is_insufficient") or finding.get("reason") or "Claim verification identified a required concept that is not adequately taught.",
                    "instructional_reason": finding.get("instructional_reason") or "A source-backed concept changes the learning story and cannot be handled cleanly as a small existing-slide edit.",
                    "learning_goal": finding.get("learning_goal") or "",
                    "why_this_slide_exists": finding.get("why_existing_slide_update_is_insufficient") or "",
                    "what_customer_should_understand": finding.get("what_customer_should_understand") or "",
                    "visible_content_summary": finding.get("visible_content_summary") or finding.get("visual_intent") or "",
                    "visual_approach": finding.get("visual_approach") or finding.get("visual_intent") or "",
                    "qa_expectations": finding.get("qa_expectations") or [],
                    "speaker_notes": finding.get("speaker_notes") or "",
                    "source_basis": source_basis,
                    "verification_ids": [fid],
                    "visual_intent": finding.get("visual_intent") or "",
                    "flow_dependencies": finding.get("flow_dependencies") or {},
                    "requires_human_authored_text": bool(missing or not finding.get("speaker_notes")),
                    "marking": "new_slide_visual_qa",
                    "acceptance_criteria": [
                        "New slide maps to a verification finding",
                        "Slide has a source-backed learning goal",
                        "Rendered slide has no cutoffs or overlaps and matches the deck visual flow",
                        "Slide updates affected objectives, checks, or summary when applicable",
                    ],
                })
                continue

            if "notes" in location or recommended == "notes_update":
                match = finding.get("current_text") or ""
                repl = finding.get("proposed_text") or ""
                actions.append({
                    "type": "notes_update",
                    "slide_number": slide_no,
                    "reason": finding.get("reason") or f"Resolve verification finding {fid}.",
                    "source_basis": source_basis,
                    "verification_ids": [fid],
                    "notes_changes": [{"match_fragment": match, "replacement_fragment": repl}] if match and repl else [],
                    "requires_human_authored_text": not (match and repl),
                    "marking": "existing_edit",
                })
                continue

            atype = "knowledge_check_update" if ftype == "knowledge_check_invalid" or recommended == "knowledge_check_update" else "update_existing"
            match = finding.get("current_text") or ""
            repl = finding.get("proposed_text") or ""
            actions.append({
                "type": atype,
                "slide_number": slide_no,
                "reason": finding.get("reason") or f"Resolve verification finding {fid}.",
                "instructional_reason": finding.get("instructional_reason") or "Claim verification found content that is unsupported, contradicted, incomplete, or inconsistent.",
                "source_basis": source_basis,
                "verification_ids": [fid],
                "match_text": match,
                "replacement_text": repl,
                "requires_human_authored_text": not (match and repl),
                "marking": "existing_edit",
                "acceptance_criteria": ["Finding is resolved in OST and notes parity is preserved"],
            })
    return actions


def story_roles(story):
    interpretations = story.get("slide_interpretations") or []
    if interpretations:
        return [
            {
                "slide_number": item.get("slide_number"),
                "title": item.get("title", ""),
                "role": item.get("role", ""),
            }
            for item in interpretations
            if item.get("slide_number")
        ]
    return story.get("slide_roles") or []


def first_slide_by_role(story, role):
    for item in story_roles(story):
        if item.get("role") == role:
            return item.get("slide_number")
    return None


def slides_by_role(story, role):
    return [item["slide_number"] for item in story_roles(story) if item.get("role") == role]


def knowledge_check_slides(story):
    if story.get("slide_interpretations"):
        return slides_by_role(story, "knowledge_check")
    return story.get("knowledge_checks") or slides_by_role(story, "knowledge_check")


def hygiene_actions(deck, target_version):
    actions = []
    if target_version:
        for s in deck["slides"]:
            for item in s["texts"]:
                if item["text"].strip().startswith("202") and item["text"].strip() != target_version:
                    actions.append({
                        "type": "update_existing",
                        "slide_number": s["slide_number"],
                        "reason": "Update visible deck version label.",
                        "instructional_reason": "Version label must match the target release before learners or reviewers interpret the deck.",
                        "source_basis": ["user target version"],
                        "match_text": item["text"],
                        "replacement_text": target_version,
                        "marking": "existing_edit",
                        "acceptance_criteria": ["Version label matches target version"],
                    })
                    return actions
    return actions


def trailing_blank_action(deck):
    # The trailing slide is always preserved — it carries the AMD logo for legal/compliance.
    return []


def source_delta_actions(deltas, story):
    actions = []
    objectives_slide = first_slide_by_role(story, "objectives")
    summary_slides = slides_by_role(story, "summary")
    checks = knowledge_check_slides(story)
    deep_dive_slides = [
        item["slide_number"]
        for item in story_roles(story)
        if item.get("role") in {
            "deep_dive",
            "concept_setup",
            "architecture_walkthrough",
            "comparison",
            "recommendation",
            "example",
            "case_study",
            "lab",
        }
    ]

    for delta in deltas:
        concept = delta.get("concept") or delta.get("title") or "new concept"
        impact = delta.get("instructional_impact", "major")
        if impact not in {"major", "moderate"}:
            continue
        source_basis = delta.get("source_basis", [])
        insert_after = delta.get("insert_after_slide") or (deep_dive_slides[-1] if deep_dive_slides else 1)
        actions.append({
            "type": "add_new_slide",
            "title": delta.get("title", f"Understanding {concept}"),
            "insert_after_slide": insert_after,
            "reason": delta.get("reason", f"Add source-backed instructional coverage for {concept}."),
            "instructional_reason": delta.get(
                "instructional_reason",
                f"{concept} changes what learners need to understand, so it must be taught in the narrative flow rather than appended as an isolated feature slide.",
            ),
            "learning_goal": delta.get("learning_goal", f"Explain what {concept} is, why it matters, and what value it brings."),
            "why_this_slide_exists": delta.get("why_this_slide_exists", f"Provide context and customer motivation for {concept}."),
            "what_customer_should_understand": delta.get(
                "what_customer_should_understand",
                f"Customers should understand the purpose, problem solved, and enabled use cases for {concept}.",
            ),
            "cards": delta.get("cards", []),
            "visual_spec": delta.get("visual_spec", {
                "type": "concept_or_architecture_diagram",
                "required": True,
                "description": f"Show how {concept} fits into the system architecture and what customer problem it addresses.",
            }),
            "speaker_notes": delta.get("speaker_notes", ""),
            "source_basis": source_basis,
            "marking": "new_slide_badge",
            "connects_from_slide": insert_after,
            "connects_to_slide": insert_after + 1,
            "acceptance_criteria": [
                "Slide explains what the technology is",
                "Slide explains why it exists",
                "Slide explains customer value or enabled use cases",
                "Slide includes a visual or explicit diagram placeholder",
                "Speaker notes provide full narration",
            ],
        })

        if objectives_slide:
            actions.append({
                "type": "update_existing",
                "slide_number": objectives_slide,
                "reason": f"Objective coverage must reflect new required concept: {concept}.",
                "instructional_reason": "New major concepts must be represented in learner objectives or explicitly scoped as supplemental.",
                "source_basis": source_basis,
                "dependency_of": concept,
                "requires_human_authored_text": True,
                "marking": "existing_edit",
                "acceptance_criteria": ["Objectives include or intentionally exclude the new concept with rationale"],
            })
        for slide in summary_slides:
            actions.append({
                "type": "update_existing",
                "slide_number": slide,
                "reason": f"Summary must reflect the updated learning story for {concept}.",
                "instructional_reason": "The summary should reinforce the deck’s final takeaways, including newly taught major concepts.",
                "source_basis": source_basis,
                "dependency_of": concept,
                "requires_human_authored_text": True,
                "marking": "existing_edit",
                "acceptance_criteria": ["Summary includes the customer value and impact of the new concept"],
            })
        if checks:
            target_check = next((c for c in checks if c > insert_after), checks[-1])
            actions.append({
                "type": "knowledge_check_update",
                "slide_number": target_check,
                "reason": f"Knowledge check should assess the newly taught concept: {concept}.",
                "instructional_reason": "Assessments must test the updated learning objectives and not only pre-existing content.",
                "source_basis": source_basis,
                "dependency_of": concept,
                "requires_human_authored_text": True,
                "marking": "existing_edit",
                "acceptance_criteria": ["Knowledge check reinforces why/what/value, not only feature recall"],
            })
    return actions


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deck-extract", required=True)
    ap.add_argument("--story-model", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--target-version", default="")
    ap.add_argument("--focus", default="")
    ap.add_argument("--source-deltas")
    ap.add_argument("--verification-report")
    args = ap.parse_args()

    deck = safe_load_json(args.deck_extract, "deck_extract.json")
    story = safe_load_json(args.story_model, "story_model.json")
    delta_doc = load_json(args.source_deltas, {"source_deltas": []})
    deltas = delta_doc.get("source_deltas", [])
    rows = verification_rows(args.verification_report)

    actions = []
    actions.extend(hygiene_actions(deck, args.target_version))
    actions.extend(trailing_blank_action(deck))
    actions.extend(verification_actions(rows))
    actions.extend(source_delta_actions(deltas, story))

    dependency_updates = [
        a for a in actions
        if a.get("dependency_of") or a.get("type") in {"knowledge_check_update", "notes_update"}
    ]
    flow_status = "requires_source_augmented_review"
    if deltas and all(not a.get("requires_human_authored_text") for a in dependency_updates):
        flow_status = "pass"

    plan = {
        "schema_version": "2.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "deck": deck["deck"],
        "target_version": args.target_version,
        "focus": [p.strip() for p in args.focus.split(",") if p.strip()],
        "approval_required": True,
        "status": "draft_requires_user_approval",
        "advisory_scaffold": True,
        "llm_authoring_required": any(a.get("requires_human_authored_text") for a in actions),
        "story_model": story,
        "source_deltas": deltas,
        "verification_report": args.verification_report or "",
        "dependency_updates": dependency_updates,
        "flow_validation": {
            "status": flow_status,
            "checks": [
                "primary message identified",
                "objectives reviewed against new concepts",
                "body flow reviewed against source deltas",
                "knowledge checks reviewed",
                "summary reviewed",
            ],
        },
        "instructional_design_notes": [
            "Do not add keyword-triggered slides without objective/body/assessment/summary dependency checks.",
            "New slides must be instructionally designed with what/why/value/use-case narrative and visual support.",
            "Actions requiring human-authored text must be completed before execute mode.",
        ],
        "actions": actions,
        "source_inventory": delta_doc.get("source_inventory", []),
    }
    Path(args.output).write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
