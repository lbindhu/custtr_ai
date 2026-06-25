#!/usr/bin/env python3
"""Post-apply differential check.

After Phase A (apply_existing_updates), re-run the stale-term scan against the
just-produced updated_base.pptx and compare hit counts vs the original.

Rules:
  - Hit count must not increase.
  - For every stale-term row addressed by an action with `match_text` /
    `replacements`, that exact token must no longer appear on that slide
    UNLESS it's part of a yellow-strike OOXML diff run (struck-through old
    text). We detect this by reading the slide XML and checking if hits are
    within <a:r> whose <a:rPr> has strike="sngStrike".
  - Tokens listed in `intentionally_kept.on_slides` for that slide are
    permitted to survive.
  - Also reports any apply_misses.json sidecar entries.

Exits non-zero if any rule is violated.
"""
import argparse
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ooxml_helpers import NS, q, parse  # noqa: E402
from constants import EXIT_OK, EXIT_ERROR, EXIT_FATAL  # noqa: E402
from json_helpers import safe_load_json, try_load_json  # noqa: E402
from stale_terms import iter_findings, is_intentionally_kept, load_stale_terms  # noqa: E402


def collect_non_struck_text_per_slide(pptx_path):
    """Return {slide_number: combined_text} excluding text inside strike runs."""
    out = {}
    with zipfile.ZipFile(pptx_path) as z:
        # ordered slide paths
        pres = ET.fromstring(z.read("ppt/presentation.xml"))
        rels = ET.fromstring(z.read("ppt/_rels/presentation.xml.rels"))
        rmap = {r.attrib["Id"]: r.attrib["Target"]
                for r in rels.findall(q("rel", "Relationship"))}
        slide_ids = pres.findall(".//" + q("p", "sldId"))
        for idx, s in enumerate(slide_ids, start=1):
            rid = s.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
            target = rmap[rid]
            path = "ppt/" + target.lstrip("./")
            root = ET.fromstring(z.read(path))
            chunks = []
            for r in root.findall(".//" + q("a", "r")):
                rpr = r.find(q("a", "rPr"))
                if rpr is not None and rpr.attrib.get("strike") == "sngStrike":
                    continue
                t = r.find(q("a", "t"))
                if t is not None and t.text:
                    chunks.append(t.text)
            out[idx] = " ".join(chunks)
    return out


def scan(text, stale_terms_doc, slide_no=None):
    """Return list of tokens (entry['token']) that survive in `text`,
    honouring skip_if_* guards and (optionally) intentionally_kept for slide_no.
    """
    hits = []
    seen = set()
    for entry, _start in iter_findings(text, stale_terms_doc):
        if slide_no is not None and is_intentionally_kept(entry["token"], slide_no, stale_terms_doc):
            continue
        if entry["token"] not in seen:
            seen.add(entry["token"])
            hits.append(entry["token"])
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--original", required=True)
    ap.add_argument("--updated", required=True)
    ap.add_argument("--stale-terms", required=True)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--require-fresh-merge", action="store_true",
                    help="Refuse to check if <updated>.merge_status.json reports a failed merge.")
    args = ap.parse_args()

    # ── Stale-artifact guard ────────────────────────────────────────────
    updated_path = Path(args.updated)
    sidecar = updated_path.with_suffix(updated_path.suffix + ".merge_status.json")
    if args.require_fresh_merge:
        if not sidecar.exists():
            print(json.dumps({
                "errors": [
                    f"--require-fresh-merge: no merge_status sidecar at {sidecar}; "
                    f"refusing to check a possibly-stale artifact."
                ]
            }, indent=2))
            sys.exit(2)
        try:
            status = json.loads(sidecar.read_text(encoding="utf-8"))
        except Exception as e:
            print(json.dumps({"errors": [f"could not read merge_status sidecar: {e}"]}, indent=2))
            sys.exit(2)
        if status.get("exit_code") not in (0, None):
            print(json.dumps({
                "errors": [
                    f"last merge_storyboard.py exit_code was {status['exit_code']}; "
                    f"refusing to run post-apply check on a stale on-disk deck."
                ]
            }, indent=2))
            sys.exit(2)

    stale_terms_doc = load_stale_terms(Path(args.stale_terms))
    orig_text = collect_non_struck_text_per_slide(args.original)
    upd_text = collect_non_struck_text_per_slide(args.updated)
    plan = safe_load_json(args.plan, "update_plan.json")

    # Build per-slide "expected to be removed" sets
    expected_removed = {}
    for a in plan.get("actions", []):
        sno = a.get("slide_number")
        if not sno:
            continue
        terms = []
        for r in a.get("replacements", []) or []:
            terms.append(r.get("match_text", ""))
        if a.get("match_text"):
            terms.append(a["match_text"])
        # notes_changes: the match_fragments are also expected to be gone from notes,
        # but post-apply check focuses on visible slide text. Notes regression is
        # caught by audit_gate's notes_structure_sweep + apply_misses.json.
        if terms:
            expected_removed[int(sno)] = terms

    errors = []
    warnings = []
    by_slide = {}
    for sno, txt in upd_text.items():
        before_hits = set(scan(orig_text.get(sno, ""), stale_terms_doc, sno))
        after_hits = set(scan(txt, stale_terms_doc, sno))
        new = after_hits - before_hits
        leaked = []
        # Any term that was in expected_removed for this slide but is still in `after_hits`
        # outside strike markup is a silent no-op miss.
        for term in expected_removed.get(sno, []):
            for needle in scan(term, stale_terms_doc, sno):
                if needle in after_hits:
                    leaked.append(needle)
        by_slide[sno] = {
            "before": sorted(before_hits),
            "after": sorted(after_hits),
            "new_hits_introduced": sorted(new),
            "expected_removed_but_still_present": sorted(set(leaked)),
        }
        if new:
            errors.append(f"slide {sno}: new stale token(s) introduced after apply: {sorted(new)}")
        if leaked:
            errors.append(f"slide {sno}: plan said to remove {sorted(set(leaked))} but they are still on the slide outside a strike run — match_text typo or whitespace mismatch.")

    # Highlight position validation: <a:highlight> must not appear after <a:latin>/<a:ea>/<a:cs>
    LATE_TAGS = {q("a", "latin"), q("a", "ea"), q("a", "cs")}
    hl_warnings = 0
    try:
        with zipfile.ZipFile(args.updated) as z:
            pres = ET.fromstring(z.read("ppt/presentation.xml"))
            rels = ET.fromstring(z.read("ppt/_rels/presentation.xml.rels"))
            rmap = {r.attrib["Id"]: r.attrib["Target"]
                    for r in rels.findall(q("rel", "Relationship"))}
            slide_ids = pres.findall(".//" + q("p", "sldId"))
            for idx, s in enumerate(slide_ids, start=1):
                rid = s.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
                target = rmap[rid]
                path = "ppt/" + target.lstrip("./")
                root = ET.fromstring(z.read(path))
                for rpr in root.findall(".//" + q("a", "rPr")):
                    hl = rpr.find(q("a", "highlight"))
                    if hl is None:
                        continue
                    children = list(rpr)
                    hl_idx = children.index(hl)
                    before_hl = {c.tag for c in children[:hl_idx]}
                    if not (before_hl & LATE_TAGS):
                        continue
                    hl_warnings += 1
                    warnings.append(
                        f"slide {idx}: <a:highlight> is after <a:latin>/<a:ea>/<a:cs> "
                        f"in <a:rPr> — PowerPoint will not render this highlight. "
                        f"Use add_highlight() from ooxml_helpers.py for correct positioning."
                    )
    except Exception as e:
        warnings.append(f"highlight position validation skipped: {e}")
    if hl_warnings:
        warnings.append(f"total mispositioned highlights: {hl_warnings}")

    # Sidecar: apply_misses.json (written by apply_existing_updates.py)
    misses_path = Path(args.updated).with_suffix("").parent / "apply_misses.json"
    misses = try_load_json(misses_path)
    if misses:
        for m in misses:
            errors.append(f"apply miss: slide {m.get('slide_number')} {m.get('kind')}: {m.get('match_text', '')[:80]!r}")

    payload = {"errors": errors, "warnings": warnings, "by_slide": by_slide}
    Path(args.output).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"errors": errors, "warnings": warnings, "slides_checked": len(by_slide)}, indent=2))
    sys.exit(EXIT_ERROR if errors else EXIT_OK)


if __name__ == "__main__":
    main()
