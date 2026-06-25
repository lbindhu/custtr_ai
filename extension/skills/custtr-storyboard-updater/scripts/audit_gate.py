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
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_plan import validate as validate_plan_schema  # noqa: E402
from json_helpers import try_load_json  # noqa: E402
from constants import (  # noqa: E402
    BANNED_OPENERS,
    EXIT_ERROR,
    EXIT_FATAL,
    EXIT_OK,
    KNOWLEDGE_RE,
    MUTATING_ACTIONS,
    SUMMARY_RE,
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

CLAIM_DISPOSITIONS = frozenset({"supported", "contradicted", "insufficient", "out_of_scope"})
LINT_SIGNAL_DISPOSITIONS = frozenset({
    "confirmed_finding", "rejected_lint", "intentionally_kept", "out_of_scope",
})
LINT_DERIVED_FINDING_TYPES = frozenset({
    "stale_token", "content_gap", "notes_gap", "delta_trace_hit",
    "intra_slide_inconsistency", "scope_consistency", "new_slide_candidate",
})

SRC_ID_RE = re.compile(r"SRC-[A-Z0-9-]+", re.IGNORECASE)


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


def _source_kind(entry: dict) -> str:
    return " ".join(
        str(entry.get(k, ""))
        for k in ("server", "source", "source_type", "kind", "tool", "name")
    ).lower()


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
        if not entries:
            errors.append(
                "source_inventory: no source entries recorded; source coverage "
                "must be documented before claim verification can be audited"
            )
        for i, entry in enumerate(entries):
            if not (entry.get("source_id") or entry.get("id")):
                errors.append(f"source_inventory entry {i}: missing source_id/id")
        kinds = {_source_kind(e) for e in entries}
        if kinds and not any(k.strip() for k in kinds):
            warnings.append(
                "source_inventory entries do not identify source channels; "
                "coverage can still pass through cited reference_extract evidence"
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
    require_finding_actions: bool = True,
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
                if bucket_name == "claims_verified":
                    disp = str(item.get("claim_disposition") or "").lower()
                    if not disp:
                        errors.append(
                            f"slide {slide_no} claims_verified[{i}]: missing claim_disposition "
                            f"(supported|contradicted|insufficient|out_of_scope)"
                        )
                    elif disp not in CLAIM_DISPOSITIONS:
                        errors.append(
                            f"slide {slide_no} claims_verified[{i}]: invalid claim_disposition {disp!r}"
                        )
                    entail = str(item.get("source_entailment") or "")
                    if len(entail.strip()) < 20:
                        errors.append(
                            f"slide {slide_no} claims_verified[{i}]: source_entailment "
                            f"required (min 20 chars)"
                        )
                    elif len(entail.strip()) < 40:
                        warnings.append(
                            f"slide {slide_no} claims_verified[{i}]: source_entailment is short "
                            f"({len(entail.strip())} chars); prefer >=40 for substantive entailment"
                        )
                if bucket_name == "findings":
                    ftype = str(item.get("type") or "").lower()
                    if ftype in LINT_DERIVED_FINDING_TYPES:
                        lint_disp = str(item.get("lint_signal_disposition") or "").lower()
                        if not lint_disp:
                            errors.append(
                                f"slide {slide_no} findings[{i}]: lint-derived finding type "
                                f"{ftype!r} requires lint_signal_disposition"
                            )
                        elif lint_disp not in LINT_SIGNAL_DISPOSITIONS:
                            errors.append(
                                f"slide {slide_no} findings[{i}]: invalid lint_signal_disposition "
                                f"{lint_disp!r}"
                            )
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
                    "visual_intent",
                    "qa_expectations",
                ]
                missing_candidate = [k for k in required_candidate_fields if not finding.get(k)]
                if missing_candidate:
                    errors.append(f"finding {fid}: new_slide_candidate missing {missing_candidate}")
            if not action_required:
                continue
            if not require_finding_actions:
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
    """Validate add_new_slide actions without imposing a renderer or layout schema."""
    errors: list[str] = []
    warnings: list[str] = []

    add_actions = [a for a in actions if a.get("type") == "add_new_slide"]
    for i, action in enumerate(add_actions):
        ids = action_ids(action)
        if not (ids & new_slide_candidate_ids):
            errors.append(f"add_new_slide action #{i} is not tied to a new_slide_candidate finding via verification_ids/finding_ids")
        required_fields = [
            "insert_after_slide",
            "title",
            "learning_goal",
            "why_this_slide_exists",
            "what_customer_should_understand",
            "visible_content_summary",
            "visual_approach",
            "speaker_notes",
            "source_basis",
            "qa_expectations",
        ]
        missing_fields = [k for k in required_fields if not action.get(k)]
        if missing_fields:
            errors.append(f"add_new_slide action #{i} missing required fields: {missing_fields}")

        atitle = action.get("title") or f"<add_new_slide #{i}>"
        qa = action.get("qa_expectations")
        if qa is not None and not isinstance(qa, list):
            errors.append(
                f"add_new_slide '{atitle}': qa_expectations must be a list "
                f"of rendered visual checks"
            )
        visual = str(action.get("visual_approach") or "").lower()
        if visual and not any(term in visual for term in ("deck", "slide", "visual", "render", "qa", "match", "reuse")):
            warnings.append(
                f"add_new_slide '{atitle}': visual_approach should explain how "
                f"the LLM will preserve deck visual flow and verify the rendered slide"
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


def _has_corpus_anchor(text: str, corpus_blob: str, min_len: int = 20) -> bool:
    """Return True if text contains a substring of corpus_blob at least min_len chars."""
    if not corpus_blob or not text:
        return False
    low = text.lower()
    blob = corpus_blob.lower()
    # Sliding window over words/phrases in text against corpus
    words = re.findall(r"\S+", low)
    for width in range(min(len(words), 12), 2, -1):
        for start in range(0, len(words) - width + 1):
            phrase = " ".join(words[start : start + width])
            if len(phrase) >= min_len and phrase in blob:
                return True
    # Fallback: any contiguous slice of text
    for start in range(len(low)):
        for end in range(start + min_len, min(len(low) + 1, start + 120)):
            chunk = low[start:end]
            if chunk in blob:
                return True
    return False


def run_generational_analysis_sweep(
    xval: dict,
    *,
    corpus_blob: str = "",
    known_source_ids: set[str] | None = None,
) -> list[str]:
    """Validate that every slides_explicitly_cleared entry has substantive generational_analysis."""
    errors: list[str] = []
    known_source_ids = known_source_ids or set()
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
                    f"Rule 39 requires substantive generational analysis"
                )
            clear_sids = row.get("source_ids") or []
            if not clear_sids:
                errors.append(f"slide {slide_no}: slides_explicitly_cleared missing source_ids")
            else:
                for sid in clear_sids:
                    if known_source_ids and str(sid) not in known_source_ids:
                        errors.append(
                            f"slide {slide_no}: clear source_id {sid!r} not in inventory/reference extract"
                        )
            ga = row.get("generational_analysis")
            if not isinstance(ga, dict):
                errors.append(
                    f"slide {slide_no}: slides_explicitly_cleared entry missing required "
                    f"'generational_analysis' object (Rule 39)"
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
            ga_sids = ga.get("source_ids") or []
            tgc_ids = set(SRC_ID_RE.findall(tgc))
            referenced = (
                {str(s) for s in clear_sids}
                | {str(s) for s in ga_sids}
                | {s.upper() for s in tgc_ids}
            )
            if known_source_ids and referenced:
                unknown = [s for s in referenced if s not in known_source_ids]
                if unknown:
                    errors.append(
                        f"slide {slide_no}: generational_analysis references unknown source_ids: "
                        f"{unknown[:5]}"
                    )
            elif not referenced:
                errors.append(
                    f"slide {slide_no}: generational_analysis must cite source_ids in "
                    f"target_generation_changes or generational_analysis.source_ids"
                )
            if corpus_blob and not (
                _has_corpus_anchor(tgc, corpus_blob) or _has_corpus_anchor(wni, corpus_blob)
            ):
                errors.append(
                    f"slide {slide_no}: generational_analysis must anchor target_generation_changes "
                    f"or why_no_impact to a >=20 char substring from reference_extract"
                )
    return errors


def _text_blob(value: Any) -> str:
    """Return a searchable lowercase blob from nested JSON-like values."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.lower()
    if isinstance(value, dict):
        return " ".join(_text_blob(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(_text_blob(v) for v in value)
    return str(value).lower()


def _technical_terms(text: str) -> set[str]:
    """Extract coarse technical terms from notes text for OST coherence checks."""

    terms: set[str] = set()
    for match in re.finditer(
        r"\b(?:[A-Z][A-Z0-9-]{2,}|[A-Z][a-z]+[0-9][A-Za-z0-9-]*|"
        r"[A-Z]+[a-z]*-[A-Za-z0-9-]+|\d+\s*(?:GT/s|GB/s|MHz|GHz|MB|KB|lanes?))\b",
        text or "",
    ):
        term = re.sub(r"\s+", " ", match.group(0)).strip().lower()
        if len(term) >= 3:
            terms.add(term)
    return terms


def _action_ost_blob(action: dict) -> str:
    fields = [
        action.get("match_text"),
        action.get("replacement_text"),
        action.get("find_fragment"),
        action.get("replace_fragment"),
        action.get("title"),
        action.get("statement"),
        action.get("ascii_art"),
        action.get("diagram"),
        action.get("table"),
        action.get("columns"),
        action.get("cards"),
        action.get("key_points"),
    ]
    fields.extend(action.get("replacements") or [])
    return _text_blob(fields)


def run_scope_consistency_sweep(
    scope_doc: Any,
    verification_doc: Any,
    xval: dict,
    plan: dict,
) -> tuple[list[str], list[str]]:
    """Require each scope-consistency violation to be addressed or explicitly cleared."""

    if not scope_doc:
        return [], []
    violations = scope_doc.get("violations") if isinstance(scope_doc, dict) else scope_doc
    if not isinstance(violations, list):
        return ["scope_consistency.json is neither a list nor an object with violations[]"], []

    errors: list[str] = []
    warnings: list[str] = []
    rows_by_slide = {
        int(r.get("slide_number")): r
        for r in as_rows(verification_doc)
        if isinstance(r, dict) and r.get("slide_number") is not None
    }
    clears_by_slide: dict[int, list[dict]] = {}
    for bucket in ("cleared_with_evidence", "slides_explicitly_cleared"):
        for row in (xval.get(bucket) if isinstance(xval, dict) else []) or []:
            if not isinstance(row, dict):
                continue
            try:
                clears_by_slide.setdefault(int(row.get("slide") or row.get("slide_number")), []).append(row)
            except (TypeError, ValueError):
                continue

    actions_by_slide: dict[int, list[dict]] = {}
    for action in plan.get("actions") or []:
        slide_no = _action_slide(action)
        if slide_no is not None:
            actions_by_slide.setdefault(slide_no, []).append(action)

    for violation in violations:
        if not isinstance(violation, dict):
            continue
        try:
            slide_no = int(violation.get("slide_number") or violation.get("slide"))
        except (TypeError, ValueError):
            errors.append(f"scope-consistency violation has invalid slide number: {violation}")
            continue
        tokens = [
            str(v).lower()
            for key in ("stale_tokens", "stale_tokens_found", "scope_phrases", "scope_phrases_found")
            for v in (violation.get(key) or [])
        ]
        tokens = [t for t in tokens if t]
        row_blob = _text_blob(rows_by_slide.get(slide_no, {}))
        action_blob = _text_blob(actions_by_slide.get(slide_no, []))
        clear_blob = _text_blob(clears_by_slide.get(slide_no, []))
        if tokens and any(t in row_blob or t in action_blob or t in clear_blob for t in tokens):
            continue
        errors.append(
            f"slide {slide_no}: scope-consistency violation is not represented by "
            "a finding, plan action, or explicit clear"
        )
    return errors, warnings


def _proofread_dispositions_by_slide(proofread_doc: Any) -> dict[int, list[dict]]:
    """Index proofread_review.json scan dispositions by slide number."""
    out: dict[int, list[dict]] = {}
    if not isinstance(proofread_doc, dict):
        return out
    for entry in proofread_doc.get("scan_signals_dispositioned") or []:
        if not isinstance(entry, dict):
            continue
        try:
            slide_no = int(entry.get("slide_number") or entry.get("slide"))
        except (TypeError, ValueError):
            continue
        out.setdefault(slide_no, []).append(entry)
    return out


def _signal_dismissed_by_proofread(
    proofread_by_slide: dict[int, list[dict]],
    slide_no: int,
    tokens: list[str],
) -> bool:
    """True if an LLM proofread disposition dismisses this scan signal.

    A non-`confirmed_finding` disposition (rejected_lint / intentionally_kept /
    out_of_scope) WITH a non-empty note, whose token set intersects the scan
    signal's tokens, counts as a documented dismissal — the escape hatch for
    legitimate script false positives. `confirmed_finding` does NOT dismiss; it
    must still be represented by a finding/action/clear.
    """
    token_set = {t.lower() for t in tokens if t}
    for entry in proofread_by_slide.get(slide_no, []):
        disp = str(entry.get("disposition") or "").lower()
        if disp in {"", "confirmed_finding"}:
            continue
        if disp not in LINT_SIGNAL_DISPOSITIONS:
            continue
        if not str(entry.get("note") or "").strip():
            continue
        entry_tokens = {str(t).lower() for t in (entry.get("tokens") or []) if t}
        if not entry_tokens or token_set & entry_tokens:
            return True
    return False


def run_consistency_reconciliation_sweep(
    consistency_doc: Any,
    verification_doc: Any,
    xval: dict,
    plan: dict,
    proofread_doc: Any = None,
) -> tuple[list[str], list[str]]:
    """Require every intra-slide consistency violation to be addressed (Rule 35).

    consistency_scan.py mechanically detects near-miss technical-token variants
    on a slide (e.g. callout 'A78AE' vs diagram label 'A78E'). Each non-advisory
    violation must be reconciled in one of these ways, or the typo/mismatch ships
    silently (the original B-001/B-002 failure):
      - a finding, plan action, or explicit clear that names an implicated token; OR
      - an LLM proofread disposition in proofread_review.json that dismisses the
        signal as a documented false positive / intentional / out-of-scope.

    Advisory typo signals are surfaced as warnings only.

    Returns (errors, warnings).
    """
    if not consistency_doc:
        return [], []
    violations = (
        consistency_doc.get("violations")
        if isinstance(consistency_doc, dict)
        else consistency_doc
    )
    if not isinstance(violations, list):
        return ["consistency_scan.json is neither a list nor an object with violations[]"], []

    errors: list[str] = []
    warnings: list[str] = []

    rows_by_slide = {
        int(r.get("slide_number")): r
        for r in as_rows(verification_doc)
        if isinstance(r, dict) and r.get("slide_number") is not None
    }
    clears_by_slide: dict[int, list[dict]] = {}
    for bucket in ("cleared_with_evidence", "slides_explicitly_cleared"):
        for row in (xval.get(bucket) if isinstance(xval, dict) else []) or []:
            if not isinstance(row, dict):
                continue
            try:
                clears_by_slide.setdefault(
                    int(row.get("slide") or row.get("slide_number")), []
                ).append(row)
            except (TypeError, ValueError):
                continue

    actions_by_slide: dict[int, list[dict]] = {}
    for action in plan.get("actions") or []:
        slide_no = _action_slide(action)
        if slide_no is not None:
            actions_by_slide.setdefault(slide_no, []).append(action)

    proofread_by_slide = _proofread_dispositions_by_slide(proofread_doc)

    for violation in violations:
        if not isinstance(violation, dict):
            continue
        try:
            slide_no = int(violation.get("slide_number") or violation.get("slide"))
        except (TypeError, ValueError):
            errors.append(f"consistency violation has invalid slide number: {violation}")
            continue
        tokens = [str(t).lower() for t in (violation.get("tokens") or []) if t]
        issue = str(violation.get("issue") or "")
        if violation.get("advisory"):
            warnings.append(f"slide {slide_no}: {issue}")
            continue
        if not tokens:
            continue
        # Escape hatch: LLM proofread pass documented this as a false positive.
        if _signal_dismissed_by_proofread(proofread_by_slide, slide_no, tokens):
            continue
        row_blob = _text_blob(rows_by_slide.get(slide_no, {}))
        action_blob = _text_blob(actions_by_slide.get(slide_no, []))
        clear_blob = _text_blob(clears_by_slide.get(slide_no, []))
        # Reconciled if ANY implicated token is named in a finding, action, or clear.
        if any(t in row_blob or t in action_blob or t in clear_blob for t in tokens):
            continue
        errors.append(
            f"slide {slide_no}: intra-slide consistency violation "
            f"{violation.get('tokens')} is not represented by a finding, plan "
            f"action, explicit clear, or a documented proofread disposition "
            f"(Rule 35). {issue}"
        )
    return errors, warnings


def run_proofread_review_sweep(
    proofread_doc: Any,
    consistency_doc: Any,
    slides: list[dict],
    verification_doc: Any,
    xval: dict,
    plan: dict,
    *,
    stage: str,
) -> tuple[list[str], list[str]]:
    """Require an explicit, deck-wide LLM proofreading pass (Rule 35).

    The deterministic consistency_scan.py catches near-miss letter typos. This
    sweep enforces the complementary *intelligent* pass: a named, required
    proofread_review.json deliverable that (a) covers every slide, (b) explicitly
    dispositions every non-advisory script signal, and (c) records the semantic /
    grammar / cross-slide issues a regex can never find. Without this, deck-wide
    proofreading stays an implicit hope that the per-slide audit skips under
    compaction or "topic is current" bias.

    Returns (errors, warnings).
    """
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(proofread_doc, dict):
        errors.append(
            "proofread_review.json missing or malformed. Phase 3 requires an "
            "explicit LLM proofreading pass (deck-wide spelling, grammar, and "
            "intra/cross-slide term consistency). Author it per "
            "references/artifact_schemas.md (proofread_review.json) and "
            "references/workflow_phases.md (Phase 3 proofreading sub-step)."
        )
        return errors, warnings

    expected_slides = {int(s.get("slide_number")) for s in slides if s.get("slide_number")}
    reviewed = set()
    for n in proofread_doc.get("slides_reviewed") or []:
        try:
            reviewed.add(int(n))
        except (TypeError, ValueError):
            continue
    missing = sorted(expected_slides - reviewed)
    if missing:
        errors.append(
            f"proofread_review.slides_reviewed does not cover every slide; "
            f"missing {missing[:20]}"
        )

    # Every non-advisory script signal must be explicitly dispositioned.
    violations = (
        consistency_doc.get("violations")
        if isinstance(consistency_doc, dict)
        else (consistency_doc or [])
    )
    proofread_by_slide = _proofread_dispositions_by_slide(proofread_doc)
    if isinstance(violations, list):
        for v in violations:
            if not isinstance(v, dict) or v.get("advisory"):
                continue
            try:
                slide_no = int(v.get("slide_number") or v.get("slide"))
            except (TypeError, ValueError):
                continue
            tokens = {str(t).lower() for t in (v.get("tokens") or []) if t}
            matched = False
            for entry in proofread_by_slide.get(slide_no, []):
                disp = str(entry.get("disposition") or "").lower()
                if disp not in LINT_SIGNAL_DISPOSITIONS:
                    continue
                entry_tokens = {str(t).lower() for t in (entry.get("tokens") or []) if t}
                if not tokens or not entry_tokens or tokens & entry_tokens:
                    matched = True
                    break
            if not matched:
                errors.append(
                    f"slide {slide_no}: consistency_scan signal {v.get('tokens')} "
                    f"is not dispositioned in proofread_review.scan_signals_dispositioned "
                    f"(set disposition to one of {sorted(LINT_SIGNAL_DISPOSITIONS)} with a note)"
                )

    # Proofread-discovered 'fix' issues must be acted on (warn pre-plan, error pre-execute).
    rows_by_slide = {
        int(r.get("slide_number")): r
        for r in as_rows(verification_doc)
        if isinstance(r, dict) and r.get("slide_number") is not None
    }
    actions_by_slide: dict[int, list[dict]] = {}
    for action in plan.get("actions") or []:
        sn = _action_slide(action)
        if sn is not None:
            actions_by_slide.setdefault(sn, []).append(action)
    clears_by_slide: dict[int, list[dict]] = {}
    for bucket in ("cleared_with_evidence", "slides_explicitly_cleared"):
        for row in (xval.get(bucket) if isinstance(xval, dict) else []) or []:
            if not isinstance(row, dict):
                continue
            try:
                clears_by_slide.setdefault(
                    int(row.get("slide") or row.get("slide_number")), []
                ).append(row)
            except (TypeError, ValueError):
                continue

    for issue in proofread_doc.get("issues") or []:
        if not isinstance(issue, dict):
            continue
        if str(issue.get("severity") or "").lower() != "fix":
            continue
        try:
            slide_no = int(issue.get("slide_number") or issue.get("slide"))
        except (TypeError, ValueError):
            continue
        represented = bool(
            rows_by_slide.get(slide_no, {}).get("findings")
            or actions_by_slide.get(slide_no)
            or clears_by_slide.get(slide_no)
        )
        if represented:
            continue
        msg = (
            f"slide {slide_no}: proofread_review issue marked severity 'fix' "
            f"({str(issue.get('description') or '')[:80]!r}) has no finding, "
            f"plan action, or clear on that slide"
        )
        if stage == "pre-execute":
            errors.append(msg)
        else:
            warnings.append(msg)

    return errors, warnings


def run_notes_ost_coherence_sweep(
    slides: list[dict],
    plan: dict,
) -> list[str]:
    """Ensure notes updates do not teach terms absent from visible text or companion OST actions."""

    errors: list[str] = []
    slide_ost = {
        int(slide.get("slide_number")): " ".join(
            sh.get("text") or "" for sh in (slide.get("texts") or [])
        ).lower()
        for slide in slides
        if slide.get("slide_number") is not None
    }
    actions = plan.get("actions") or []
    companion_by_slide: dict[int, str] = {}
    for action in actions:
        if action.get("type") in {"update_existing", "fragment_replace", "add_new_slide", "knowledge_check_update"}:
            slide_no = _action_slide(action)
            if slide_no is not None:
                companion_by_slide[slide_no] = companion_by_slide.get(slide_no, "") + " " + _action_ost_blob(action)

    for i, action in enumerate(actions):
        if action.get("type") != "notes_update":
            continue
        slide_no = _action_slide(action)
        if slide_no is None:
            continue
        note_text = _text_blob(action.get("notes_changes") or action.get("speaker_notes") or "")
        terms = _technical_terms(note_text)
        if not terms:
            continue
        ost_blob = slide_ost.get(slide_no, "") + " " + companion_by_slide.get(slide_no, "")
        missing = sorted(term for term in terms if term not in ost_blob)
        if missing:
            errors.append(
                f"action #{i} ({action.get('type')}, slide {slide_no}) introduces "
                f"technical term(s) absent from OST or companion OST action: {missing[:8]}"
            )
    return errors


def run_original_notes_sweep(original_notes: Any, plan: dict) -> list[str]:
    """Cross-check notes_update actions against Phase 1.5 original_notes.json."""

    if not isinstance(original_notes, dict):
        return []
    errors: list[str] = []
    for i, action in enumerate(plan.get("actions") or []):
        if action.get("type") != "notes_update":
            continue
        slide_no = action.get("slide_number")
        original = original_notes.get(str(slide_no))
        if original is None:
            original = original_notes.get(slide_no)
        if original is None:
            continue
        old_notes = action.get("old_speaker_notes")
        if old_notes != original:
            errors.append(
                f"action #{i} (notes_update, slide {slide_no}): old_speaker_notes "
                "does not exactly match original_notes.json"
            )
        for j, change in enumerate(action.get("notes_changes") or []):
            fragment = change.get("match_fragment") or ""
            if fragment and fragment not in original:
                errors.append(
                    f"action #{i} (notes_update, slide {slide_no}) "
                    f"notes_changes[{j}].match_fragment is not present in original_notes.json"
                )
    return errors


def _action_slide(action: dict) -> int | None:
    raw = action.get("slide_number") or action.get("slide") or action.get("insert_after_slide")
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _hit_location_terms(hit: dict) -> list[str]:
    terms = [
        str(hit.get("token") or "").strip().lower(),
        str(hit.get("location") or "").strip().lower(),
        str(hit.get("shape_id") or "").strip().lower(),
        str(hit.get("shape_name") or "").strip().lower(),
    ]
    preview = str(hit.get("shape_text_preview") or "").strip().lower()
    if preview:
        terms.append(preview[:80])
    return [t for t in terms if t]


def _is_intentionally_kept_hit(stale_terms_doc: dict | None, token: str, slide_no: int) -> bool:
    if not isinstance(stale_terms_doc, dict):
        return False
    token_lower = token.lower()
    for row in stale_terms_doc.get("intentionally_kept") or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("token") or "").lower() != token_lower:
            continue
        try:
            slides = {int(s) for s in (row.get("on_slides") or [])}
        except (TypeError, ValueError):
            slides = set()
        if slide_no in slides:
            return True
    return False


def run_stale_hit_reconciliation_sweep(
    wd: Path,
    verification_doc: Any,
    xval: dict,
    plan: dict,
    stale_terms_doc: dict | None,
) -> tuple[list[str], list[str]]:
    """Require every surviving stale-term scan hit to be explicitly reconciled.

    stale_term_scan.py already removes skip-guarded and intentionally kept hits.
    This sweep catches the remaining failure mode: a scan hit exists, but the
    slide is generically cleared without a finding or token-specific rationale.
    """
    scan_path = wd / "stale_term_scan.json"
    if not scan_path.exists():
        return [], ["stale_term_scan.json not found; stale-hit reconciliation sweep skipped"]

    scan_doc = load(scan_path)
    if not isinstance(scan_doc, list):
        return [("stale_term_scan.json is not a list; cannot reconcile stale hits")], []

    errors: list[str] = []
    warnings: list[str] = []
    rows_by_slide = {
        int(r.get("slide_number")): r
        for r in as_rows(verification_doc)
        if isinstance(r, dict) and r.get("slide_number") is not None
    }

    clears_by_slide: dict[int, dict] = {}
    if isinstance(xval, dict):
        for bucket in ("cleared_with_evidence", "slides_explicitly_cleared"):
            for row in xval.get(bucket) or []:
                if not isinstance(row, dict):
                    continue
                try:
                    clears_by_slide[int(row.get("slide") or row.get("slide_number"))] = row
                except (TypeError, ValueError):
                    continue

    actions_by_slide: dict[int, list[dict]] = {}
    for action in plan.get("actions") or []:
        if not isinstance(action, dict):
            continue
        slide_no = _action_slide(action)
        if slide_no is not None:
            actions_by_slide.setdefault(slide_no, []).append(action)

    total_hits = 0
    reconciled_hits = 0
    unresolved_hits: list[dict] = []

    for slide_scan in scan_doc:
        if not isinstance(slide_scan, dict):
            continue
        try:
            slide_no = int(slide_scan.get("slide_number"))
        except (TypeError, ValueError):
            continue
        for hit in slide_scan.get("hits") or []:
            if not isinstance(hit, dict):
                continue
            token = str(hit.get("token") or "").strip()
            if not token:
                continue
            total_hits += 1
            token_lower = token.lower()
            location = str(hit.get("location") or "").strip()

            if _is_intentionally_kept_hit(stale_terms_doc, token, slide_no):
                reconciled_hits += 1
                continue

            row = rows_by_slide.get(slide_no) or {}
            findings = row.get("findings") or []
            finding_matches = [
                f for f in findings
                if isinstance(f, dict) and token_lower in _text_blob(f)
            ]
            action_matches = [
                a for a in actions_by_slide.get(slide_no, [])
                if token_lower in _text_blob(a)
            ]

            clear = clears_by_slide.get(slide_no)
            clear_matches = False
            if clear and clear.get("source_ids"):
                clear_blob = _text_blob({
                    "reason": clear.get("reason"),
                    "generational_analysis": clear.get("generational_analysis"),
                })
                clear_matches = any(term in clear_blob for term in _hit_location_terms(hit))

            if finding_matches or action_matches or clear_matches:
                reconciled_hits += 1
                continue

            unresolved = {
                "slide_number": slide_no,
                "token": token,
                "location": location,
                "shape_id": hit.get("shape_id"),
                "shape_name": hit.get("shape_name"),
            }
            unresolved_hits.append(unresolved)
            where = f" in {location}" if location else ""
            shape = ""
            if hit.get("shape_id") or hit.get("shape_name"):
                shape = f" ({hit.get('shape_name') or 'shape'} {hit.get('shape_id') or ''})"
            errors.append(
                f"slide {slide_no} stale hit {token}{where}{shape} is not represented by "
                "a finding, plan action, intentionally_kept entry, or token-specific clear"
            )

    if isinstance(xval, dict):
        xval["stale_hit_reconciliation"] = {
            "total_hits": total_hits,
            "reconciled_hits": reconciled_hits,
            "unresolved_hits": unresolved_hits,
        }
        try:
            (wd / "cross_validation_report.json").write_text(
                json.dumps(xval, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except OSError as exc:
            warnings.append(f"could not write stale_hit_reconciliation summary: {exc}")

    return errors, warnings


def run_scope_depth_checks(
    deck: dict,
    plan: dict,
    stale_terms_doc: dict | None,
    concept_decomp: dict,
    parity_path: Path,
    src: dict | None,
    stale_scan_doc: Any | None = None,
    *,
    require_plan_actions: bool = True,
) -> tuple[list[str], list[str]]:
    """Surface shallow-audit lint without turning heuristic counts into blockers.

    This check intentionally returns warnings for low stale-term counts, missing
    advisory parity output, thin concept decomposition, and suspiciously few
    plan actions. The hard evidence checks live in structural, verification,
    stale-hit reconciliation, notes, and plan validation sweeps.

    Returns (errors, warnings).
    """
    errors: list[str] = []
    warnings: list[str] = []

    slides = deck.get("slides") or []
    base_slide_count = len(slides)
    actions = plan.get("actions") or []

    # --- Advisory 1: Low stale-term scan hit count ---
    st_entries = []
    if isinstance(stale_terms_doc, dict):
        st_entries = stale_terms_doc.get("stale_terms") or []
    scan_hit_count = None
    if isinstance(stale_scan_doc, list):
        scan_hit_count = sum(
            len(row.get("hits") or [])
            for row in stale_scan_doc
            if isinstance(row, dict)
        )
    if base_slide_count > 15 and scan_hit_count is not None and scan_hit_count <= 3:
        warnings.append(
            f"Only {scan_hit_count} stale-term scan hit(s) found for a "
            f"{base_slide_count}-slide deck. Treat this as an advisory lint "
            f"signal: the LLM should confirm stale_terms.json scope and document "
            f"claim/source dispositions, but this count alone is not a blocker."
        )
    elif len(st_entries) < 3 and base_slide_count > 15:
        warnings.append(
            f"Only {len(st_entries)} stale term(s) authored for a "
            f"{base_slide_count}-slide deck. Treat this as an advisory lint "
            f"signal; validate source-backed claim coverage rather than padding "
            f"stale terms to satisfy a count."
        )

    # --- Advisory 2: Parity lint missing when variants are declared ---
    product_variants = []
    if isinstance(stale_terms_doc, dict):
        product_variants = stale_terms_doc.get("product_variants") or []
    if product_variants and not parity_path.exists():
        warnings.append(
            f"product_variants lists {len(product_variants)} variant(s) "
            f"({', '.join(product_variants[:5])}) but parity_matrix.json "
            f"was not generated. This optional lint can help prompt LLM parity "
            f"review, but the LLM-authored concept coverage is authoritative."
        )

    # --- Advisory 3: Thin concept decomposition ---
    source_deltas = concept_decomp.get("source_deltas") or []
    entries = source_inventory_entries(src)
    has_source_results = any(
        (e.get("results_count") or 0) > 0
        for e in entries
    )
    if len(source_deltas) < 2 and base_slide_count > 15 and has_source_results:
        warnings.append(
            f"Only {len(source_deltas)} source delta(s) decomposed for a "
            f"{base_slide_count}-slide deck with available source data. "
            f"Confirm the LLM-authored concept decomposition covers every "
            f"source-backed change that affects the learning story."
        )

    # --- Advisory 4: Plan action count sanity check ---
    if require_plan_actions and len(actions) < 3 and base_slide_count > 15:
        warnings.append(
            f"Only {len(actions)} plan action(s) planned for a "
            f"{base_slide_count}-slide deck. This may be correct for a narrow "
            f"update, but the LLM should explicitly disposition source deltas, "
            f"stale hits, and affected story surfaces."
        )

    return errors, warnings


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--work-dir", required=True)
    ap.add_argument(
        "--stage",
        choices=["pre-plan", "pre-execute"],
        default="pre-execute",
        help="pre-plan validates audit artifacts before update_plan.json exists; pre-execute validates the approved plan.",
    )
    ap.add_argument("--corpus", nargs="*", default=[], help="Additional corpus JSON chunks used for verification.")
    ap.add_argument(
        "--require-sources",
        action="store_true",
        help="Require documented source coverage entries with source IDs; does not enforce fixed channel counts.",
    )
    ap.add_argument(
        "--legacy-require-zero-coverage-gaps",
        action="store_true",
        help="DEPRECATED: removed. Token-overlap coverage gaps are advisory only.",
    )
    ap.add_argument("--require-source-basis", action="store_true", default=True, help="Require source_basis/audit_basis on every mutating action.")
    ap.add_argument("--require-source-ids", action="store_true", default=True, help="Require source_ids on slide/finding clears.")
    ap.add_argument("--strict-notes", action="store_true", default=True, help="Reject speaker notes with banned narrator openers.")
    args = ap.parse_args(argv)

    if getattr(args, "legacy_require_zero_coverage_gaps", False):
        print(json.dumps({
            "errors": [
                "--legacy-require-zero-coverage-gaps is removed. coverage_gaps.json is advisory; "
                "LLM must disposition signals in verification artifacts or coverage_gap_reconciliation.json."
            ],
            "warnings": [],
        }, indent=2))
        return EXIT_FATAL

    wd = Path(args.work_dir)
    deck = load(wd / "deck_extract.json")
    src = load(wd / "source_inventory.json")
    ref = load(wd / "reference_extract.json")
    verification_doc = load(wd / "verification_report.json")
    xval = load(wd / "cross_validation_report.json")
    plan = load(wd / "update_plan_final.json") or load(wd / "update_plan.json")
    coverage = load(wd / "coverage_gaps.json")
    coverage_recon = load(wd / "coverage_gap_reconciliation.json")
    scope_consistency = load(wd / "scope_consistency.json")
    consistency_doc = load(wd / "consistency_scan.json")
    proofread_doc = load(wd / "proofread_review.json")
    stale_scan_doc = load(wd / "stale_term_scan.json")
    original_notes = load(wd / "original_notes.json")

    errors: list[str] = []
    warnings: list[str] = []

    required = {
        "deck_extract.json": deck,
        "source_inventory.json": src,
        "reference_extract.json": ref,
        "verification_report.json": verification_doc,
        "cross_validation_report.json": xval,
    }
    if args.stage == "pre-execute":
        required["update_plan.json"] = plan
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
    if plan is None:
        plan = {
            "schema_version": "2.0",
            "deck": deck.get("deck", ""),
            "target_version": (load(wd / "stale_terms.json") or {}).get("target_release", ""),
            "status": "audit",
            "actions": [],
        }

    if args.stage == "pre-plan" and not (wd / "audit_summary.md").exists():
        warnings.append(
            "audit_summary.md not found; write a human-readable checkpoint summary before "
            "the Phase 3→4 user acknowledgement (see references/audit_summary_guide.md)"
        )

    if coverage and not coverage_recon:
        gap_rows = coverage.get("slides_with_gaps") or coverage.get("gaps") or []
        if gap_rows:
            warnings.append(
                "coverage_gaps.json has advisory lint signals but coverage_gap_reconciliation.json "
                "is missing; document LLM dispositions after Phase 2.5"
            )

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

    # Scope-depth checks (Gates 1-4: stale-term count, parity matrix,
    # concept decomposition depth, plan action count)
    stale_terms_doc = load(wd / "stale_terms.json")
    sd_err, sd_warn = run_scope_depth_checks(
        deck, plan, stale_terms_doc, concept_decomp, parity_path, src,
        stale_scan_doc,
        require_plan_actions=args.stage == "pre-execute",
    )
    errors.extend(sd_err)
    warnings.extend(sd_warn)

    # Plan schema validation (validate_plan.py integration)
    story = load(wd / "story_model.json") or {}
    if args.stage == "pre-execute":
        vp_errors, vp_warnings = validate_plan_schema(plan, story)
        errors.extend(vp_errors)
        warnings.extend(vp_warnings)

    # Structural checks: row coverage, source inventory, corpus
    s_err, s_warn, slides, rows_by_slide, corpus_blob, known_source_ids = run_structural_checks(
        deck, src, ref, verification_doc, xval, coverage, args.corpus,
        require_sources=args.require_sources,
    )
    errors.extend(s_err)
    warnings.extend(s_warn)

    # Per-slide verification
    v_err, v_warn, unresolved_findings, new_slide_candidate_ids = run_verification_sweep(
        slides, rows_by_slide, xval, plan, corpus_blob, known_source_ids,
        require_source_ids=args.require_source_ids,
        require_finding_actions=args.stage == "pre-execute",
    )
    errors.extend(v_err)
    warnings.extend(v_warn)

    actions = plan.get("actions") or []
    if args.stage == "pre-execute":
        # New-slide schema validation
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

    # Generational analysis sweep (Rule 39)
    errors.extend(run_generational_analysis_sweep(
        xval, corpus_blob=corpus_blob, known_source_ids=known_source_ids,
    ))

    # Stale-hit reconciliation sweep (Rule 46)
    shr_err, shr_warn = run_stale_hit_reconciliation_sweep(
        wd, verification_doc, xval, plan, stale_terms_doc,
    )
    errors.extend(shr_err)
    warnings.extend(shr_warn)

    scope_err, scope_warn = run_scope_consistency_sweep(
        scope_consistency, verification_doc, xval, plan,
    )
    errors.extend(scope_err)
    warnings.extend(scope_warn)

    # Intra-slide consistency reconciliation sweep (Rule 35)
    if consistency_doc is None and (wd / "deck_extract.json").exists():
        warnings.append(
            "consistency_scan.json not found; run consistency_scan.py (or "
            "storyboard_update.py --mode audit-plan) so intra-slide near-miss "
            "variants are reconciled (Rule 35)"
        )
    cons_err, cons_warn = run_consistency_reconciliation_sweep(
        consistency_doc, verification_doc, xval, plan, proofread_doc,
    )
    errors.extend(cons_err)
    warnings.extend(cons_warn)

    # Explicit LLM proofreading pass (Rule 35) — deck-wide spelling, grammar,
    # and intra/cross-slide consistency that the deterministic scan cannot find.
    pr_err, pr_warn = run_proofread_review_sweep(
        proofread_doc, consistency_doc, slides, verification_doc, xval, plan,
        stage=args.stage,
    )
    errors.extend(pr_err)
    warnings.extend(pr_warn)

    if args.stage == "pre-execute":
        errors.extend(run_notes_ost_coherence_sweep(slides, plan))
        errors.extend(run_original_notes_sweep(original_notes, plan))

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
            if not isinstance(slide_row, dict):
                continue
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
