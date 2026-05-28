#!/usr/bin/env python3
"""Per-deck stale_terms.json loader, guard-aware matcher, and mandatory sweeps.

Library API (imported by post_apply_check.py, stale_term_scan.py,
scope_consistency_scan.py):
  load_stale_terms(path)                       -> dict
  iter_findings(text, doc)                     -> Iterator[(entry, start_pos)]
  is_intentionally_kept(token, slide_no, doc)  -> bool

CLI mode (standalone sweeps):
  python stale_terms.py --deck-extract ... --plan ... --stale-terms ... --output sweeps.json
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from constants import VERSION_RE, SUMMARY_RE, EXIT_OK, EXIT_ERROR  # noqa: E402
from json_helpers import safe_load_json  # noqa: E402


def load_stale_terms(path):
    return safe_load_json(path, "stale_terms.json")


def iter_findings(text, doc):
    """Case-insensitive scan of every stale_terms[].token against *text*.

    Yields ``(entry, start_position)`` for each hit that is NOT suppressed by
    ``skip_if_preceded_by`` / ``skip_if_followed_by`` guards.
    """
    text_lower = text.lower()
    for entry in doc.get("stale_terms", []):
        token = entry.get("token", "")
        if not token:
            continue
        token_lower = token.lower()
        start = 0
        while True:
            pos = text_lower.find(token_lower, start)
            if pos == -1:
                break
            start = pos + 1

            preceded_by = entry.get("skip_if_preceded_by", [])
            if preceded_by:
                prefix = text[:pos]
                skip = False
                for guard in preceded_by:
                    if guard and prefix.endswith(guard):
                        skip = True
                        break
                if skip:
                    continue

            followed_by = entry.get("skip_if_followed_by", [])
            if followed_by:
                suffix = text[pos + len(token):]
                skip = False
                for guard in followed_by:
                    if guard and suffix.startswith(guard):
                        skip = True
                        break
                if skip:
                    continue

            yield entry, pos


def is_intentionally_kept(token, slide_no, doc):
    for ik in doc.get("intentionally_kept", []):
        if ik.get("token", "").lower() == token.lower():
            if slide_no in ik.get("on_slides", []):
                return True
    return False


# ── Mandatory sweeps (also available as CLI) ──────────────────────────

# VERSION_RE and SUMMARY_RE imported from constants


def _version_sweep(deck_extract, stale_terms_doc, plan):
    target = stale_terms_doc.get("target_release", "")
    if not target:
        return []
    errors = []
    version_exceptions = {}
    for v in (plan.get("version_exceptions") or []):
        version_exceptions[(v.get("token", ""), v.get("slide", 0))] = v.get("reason", "")
    for slide in deck_extract.get("slides", []):
        sno = slide.get("slide_number", 0)
        all_text = " ".join(t.get("text", "") for t in slide.get("texts", []))
        for m in VERSION_RE.finditer(all_text):
            tok = m.group()
            if tok == target:
                continue
            if (tok, sno) in version_exceptions:
                continue
            label = "title slide" if sno == 1 else f"slide {sno}"
            errors.append(f"{label}: non-target version token {tok}")
    return errors


def _summary_recap_sweep(deck_extract, plan):
    errors = []
    targeted_slides = set()
    for a in plan.get("actions", []):
        s = a.get("slide") or a.get("slide_number")
        if s:
            targeted_slides.add(int(s))
    for slide in deck_extract.get("slides", []):
        sno = slide.get("slide_number", 0)
        title = ""
        for t in slide.get("texts", []):
            if t.get("is_title"):
                title = t.get("text", "")
                break
        if not title:
            texts = slide.get("texts", [])
            if texts:
                title = texts[0].get("text", "")
        if SUMMARY_RE.search(title) and sno not in targeted_slides:
            errors.append(f"slide {sno} ({title!r}): summary/recap slide has no plan action")
    return errors


def _notes_structure_sweep(plan):
    errors = []
    for a in plan.get("actions", []):
        at = a.get("type") or a.get("action_type", "")
        if at not in ("notes_update", "update_existing"):
            continue
        has_old = bool(a.get("old_speaker_notes"))
        has_new = bool(a.get("speaker_notes"))
        has_changes = bool(a.get("notes_changes"))
        if has_old and has_new and not has_changes:
            aid = a.get("action_id", "?")
            errors.append(
                f"action {aid}: wholesale notes replacement "
                f"(old_speaker_notes + speaker_notes) without notes_changes"
            )
    return errors


def run_sweeps(deck_extract, plan, stale_terms_doc):
    return {
        "version_sweep": _version_sweep(deck_extract, stale_terms_doc, plan),
        "summary_recap_sweep": _summary_recap_sweep(deck_extract, plan),
        "notes_structure_sweep": _notes_structure_sweep(plan),
    }


def main():
    ap = argparse.ArgumentParser(description="Run mandatory sweeps.")
    ap.add_argument("--deck-extract", required=True)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--stale-terms", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    deck_extract = safe_load_json(args.deck_extract, "deck_extract.json")
    plan = safe_load_json(args.plan, "update_plan.json")
    stale_terms_doc = load_stale_terms(Path(args.stale_terms))

    report = run_sweeps(deck_extract, plan, stale_terms_doc)
    Path(args.output).write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    total = sum(len(v) for v in report.values())
    print(json.dumps({"total_errors": total, **{k: len(v) for k, v in report.items()}}, indent=2))
    sys.exit(EXIT_ERROR if total > 0 else EXIT_OK)


if __name__ == "__main__":
    main()
