#!/usr/bin/env python3
import argparse
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ooxml_helpers import NS, q, parse, validate_pptx  # noqa: E402
from constants import EXIT_OK, EXIT_ERROR  # noqa: E402
from json_helpers import safe_load_json, try_load_json  # noqa: E402


def ordered(z):
    pres = parse(z.read("ppt/presentation.xml"))
    rels = parse(z.read("ppt/_rels/presentation.xml.rels"))
    rmap = {r.attrib["Id"]: r.attrib["Target"] for r in rels.findall(q("rel", "Relationship"))}
    return ["ppt/" + rmap[s.attrib[q("r", "id")]] for s in pres.findall(".//" + q("p", "sldId"))]


def texts(z, path):
    root = parse(z.read(path))
    out = []
    for sp in root.findall(".//" + q("p", "sp")):
        s = " ".join((t.text or "") for t in sp.findall(".//" + q("a", "t"))).strip()
        if s:
            out.append(re.sub(r"\s+", " ", s))
    return out


def new_slide_positions(plan):
    """Return 1-based logical output positions for add_new_slide actions.

    The final deck may contain review highlights on existing slides. The
    no-highlight rule is only for slides created by add_new_slide actions, so
    mirror merge_storyboard.py's insertion ordering and identify those slides.
    """
    slide_count = plan.get("base_slide_count")
    if not slide_count:
        return []

    remove = {
        a["slide_number"]
        for a in plan.get("actions", [])
        if a.get("type") == "remove_or_deprecate" and a.get("slide_number")
    }
    remove.discard(slide_count)

    groups = {}
    for action in plan.get("actions", []):
        if action.get("type") == "add_new_slide":
            after = action.get("insert_after_slide", slide_count)
            groups.setdefault(after, []).append(action)

    positions = []
    final_position = 0
    cursor = 1
    for after in sorted(groups):
        for original_slide in range(cursor, min(after, slide_count) + 1):
            if original_slide not in remove:
                final_position += 1
        for _action in groups[after]:
            final_position += 1
            positions.append(final_position)
        cursor = after + 1
    for original_slide in range(cursor, slide_count + 1):
        if original_slide not in remove:
            final_position += 1
    return positions


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("deck")
    ap.add_argument("--plan")
    ap.add_argument("--output")
    ap.add_argument("--work-dir", default=None, help="Work directory containing story_model.json fallback")
    ap.add_argument("--require-fresh-merge", action="store_true",
                    help="Refuse to validate if <deck>.merge_status.json reports a failed merge "
                         "or is missing while the deck file already exists.")
    args = ap.parse_args()

    # ── Stale-artifact guard ────────────────────────────────────────────
    # If a sidecar from merge_storyboard.py is present, refuse to validate
    # when the last merge exited non-zero. This prevents the silent-success
    # mode where validate runs against a stale prior deck.
    deck_path = Path(args.deck)
    sidecar = deck_path.with_suffix(deck_path.suffix + ".merge_status.json")
    if args.require_fresh_merge:
        if not sidecar.exists():
            print(json.dumps({
                "errors": [
                    f"--require-fresh-merge: no merge_status sidecar found at {sidecar}; "
                    f"merge_storyboard.py was not run (or its output was deleted)."
                ]
            }, indent=2))
            raise SystemExit(2)
        try:
            status = json.loads(sidecar.read_text(encoding="utf-8"))
        except Exception as e:
            print(json.dumps({"errors": [f"could not read merge_status sidecar: {e}"]}, indent=2))
            raise SystemExit(2)
        if status.get("exit_code") not in (0, None):
            print(json.dumps({
                "errors": [
                    f"last merge_storyboard.py exit_code was {status['exit_code']}; "
                    f"refusing to validate a stale on-disk deck. Fix the merge first."
                ]
            }, indent=2))
            raise SystemExit(2)

    validate_pptx(args.deck)
    report = {"deck": args.deck, "errors": [], "warnings": []}
    with zipfile.ZipFile(args.deck) as z:
        bad = z.testzip()
        if bad:
            report["errors"].append(f"zip corruption at {bad}")
        order = ordered(z)
        report["slide_count"] = len(order)
        report["notes_count"] = sum(n.startswith("ppt/notesSlides/notesSlide") and n.endswith(".xml") for n in z.namelist())
        all_xml = b"\n".join(z.read(n) for n in z.namelist() if n.endswith(".xml"))
        # Load target_version from plan (if provided) to identify version markers dynamically
        _target_ver = None
        if args.plan:
            try:
                _target_ver = json.loads(Path(args.plan).read_text(encoding="utf-8")).get("target_version", "")
            except (OSError, json.JSONDecodeError) as e:
                print(f"WARNING: could not read plan for target_version: {e}", file=sys.stderr)
        # Title-slide version must match target_version exactly (error, not warning).
        # We inspect slide 1 only for this hard check; downstream slides may keep
        # historical version markers via intentionally_kept.
        if _target_ver and order:
            slide1_txt = " ".join(texts(z, order[0]))
            slide1_versions = re.findall(r"\b20\d{2}\.\d\b", slide1_txt)
            non_target_on_title = [v for v in slide1_versions if v != _target_ver]
            if non_target_on_title:
                report["errors"].append(
                    f"title slide carries non-target version marker(s) "
                    f"{non_target_on_title}; expected {_target_ver}"
                )
            elif not slide1_versions:
                report["warnings"].append(
                    f"title slide has no version marker; expected {_target_ver}"
                )
        # Version marker = any 20xx.y string that is NOT the target version (deck-wide warning)
        for m in re.finditer(rb"20\d\d\.\d", all_xml):
            marker = m.group(0).decode(errors="ignore")
            if _target_ver and marker != _target_ver:
                report["warnings"].append(f"non-target version marker remains: {marker}")
                break  # one warning is enough; report once
        if order and not texts(z, order[-1]):
            report["warnings"].append("final slide is blank")

        if args.plan:
            plan = safe_load_json(args.plan, "update_plan.json")
            # Defensive: refuse wholesale existing-slide notes replacement.
            # audit_gate catches this earlier; this is a last-line check on the
            # plan that actually shipped.
            for i, a in enumerate(plan.get("actions", [])):
                if a.get("type") in {"notes_update", "update_existing", "knowledge_check_update"} and a.get("speaker_notes"):
                    report["errors"].append(
                        f"action #{i} on slide {a.get('slide_number')} uses speaker_notes "
                        f"on an existing slide; must use notes_changes."
                    )
            if plan.get("schema_version") == "2.0":
                story = plan.get("story_model", {})
                # Derive work_dir from the plan file's own location if --work-dir not supplied.
                # The plan lives at <work_dir>/update_plan.json, so its parent IS the work_dir.
                effective_work_dir = args.work_dir
                if not effective_work_dir and args.plan:
                    effective_work_dir = str(Path(args.plan).parent)
                if not story and effective_work_dir:
                    sm_path = Path(effective_work_dir) / "story_model.json"
                    if sm_path.exists():
                        story = try_load_json(sm_path) or {}
                if not story.get("primary_message"):
                    report["errors"].append("story_model.primary_message missing")
                if not story.get("key_talking_points"):
                    report["errors"].append("story_model.key_talking_points missing")
                fv = plan.get("flow_validation") or (story.get("flow_validation") if story else None)
                if fv is None:
                    report["warnings"].append("flow_validation not found in plan or story model")
                elif fv.get("status") not in {"pass", "ok", "approved", "requires_source_augmented_review", "requires_human_or_source_augmented_review", None}:
                    report["warnings"].append(f"unexpected flow_validation status: {fv.get('status')}")
                unresolved = [a for a in plan.get("actions", []) if a.get("requires_human_authored_text")]
                if unresolved:
                    report["errors"].append(f"{len(unresolved)} actions still require human-authored text")

            added_positions = new_slide_positions(plan)
            if added_positions:
                highlighted_new_slides = []
                for pos in added_positions:
                    if pos <= len(order) and b"<a:highlight" in z.read(order[pos - 1]):
                        highlighted_new_slides.append(pos)
                if highlighted_new_slides:
                    report["errors"].append(
                        "new slide(s) contain highlight markup; new slides must rely "
                        f"on XML/package QA, not edit highlighting: {highlighted_new_slides}"
                    )

    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    raise SystemExit(EXIT_ERROR if report["errors"] else EXIT_OK)


if __name__ == "__main__":
    main()
