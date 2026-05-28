#!/usr/bin/env python3
"""Claim-verification audit gate.

This gate replaces legacy token-list scanning. It refuses execution unless every slide
has a source-backed verification row and every required finding maps to an
approved plan action or an explicit source-backed clear.

Required inputs in <work_dir>:
  - deck_extract.json
  - source_inventory.json
  - reference_extract.json
  - verification_report.json
  - cross_validation_report.json
  - update_plan.json or update_plan_final.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from json_helpers import try_load_json  # noqa: E402
from constants import (  # noqa: E402
    BANNED_OPENERS,
    DATASHEET_BULLET_RE,
    DATASHEET_HEADINGS,
    DIAGRAM_ONLY_LAYOUTS,
    EXIT_ERROR,
    EXIT_FATAL,
    EXIT_OK,
    KNOWLEDGE_RE,
    LAYOUT_DATA_FIELDS,
    MARP_ELIGIBLE_LAYOUTS,
    MUTATING_ACTIONS,
    SUMMARY_RE,
    VALID_SLIDE_LAYOUTS,
    VERSION_RE,
)


PASSIVE_CLEAR_PHRASES = [
    "no stale terms",
    "content is still valid",
    "scan is clean",
    "no findings",
    "content looks correct",
    "no changes needed",
    "still accurate",
    "nothing to update",
    "all clear",
    "no issues found",
]


def load(path: Path) -> Any | None:
    return try_load_json(path)


def as_rows(report: Any) -> list[dict]:
    if isinstance(report, list):
        return report
    if isinstance(report, dict):
        return report.get("slides") or report.get("verification_rows") or []
    return []


def slide_title(slide: dict) -> str:
    for sh in slide.get("texts") or []:
        if (sh.get("placeholder_type") or "").lower() in {"title", "ctrtitle"}:
            return sh.get("text") or ""
    return slide.get("title") or ""


def slide_text(slide: dict) -> str:
    parts = [sh.get("text") or "" for sh in slide.get("texts") or []]
    parts.append(slide.get("notes") or "")
    return "\n".join(parts)


def is_boilerplate(slide: dict) -> bool:
    title = slide_title(slide).lower()
    if slide.get("is_blank"):
        return True
    return any(k in title for k in ("disclaimer", "attribution", "thank you", "legal"))


def has_banned_opener(text: str) -> str | None:
    head = (text or "").strip().lower()[:120]
    for opener in BANNED_OPENERS:
        if head.startswith(opener):
            return opener
    return None


def source_inventory_entries(src: dict | None) -> list[dict]:
    if not isinstance(src, dict):
        return []
    entries = src.get("queries") or src.get("entries") or src.get("sources") or []
    return entries if isinstance(entries, list) else []


def reference_entries(ref: dict | None) -> list[dict]:
    if isinstance(ref, list):
        return ref
    if not isinstance(ref, dict):
        return []
    entries = ref.get("entries") or ref.get("sources") or ref.get("chunks") or []
    return entries if isinstance(entries, list) else []


def gather_corpus(ref: dict | None, extra_paths: list[str]) -> tuple[str, set[str]]:
    blobs: list[str] = []
    source_ids: set[str] = set()

    for entry in reference_entries(ref):
        sid = entry.get("source_id") or entry.get("id")
        if sid:
            source_ids.add(str(sid))
        for key in ("text", "body", "content", "summary", "excerpt", "title"):
            value = entry.get(key)
            if isinstance(value, str):
                blobs.append(value)
            elif isinstance(value, list):
                blobs.extend(str(v) for v in value)

    for raw in extra_paths:
        path = Path(raw)
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        items = data if isinstance(data, list) else data.get("chunks", [data])
        for item in items:
            if not isinstance(item, dict):
                continue
            sid = item.get("source_id") or item.get("id")
            if sid:
                source_ids.add(str(sid))
            blobs.append(str(item.get("text") or item.get("body") or item.get("content") or ""))

    return "\n".join(blobs).lower(), source_ids


def source_id_of(item: dict) -> str:
    sid = item.get("source_id")
    if isinstance(sid, list):
        return str(sid[0]) if sid else ""
    return str(sid or "")


def quote_of(item: dict) -> str:
    return str(item.get("quoted_source") or item.get("source_quote") or "").strip()


def finding_id(slide_no: int, index: int, finding: dict) -> str:
    return str(finding.get("id") or finding.get("finding_id") or f"S{slide_no}-F{index + 1:02d}")


def action_ids(action: dict) -> set[str]:
    ids: set[str] = set()
    for key in ("verification_ids", "finding_ids", "addresses_findings"):
        value = action.get(key)
        if isinstance(value, str):
            ids.add(value)
        elif isinstance(value, list):
            ids.update(str(v) for v in value)
    return ids


def action_source_tokens(action: dict) -> set[str]:
    out: set[str] = set()
    value = action.get("source_basis") or action.get("audit_basis") or []
    if isinstance(value, str):
        out.add(value)
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, str):
                out.add(item)
            elif isinstance(item, dict):
                for key in ("source_id", "id", "url", "section"):
                    if item.get(key):
                        out.add(str(item[key]))
    elif isinstance(value, dict):
        for key in ("source_id", "id", "url", "section"):
            if value.get(key):
                out.add(str(value[key]))
    return out


def cleared_findings(xval: dict | None) -> dict[str, dict]:
    if not isinstance(xval, dict):
        return {}
    rows = []
    rows.extend(xval.get("findings_cleared") or [])
    rows.extend(xval.get("cleared_findings") or [])
    out = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        fid = row.get("finding_id") or row.get("id")
        if fid:
            out[str(fid)] = row
    return out


def slide_clear_evidence(xval: dict | None, slide_no: int) -> dict | None:
    if not isinstance(xval, dict):
        return None
    for bucket in ("cleared_with_evidence", "slides_explicitly_cleared"):
        for row in xval.get(bucket) or []:
            if not isinstance(row, dict):
                continue
            if int(row.get("slide") or row.get("slide_number") or -1) == int(slide_no):
                return row
    return None


def notes_structure_issues(plan: dict) -> list[str]:
    issues = []
    for i, action in enumerate(plan.get("actions") or []):
        atype = action.get("type")
        if atype not in {"notes_update", "update_existing", "knowledge_check_update"}:
            continue
        if action.get("speaker_notes"):
            issues.append(
                f"action #{i} on slide {action.get('slide_number')} uses speaker_notes on an existing slide; "
                "use notes_changes with verbatim match_fragment/replacement_fragment instead"
            )
        for j, change in enumerate(action.get("notes_changes") or []):
            if not change.get("match_fragment") or not change.get("replacement_fragment"):
                issues.append(
                    f"action #{i} notes_changes[{j}] on slide {action.get('slide_number')} "
                    "requires non-empty match_fragment and replacement_fragment"
                )
    return issues


def run_structural_checks(
    deck: dict,
    src: dict,
    ref: dict,
    verification_doc: Any,
    xval: dict,
    coverage: dict | None,
    corpus_paths: list[str],
    *,
    require_sources: bool = False,
    require_coverage: bool = False,
) -> tuple[list[str], list[str], list[dict], dict[int, dict], str, set[str]]:
    """Validate artifact completeness, row coverage, source inventory, and corpus.

    Returns (errors, warnings, slides, rows_by_slide, corpus_blob, known_source_ids).
    """
    errors: list[str] = []
    warnings: list[str] = []

    slides = deck.get("slides") or []
    expected_slides = {int(s.get("slide_number")) for s in slides if s.get("slide_number")}
    rows = as_rows(verification_doc)
    rows_by_slide = {int(r.get("slide_number")): r for r in rows if r.get("slide_number") is not None}
    missing = sorted(expected_slides - set(rows_by_slide))
    extra = sorted(set(rows_by_slide) - expected_slides)
    if missing:
        errors.append(f"verification_report missing slide rows: {missing}")
    if extra:
        errors.append(f"verification_report has rows for unknown slides: {extra}")

    examined = set(xval.get("slides_examined") or []) if isinstance(xval, dict) else set()
    if not examined:
        errors.append("cross_validation_report missing slides_examined")
    elif {int(s) for s in examined} != expected_slides:
        errors.append(
            f"cross_validation_report slides_examined != deck slides; "
            f"missing {sorted(expected_slides - {int(s) for s in examined})}"
        )

    entries = source_inventory_entries(src)
    if require_sources:
        n_nabu = sum(1 for e in entries if "nabu" in (str(e.get("server", "")) + str(e.get("source", ""))).lower())
        n_conf = sum(1 for e in entries if "confl" in (str(e.get("server", "")) + str(e.get("source", ""))).lower())
        n_jira = sum(1 for e in entries if "jira" in (str(e.get("server", "")) + str(e.get("source", ""))).lower())
        if n_nabu < 3:
            errors.append(f"source_inventory: NABU queries {n_nabu} < 3")
        if n_conf < 1:
            errors.append(f"source_inventory: Confluence queries {n_conf} < 1")
        if n_jira < 1:
            errors.append(f"source_inventory: JIRA queries {n_jira} < 1")

    if require_coverage:
        if coverage is None:
            errors.append("missing required artifact: coverage_gaps.json")
        elif coverage.get("slides_with_gaps"):
            for gap in (coverage.get("slides_with_gaps") or [])[:10]:
                errors.append(
                    f"slide {gap.get('slide_number')} has uncovered claims: "
                    f"{gap.get('uncovered_claims', [])[:5]}"
                )

    corpus_blob, known_source_ids = gather_corpus(ref, corpus_paths)
    inventory_ids = {
        str(e.get("source_id") or e.get("id"))
        for e in entries
        if e.get("source_id") or e.get("id")
    }
    known_source_ids |= inventory_ids
    if not corpus_blob.strip():
        errors.append("reference_extract.json contains no source text; claim verification cannot be audited")

    return errors, warnings, slides, rows_by_slide, corpus_blob, known_source_ids


def run_verification_sweep(
    slides: list[dict],
    rows_by_slide: dict[int, dict],
    xval: dict,
    plan: dict,
    corpus_blob: str,
    known_source_ids: set[str],
    *,
    require_source_ids: bool = True,
) -> tuple[list[str], list[str], int, set[str]]:
    """Per-slide claim/finding verification.

    Returns (errors, warnings, unresolved_findings, new_slide_candidate_ids).
    """
    errors: list[str] = []
    warnings: list[str] = []

    actions = plan.get("actions") or []
    actions_by_id: dict[str, list[dict]] = {}
    for action in actions:
        for fid in action_ids(action):
            actions_by_id.setdefault(fid, []).append(action)

    clears = cleared_findings(xval)
    unresolved_findings = 0
    new_slide_candidate_ids: set[str] = set()

    for slide in slides:
        slide_no = int(slide.get("slide_number"))
        row = rows_by_slide.get(slide_no)
        if not row:
            continue

        if row.get("additional_sources_needed"):
            errors.append(f"slide {slide_no}: additional_sources_needed is not empty")
        for q in row.get("open_questions") or []:
            if q.get("blocks_finalization"):
                errors.append(f"slide {slide_no}: blocking open question: {str(q.get('question', ''))[:160]}")

        claims = row.get("claims_verified") or []
        findings = row.get("findings") or []
        clear = slide_clear_evidence(xval, slide_no)
        if not claims and not findings and not is_boilerplate(slide):
            if not clear or (require_source_ids and not clear.get("source_ids")):
                errors.append(
                    f"slide {slide_no}: no claims/findings and no source-backed clear; "
                    "verification cannot prove the slide was reviewed"
                )

        for bucket_name, bucket in (("claims_verified", claims), ("findings", findings)):
            for i, item in enumerate(bucket):
                sid = source_id_of(item)
                quote = quote_of(item)
                if not sid:
                    errors.append(f"slide {slide_no} {bucket_name}[{i}]: missing source_id")
                elif known_source_ids and sid not in known_source_ids:
                    warnings.append(f"slide {slide_no} {bucket_name}[{i}]: source_id {sid!r} not listed in source inventory/reference extract")
                if not quote:
                    errors.append(f"slide {slide_no} {bucket_name}[{i}]: missing quoted_source")
                elif len(quote) < 30:
                    errors.append(f"slide {slide_no} {bucket_name}[{i}]: quoted_source shorter than 30 chars")
                elif corpus_blob and quote.lower() not in corpus_blob:
                    errors.append(f"slide {slide_no} {bucket_name}[{i}]: quoted_source is not a literal substring of reference_extract")

        for i, finding in enumerate(findings):
            fid = finding_id(slide_no, i, finding)
            ftype = str(finding.get("type") or "")
            recommended = str(finding.get("recommended_action_type") or "")
            action_required = finding.get("action_required", True)
            if ftype == "new_slide_candidate" or recommended == "add_new_slide":
                new_slide_candidate_ids.add(fid)
                required_candidate_fields = [
                    "concept",
                    "why_existing_slide_update_is_insufficient",
                    "insert_after_slide",
                    "learning_goal",
                    "flow_dependencies",
                    "recommended_layout",
                    "visual_intent",
                ]
                missing_candidate = [k for k in required_candidate_fields if not finding.get(k)]
                if missing_candidate:
                    errors.append(f"finding {fid}: new_slide_candidate missing {missing_candidate}")
            if not action_required:
                continue
            matched_actions = actions_by_id.get(fid, [])
            clear_row = clears.get(fid)
            if not matched_actions and not clear_row:
                unresolved_findings += 1
                errors.append(f"finding {fid} on slide {slide_no} is not addressed by a plan action or explicit clear")
                continue
            if clear_row:
                if not clear_row.get("reason"):
                    errors.append(f"finding {fid}: clear has no reason")
                if require_source_ids and not clear_row.get("source_ids"):
                    errors.append(f"finding {fid}: clear has no source_ids")
            for action in matched_actions:
                action_sources = action_source_tokens(action)
                sid = source_id_of(finding)
                if sid and not any(sid in token for token in action_sources):
                    errors.append(f"finding {fid}: mapped action lacks source_basis containing {sid}")

        title = slide_title(slide)
        if SUMMARY_RE.search(title) and not (row.get("summary_review") or findings):
            errors.append(f"summary slide {slide_no}: verification row missing summary_review or findings")
        if KNOWLEDGE_RE.search(title) and not (row.get("knowledge_check_review") or findings):
            errors.append(f"knowledge-check slide {slide_no}: verification row missing knowledge_check_review or findings")

    return errors, warnings, unresolved_findings, new_slide_candidate_ids


def run_new_slide_sweep(
    actions: list[dict],
    new_slide_candidate_ids: set[str],
) -> tuple[list[str], list[str]]:
    """Validate add_new_slide actions: required fields, layout schema, card quality."""
    errors: list[str] = []
    warnings: list[str] = []

    add_actions = [a for a in actions if a.get("type") == "add_new_slide"]
    for i, action in enumerate(add_actions):
        ids = action_ids(action)
        if not (ids & new_slide_candidate_ids):
            errors.append(f"add_new_slide action #{i} is not tied to a new_slide_candidate finding via verification_ids/finding_ids")
        required_fields = [
            "insert_after_slide",
            "slide_layout",
            "title",
            "learning_goal",
            "why_this_slide_exists",
            "what_customer_should_understand",
            "speaker_notes",
            "source_basis",
        ]
        missing_fields = [k for k in required_fields if not action.get(k)]
        if missing_fields:
            errors.append(f"add_new_slide action #{i} missing required fields: {missing_fields}")

        sl = action.get("slide_layout") or ""
        atitle = action.get("title") or f"<add_new_slide #{i}>"

        if sl and sl not in VALID_SLIDE_LAYOUTS:
            errors.append(
                f"add_new_slide '{atitle}': invalid slide_layout '{sl}'; "
                f"must be one of {sorted(VALID_SLIDE_LAYOUTS)}"
            )
        if sl in LAYOUT_DATA_FIELDS:
            data_field = LAYOUT_DATA_FIELDS[sl]
            if not action.get(data_field):
                errors.append(
                    f"add_new_slide '{atitle}': layout '{sl}' requires "
                    f"non-empty '{data_field}' field"
                )
        if action.get("body"):
            errors.append(
                f"add_new_slide '{atitle}': 'body' is not a valid field; "
                f"use the layout-specific data field (cards, table, columns, "
                f"diagram, ascii_art, statement)"
            )

        if sl == "cards":
            card_list = action.get("cards") or []
            for ci, card in enumerate(card_list):
                heading = (card.get("heading") or "").strip().lower()
                if heading in DATASHEET_HEADINGS:
                    errors.append(
                        f"add_new_slide '{atitle}': cards[{ci}] heading "
                        f"'{card.get('heading')}' is a generic datasheet heading; "
                        f"use domain-specific headings"
                    )
                for bi, bullet in enumerate(card.get("bullets") or []):
                    if isinstance(bullet, str) and DATASHEET_BULLET_RE.match(bullet):
                        warnings.append(
                            f"add_new_slide '{atitle}': cards[{ci}].bullets[{bi}] "
                            f"looks like a datasheet definition (\"Term: description\"); "
                            f"training bullets should include comparison, condition, "
                            f"consequence, or metric"
                        )

    return errors, warnings


def run_action_quality_sweep(
    plan: dict,
    *,
    require_source_basis: bool = True,
    strict_notes: bool = True,
) -> list[str]:
    """Source-basis, banned-opener, and notes-structure checks on all actions."""
    errors: list[str] = []
    actions = plan.get("actions") or []

    if require_source_basis:
        for i, action in enumerate(actions):
            if action.get("type") not in MUTATING_ACTIONS:
                continue
            if not action.get("source_basis") and not action.get("audit_basis"):
                errors.append(f"action #{i} ({action.get('type')}) missing source_basis/audit_basis")

    if strict_notes:
        for i, action in enumerate(actions):
            for key in ("speaker_notes",):
                opener = has_banned_opener(action.get(key) or "")
                if opener:
                    errors.append(f"action #{i} speaker_notes starts with banned opener: {opener!r}")

    errors.extend(notes_structure_issues(plan))
    return errors


def run_version_sweep(
    slides: list[dict],
    plan: dict,
    xval: dict,
) -> tuple[list[str], list[str]]:
    """Scan all slides for non-target version tokens."""
    errors: list[str] = []
    warnings: list[str] = []

    target_version = plan.get("target_version") or ""
    version_exceptions = {
        (str(v.get("token")), int(v.get("slide")))
        for v in (xval.get("version_exceptions") or [])
        if isinstance(v, dict) and v.get("token") and v.get("slide")
    }
    if target_version:
        for slide in slides:
            slide_no = int(slide.get("slide_number"))
            for m in VERSION_RE.finditer(slide_text(slide)):
                tok = m.group(0)
                if tok == target_version:
                    continue
                if (tok, slide_no) in version_exceptions:
                    warnings.append(f"slide {slide_no}: keeps version token {tok} by version_exceptions")
                    continue
                if slide_no == 1:
                    errors.append(f"title slide contains non-target version token {tok}; expected {target_version}")
                else:
                    errors.append(f"slide {slide_no} contains non-target version token {tok}; add version_exceptions if intentional")

    return errors, warnings


def _has_passive_phrase(text: str) -> str | None:
    low = (text or "").lower()
    for phrase in PASSIVE_CLEAR_PHRASES:
        if phrase in low:
            return phrase
    return None


def run_generational_analysis_sweep(xval: dict) -> list[str]:
    """Validate that every slides_explicitly_cleared entry has a substantive generational_analysis."""
    errors: list[str] = []
    if not isinstance(xval, dict):
        return errors
    for bucket in ("cleared_with_evidence", "slides_explicitly_cleared"):
        for row in xval.get(bucket) or []:
            if not isinstance(row, dict):
                continue
            slide_no = row.get("slide") or row.get("slide_number") or "?"
            reason = row.get("reason") or ""
            passive = _has_passive_phrase(reason)
            if passive:
                errors.append(
                    f"slide {slide_no}: cleared with passive phrase '{passive}' in reason — "
                    f"Rule 38 requires substantive generational analysis"
                )
            ga = row.get("generational_analysis")
            if not isinstance(ga, dict):
                errors.append(
                    f"slide {slide_no}: slides_explicitly_cleared entry missing required "
                    f"'generational_analysis' object (Rule 38)"
                )
                continue
            cg = ga.get("content_generation") or ""
            tgc = ga.get("target_generation_changes") or ""
            wni = ga.get("why_no_impact") or ""
            if len(cg) < 10:
                errors.append(
                    f"slide {slide_no}: generational_analysis.content_generation "
                    f"too short ({len(cg)} chars, min 10)"
                )
            if len(tgc) < 20:
                errors.append(
                    f"slide {slide_no}: generational_analysis.target_generation_changes "
                    f"too short ({len(tgc)} chars, min 20)"
                )
            if len(wni) < 30:
                errors.append(
                    f"slide {slide_no}: generational_analysis.why_no_impact "
                    f"too short ({len(wni)} chars, min 30)"
                )
            passive_wni = _has_passive_phrase(wni)
            if passive_wni:
                errors.append(
                    f"slide {slide_no}: generational_analysis.why_no_impact uses passive phrase "
                    f"'{passive_wni}' — explain specifically why changes don't affect this slide"
                )
    return errors


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--work-dir", required=True)
    ap.add_argument("--corpus", nargs="*", default=[], help="Additional corpus JSON chunks used for verification.")
    ap.add_argument("--require-sources", action="store_true", help="Require >=3 NABU, >=1 Confluence, >=1 JIRA source entries.")
    ap.add_argument("--require-coverage", action="store_true", help="Require coverage_gaps.json to exist and contain zero gaps.")
    ap.add_argument("--require-source-basis", action="store_true", default=True, help="Require source_basis/audit_basis on every mutating action.")
    ap.add_argument("--require-source-ids", action="store_true", default=True, help="Require source_ids on slide/finding clears.")
    ap.add_argument("--strict-notes", action="store_true", default=True, help="Reject speaker notes with banned narrator openers.")
    args = ap.parse_args(argv)

    wd = Path(args.work_dir)
    deck = load(wd / "deck_extract.json")
    src = load(wd / "source_inventory.json")
    ref = load(wd / "reference_extract.json")
    verification_doc = load(wd / "verification_report.json")
    xval = load(wd / "cross_validation_report.json")
    plan = load(wd / "update_plan_final.json") or load(wd / "update_plan.json")
    coverage = load(wd / "coverage_gaps.json")

    errors: list[str] = []
    warnings: list[str] = []

    required = {
        "deck_extract.json": deck,
        "source_inventory.json": src,
        "reference_extract.json": ref,
        "verification_report.json": verification_doc,
        "cross_validation_report.json": xval,
        "update_plan.json": plan,
    }
    for name, obj in required.items():
        if obj is None:
            errors.append(f"missing required artifact: {name}")
    # Hint: if verification_report.json is absent but slide_rows/ sidecars exist,
    # the LLM likely wrote per-slide files and needs to merge them first.
    if verification_doc is None and (wd / "slide_rows").exists():
        warnings.append(
            "verification_report.json missing but slide_rows/ sidecars found; "
            "run merge_slide_rows.py to assemble it before re-running audit_gate."
        )
    if errors:
        print(json.dumps({"errors": errors, "warnings": warnings}, indent=2))
        return EXIT_FATAL

    # concept_decomposition.json gate — must be present before verification can advance
    concept_decomp_path = wd / "concept_decomposition.json"
    if not concept_decomp_path.exists():
        print(json.dumps({
            "errors": [
                "concept_decomposition.json not found in work dir. "
                "Complete Phase 3 concept decomposition before running audit_gate. "
                "See references/artifact_schemas.md for schema."
            ],
            "warnings": [],
        }, indent=2))
        return EXIT_FATAL
    concept_decomp = load(concept_decomp_path) or {}

    # Warn for concepts marked adequate=false with recommended_action=add_new_slide
    # that have no matching add_new_slide action in the plan (soft check — title matching is fuzzy).
    plan_add_titles = {
        (a.get("title") or "").lower()
        for a in (plan.get("actions") or [])
        if a.get("type") == "add_new_slide"
    }
    for delta in (concept_decomp.get("source_deltas") or []):
        for tc in (delta.get("teachable_concepts") or []):
            if not tc.get("adequate") and tc.get("recommended_action") == "add_new_slide":
                cname = (tc.get("concept") or "").lower()
                if not any(cname in title for title in plan_add_titles):
                    warnings.append(
                        f"concept '{tc.get('concept')}' (delta {delta.get('delta_id')}) "
                        f"marked add_new_slide but no matching add_new_slide action found in plan"
                    )

    # Parity matrix warnings — non-fatal; inform about structural coverage gaps
    parity_path = wd / "parity_matrix.json"
    if parity_path.exists():
        parity = load(parity_path) or {}
        for candidate in (parity.get("new_slide_candidates") or []):
            variant = candidate.get("variant") or "<unknown>"
            reason = candidate.get("reason") or ""
            warnings.append(
                f"parity matrix: variant '{variant}' has no dedicated slides — {reason}. "
                "Consider an add_new_slide action."
            )

    # Structural checks: row coverage, source inventory, corpus
    s_err, s_warn, slides, rows_by_slide, corpus_blob, known_source_ids = run_structural_checks(
        deck, src, ref, verification_doc, xval, coverage, args.corpus,
        require_sources=args.require_sources,
        require_coverage=args.require_coverage,
    )
    errors.extend(s_err)
    warnings.extend(s_warn)

    # Per-slide verification
    v_err, v_warn, unresolved_findings, new_slide_candidate_ids = run_verification_sweep(
        slides, rows_by_slide, xval, plan, corpus_blob, known_source_ids,
        require_source_ids=args.require_source_ids,
    )
    errors.extend(v_err)
    warnings.extend(v_warn)

    # New-slide schema validation
    actions = plan.get("actions") or []
    ns_err, ns_warn = run_new_slide_sweep(actions, new_slide_candidate_ids)
    errors.extend(ns_err)
    warnings.extend(ns_warn)

    # Action quality: source-basis, banned openers, notes structure
    errors.extend(run_action_quality_sweep(
        plan,
        require_source_basis=args.require_source_basis,
        strict_notes=args.strict_notes,
    ))

    # Version sweep
    ver_err, ver_warn = run_version_sweep(slides, plan, xval)
    errors.extend(ver_err)
    warnings.extend(ver_warn)

    # Generational analysis sweep (Rule 38)
    errors.extend(run_generational_analysis_sweep(xval))

    # OST-review cross-reference warning:
    # If a notes_update action claims ost_reviewed="consistent" but the Phase 3 finding it
    # references recommended an OST-level action, warn the author to re-examine.
    findings_index: dict[str, dict] = {}
    for slide_row in as_rows(verification_doc):
        for f in (slide_row.get("findings") or []):
            if isinstance(f, dict):
                fid = str(f.get("id") or f.get("finding_id") or "")
                if fid:
                    findings_index[fid] = f
    # Also include cross_validation_report slides_with_findings entries
    if isinstance(xval, dict):
        for slide_row in (xval.get("slides_with_findings") or []):
            for f in (slide_row.get("findings") or []):
                if isinstance(f, dict):
                    fid = str(f.get("id") or f.get("finding_id") or "")
                    if fid:
                        findings_index.setdefault(fid, f)
    notes_only_recommended = {"notes_update", "notes_gap", ""}
    for i, action in enumerate(actions):
        if action.get("type") != "notes_update":
            continue
        if action.get("ost_reviewed") != "consistent":
            continue
        for fid in action_ids(action):
            finding = findings_index.get(fid)
            if not finding:
                continue
            rec = str(finding.get("recommended_action_type") or "")
            if rec and rec not in notes_only_recommended:
                warnings.append(
                    f"action #{i} (notes_update, slide {action.get('slide_number')}): "
                    f"ost_reviewed is 'consistent' but finding {fid} was originally typed as "
                    f"recommended_action_type='{rec}' — verify OST does not need changing "
                    f"before marking it consistent"
                )

    rows = as_rows(verification_doc)
    report = {
        "passed": not errors,
        "errors": errors,
        "warnings": warnings,
        "totals": {
            "slides_expected": len({int(s.get("slide_number")) for s in slides if s.get("slide_number")}),
            "slides_verified": len(rows_by_slide),
            "claims_verified": sum(len((r.get("claims_verified") or [])) for r in rows),
            "findings": sum(len((r.get("findings") or [])) for r in rows),
            "unresolved_findings": unresolved_findings,
            "plan_actions": len(actions),
            "new_slide_candidates": len(new_slide_candidate_ids),
        },
    }
    (wd / "audit_gate_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return EXIT_ERROR if errors else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
