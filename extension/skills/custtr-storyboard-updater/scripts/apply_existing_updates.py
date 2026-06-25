#!/usr/bin/env python3
import argparse
import copy
import difflib
import json
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ooxml_helpers import NS, q, parse, out_xml, ordered_slides, shape_text, text_shapes, validate_pptx, add_highlight, _force_dark_fill  # noqa: E402
from json_helpers import safe_load_json  # noqa: E402



def _extract_templates(tx):
    """Return (pPr_template, rPr_template) from the first paragraph/run of txBody."""
    pPr_tmpl = None
    rPr_tmpl = None
    for p in tx.findall(q("a", "p")):
        if pPr_tmpl is None:
            pp = p.find(q("a", "pPr"))
            if pp is not None:
                pPr_tmpl = copy.deepcopy(pp)
        for r in p.findall(q("a", "r")):
            rp = r.find(q("a", "rPr"))
            if rp is not None and rPr_tmpl is None:
                rPr_tmpl = copy.deepcopy(rp)
                for old_hl in list(rPr_tmpl.findall(q("a", "highlight"))):
                    rPr_tmpl.remove(old_hl)
                rPr_tmpl.attrib.pop("strike", None)
            if pPr_tmpl is not None and rPr_tmpl is not None:
                break
        if pPr_tmpl is not None and rPr_tmpl is not None:
            break
    if rPr_tmpl is None:
        rPr_tmpl = ET.Element(q("a", "rPr"), {"lang": "en-US"})
    return pPr_tmpl, rPr_tmpl


def _make_run(parent, text, rPr_tmpl, highlight=False, strike=False):
    """Append a run to parent, cloning rPr_tmpl for all properties."""
    r = ET.SubElement(parent, q("a", "r"))
    rpr = copy.deepcopy(rPr_tmpl)
    if strike:
        rpr.set("strike", "sngStrike")
    else:
        rpr.attrib.pop("strike", None)
    if highlight:
        add_highlight(rpr)
    r.append(rpr)
    t = ET.SubElement(r, q("a", "t"))
    t.text = text
    if text and (text[0] == " " or text[-1] == " "):
        t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")


_PARA_LEVEL_THRESHOLD = 0.45  # similarity ratio below this → paragraph-level diff for a line


def set_text_diff(sp, old_text, new_text):
    """Replace all paragraphs in txBody with a threshold-based diff.

    For each line pair:
      - Pure insertion (no old line): one highlighted paragraph.
      - Pure deletion (no new line): one struck+highlighted paragraph.
      - similarity >= threshold: char-level inline diff (good for small token edits).
      - similarity < threshold: paragraph-level — old line struck+highlighted, then new
        line highlighted as a separate paragraph. This keeps heavily rewritten lines
        readable instead of producing a fragmented run soup.
    """
    tx = sp.find(q("p", "txBody"))
    pPr_tmpl, rPr_tmpl = _extract_templates(tx)

    for p in list(tx.findall(q("a", "p"))):
        tx.remove(p)

    old_lines = old_text.splitlines() or [""]
    new_lines = new_text.splitlines() or [""]

    def _end_attrs():
        attrs = {"lang": rPr_tmpl.attrib.get("lang", "en-US")}
        sz = rPr_tmpl.attrib.get("sz")
        if sz:
            attrs["sz"] = sz
        return attrs

    def _para():
        p_el = ET.SubElement(tx, q("a", "p"))
        if pPr_tmpl is not None:
            p_el.append(copy.deepcopy(pPr_tmpl))
        return p_el

    for i in range(max(len(old_lines), len(new_lines))):
        old_line = old_lines[i] if i < len(old_lines) else ""
        new_line = new_lines[i] if i < len(new_lines) else ""

        if not old_line:
            p_el = _para()
            _make_run(p_el, new_line, rPr_tmpl, highlight=True)
            ET.SubElement(p_el, q("a", "endParaRPr"), _end_attrs())
        elif not new_line:
            p_el = _para()
            _make_run(p_el, old_line, rPr_tmpl, highlight=True, strike=True)
            ET.SubElement(p_el, q("a", "endParaRPr"), _end_attrs())
        elif difflib.SequenceMatcher(None, old_line, new_line).ratio() < _PARA_LEVEL_THRESHOLD:
            p_old = _para()
            _make_run(p_old, old_line, rPr_tmpl, highlight=True, strike=True)
            ET.SubElement(p_old, q("a", "endParaRPr"), _end_attrs())
            p_new = _para()
            _make_run(p_new, new_line, rPr_tmpl, highlight=True)
            ET.SubElement(p_new, q("a", "endParaRPr"), _end_attrs())
        else:
            p_el = _para()
            for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, old_line, new_line, autojunk=False).get_opcodes():
                if tag == "equal":
                    _make_run(p_el, new_line[j1:j2], rPr_tmpl)
                elif tag == "delete":
                    _make_run(p_el, old_line[i1:i2], rPr_tmpl, highlight=True, strike=True)
                elif tag == "insert":
                    _make_run(p_el, new_line[j1:j2], rPr_tmpl, highlight=True)
                elif tag == "replace":
                    _make_run(p_el, old_line[i1:i2], rPr_tmpl, highlight=True, strike=True)
                    _make_run(p_el, new_line[j1:j2], rPr_tmpl, highlight=True)
            ET.SubElement(p_el, q("a", "endParaRPr"), _end_attrs())


def fragment_replace(root, find_fragment, replace_fragment):
    """Surgical in-place replacement of a text fragment that may span multiple runs.

    Concatenates all <a:t> texts within each <a:p> paragraph, searches for
    find_fragment in the concatenated string, then rewrites the paragraph with
    char-level diff highlighting. Unchanged prefix/suffix text stays plain;
    changed characters get yellow highlight + strikethrough for deletions.

    This handles the common case where PowerPoint splits text across multiple
    <a:r> runs within a paragraph (e.g. for ®/™ superscripts, mid-text
    formatting changes, or font fallbacks).
    """
    for sp in text_shapes(root):
        for p in sp.findall(".//" + q("a", "p")):
            para_text = "".join(t.text or "" for t in p.findall(".//" + q("a", "t")))
            if find_fragment not in para_text:
                continue

            pPr_tmpl = copy.deepcopy(p.find(q("a", "pPr"))) if p.find(q("a", "pPr")) is not None else None
            rPr_tmpl = ET.Element(q("a", "rPr"), {"lang": "en-US"})
            for r in p.findall(q("a", "r")):
                rp = r.find(q("a", "rPr"))
                if rp is not None:
                    rPr_tmpl = copy.deepcopy(rp)
                    for old_hl in list(rPr_tmpl.findall(q("a", "highlight"))):
                        rPr_tmpl.remove(old_hl)
                    rPr_tmpl.attrib.pop("strike", None)
                    break

            idx_in_para = para_text.index(find_fragment)
            prefix = para_text[:idx_in_para]
            suffix = para_text[idx_in_para + len(find_fragment):]

            for r in list(p.findall(q("a", "r"))):
                p.remove(r)
            if pPr_tmpl is not None and p.find(q("a", "pPr")) is None:
                p.insert(0, copy.deepcopy(pPr_tmpl))
            if prefix:
                _make_run(p, prefix, rPr_tmpl)
            for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(
                None, find_fragment, replace_fragment, autojunk=False
            ).get_opcodes():
                if tag == "equal":
                    _make_run(p, replace_fragment[j1:j2], rPr_tmpl)
                elif tag == "delete":
                    _make_run(p, find_fragment[i1:i2], rPr_tmpl, highlight=True, strike=True)
                elif tag == "insert":
                    _make_run(p, replace_fragment[j1:j2], rPr_tmpl, highlight=True)
                elif tag == "replace":
                    _make_run(p, find_fragment[i1:i2], rPr_tmpl, highlight=True, strike=True)
                    _make_run(p, replace_fragment[j1:j2], rPr_tmpl, highlight=True)
            if suffix:
                _make_run(p, suffix, rPr_tmpl)

            return True
    return False


def set_text(sp, text, highlight=True):
    tx = sp.find(q("p", "txBody"))
    pPr_tmpl, rPr_tmpl = _extract_templates(tx)

    for p in list(tx.findall(q("a", "p"))):
        tx.remove(p)

    for para in text.splitlines() or [""]:
        p = ET.SubElement(tx, q("a", "p"))
        if pPr_tmpl is not None:
            p.append(copy.deepcopy(pPr_tmpl))
        _make_run(p, para, rPr_tmpl, highlight=highlight)
        end_attrs = {"lang": rPr_tmpl.attrib.get("lang", "en-US")}
        sz = rPr_tmpl.attrib.get("sz")
        if sz:
            end_attrs["sz"] = sz
        ET.SubElement(p, q("a", "endParaRPr"), end_attrs)


def remove_shapes_by_text(root, texts):
    parents = {child: parent for parent in root.iter() for child in parent}
    removed = 0
    for sp in list(text_shapes(root)):
        if shape_text(sp) in texts:
            parent = parents.get(sp)
            if parent is not None:
                parent.remove(sp)
                removed += 1
    return removed


def resolve(base, target):
    parts = []
    for part in (base.rsplit("/", 1)[0] + "/" + target).split("/"):
        if part == "..":
            if parts:
                parts.pop()
        elif part and part != ".":
            parts.append(part)
    return "/".join(parts)


def notes_path_for(z, slide_path):
    rel_path = slide_path.rsplit("/", 1)[0] + "/_rels/" + slide_path.rsplit("/", 1)[1] + ".rels"
    if rel_path not in z.namelist():
        return None
    rels = parse(z.read(rel_path))
    for r in rels.findall(q("rel", "Relationship")):
        if r.attrib.get("Type", "").endswith("/notesSlide"):
            return resolve(slide_path, r.attrib["Target"])
    return None


def get_notes_text(root):
    """Return the full plain-text content of the notes body placeholder."""
    for sp in root.findall(".//" + q("p", "sp")):
        ph = sp.find(".//" + q("p", "ph"))
        if ph is not None and ph.attrib.get("type") == "body":
            return "".join(t.text or "" for t in sp.findall(".//" + q("a", "t")))
    return ""


def apply_notes_changes(root, notes_changes, slide_no=None, misses=None):
    """Apply {match_fragment, replacement_fragment} entries to the notes body.

    Finds the paragraph containing match_fragment and rewrites only that
    fragment. Unchanged prefix/suffix text stays plain. Inserted text is
    highlighted; deleted/replaced text is struck+highlighted. This prevents the
    common failure mode where an additive note like "add XXX" turns into a
    wholesale notes replacement.
    """
    body_sp = None
    for sp in root.findall(".//" + q("p", "sp")):
        ph = sp.find(".//" + q("p", "ph"))
        if ph is not None and ph.attrib.get("type") == "body":
            body_sp = sp
            break
    if body_sp is None:
        msg = "notes body placeholder not found"
        if misses is not None:
            misses.append({"slide_number": slide_no, "kind": "notes_changes", "match_text": "", "error": msg})
        print(f"ERROR: {msg} — notes_changes skipped", file=sys.stderr)
        return

    tx = body_sp.find(q("p", "txBody"))
    if tx is None:
        msg = "notes txBody not found"
        if misses is not None:
            misses.append({"slide_number": slide_no, "kind": "notes_changes", "match_text": "", "error": msg})
        print(f"ERROR: {msg} — notes_changes skipped", file=sys.stderr)
        return

    for idx, change in enumerate(notes_changes):
        match_frag = change.get("match_fragment", "")
        repl_frag = change.get("replacement_fragment", "")
        if not match_frag or not repl_frag:
            msg = "notes_changes requires non-empty match_fragment and replacement_fragment"
            if misses is not None:
                misses.append({
                    "slide_number": slide_no,
                    "kind": "notes_changes",
                    "match_text": match_frag,
                    "error": msg,
                    "change_index": idx,
                })
            print(f"ERROR: {msg} on slide {slide_no}", file=sys.stderr)
            continue

        found = False
        paragraphs = list(tx.findall(q("a", "p")))
        for p in paragraphs:
            para_text = "".join(t.text or "" for t in p.findall(".//" + q("a", "t")))
            if match_frag not in para_text:
                continue

            pPr_tmpl = copy.deepcopy(p.find(q("a", "pPr"))) if p.find(q("a", "pPr")) is not None else None
            rPr_tmpl = ET.Element(q("a", "rPr"), {"lang": "en-US"})
            for r in p.findall(q("a", "r")):
                rp = r.find(q("a", "rPr"))
                if rp is not None:
                    rPr_tmpl = copy.deepcopy(rp)
                    for old_hl in list(rPr_tmpl.findall(q("a", "highlight"))):
                        rPr_tmpl.remove(old_hl)
                    rPr_tmpl.attrib.pop("strike", None)
                    break

            idx_in_para = para_text.index(match_frag)
            prefix = para_text[:idx_in_para]
            suffix = para_text[idx_in_para + len(match_frag):]

            # Rewrite p in-place with an inline diff of just the changed fragment.
            for r in list(p.findall(q("a", "r"))):
                p.remove(r)
            if pPr_tmpl is not None and p.find(q("a", "pPr")) is None:
                p.insert(0, copy.deepcopy(pPr_tmpl))
            if prefix:
                _make_run(p, prefix, rPr_tmpl)
            for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(
                None, match_frag, repl_frag, autojunk=False
            ).get_opcodes():
                if tag == "equal":
                    _make_run(p, repl_frag[j1:j2], rPr_tmpl)
                elif tag == "delete":
                    _make_run(p, match_frag[i1:i2], rPr_tmpl, highlight=True, strike=True)
                elif tag == "insert":
                    _make_run(p, repl_frag[j1:j2], rPr_tmpl, highlight=True)
                elif tag == "replace":
                    _make_run(p, match_frag[i1:i2], rPr_tmpl, highlight=True, strike=True)
                    _make_run(p, repl_frag[j1:j2], rPr_tmpl, highlight=True)
            if suffix:
                _make_run(p, suffix, rPr_tmpl)

            found = True
            break

        if not found:
            if misses is not None:
                misses.append({
                    "slide_number": slide_no,
                    "kind": "notes_changes",
                    "match_text": match_frag,
                    "error": "match_fragment not found in any notes paragraph",
                    "change_index": idx,
                })
            print(f"ERROR: notes match_fragment not found in any paragraph on slide {slide_no}: {match_frag[:80]!r}", file=sys.stderr)


def _lenient_match(haystack, needle):
    """Return True if haystack == needle after stripping leading/trailing
    whitespace and collapsing internal runs of whitespace to a single space."""
    def norm(s):
        return " ".join(s.split())
    return norm(haystack) == norm(needle)


def _suggest_closest(target, candidates, k=3):
    """Return the top-k closest shape texts to `target`."""
    scored = []
    for s in candidates:
        if not s:
            continue
        scored.append((difflib.SequenceMatcher(None, target, s).ratio(), s))
    scored.sort(reverse=True)
    return [s for _, s in scored[:k]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deck", required=True)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--lenient-whitespace", action="store_true",
                    help="If an exact match_text lookup fails, retry after whitespace normalization.")
    ap.add_argument("--misses-output",
                    help="Write structured miss records here (default: <output_dir>/apply_misses.json).")
    args = ap.parse_args()

    plan = safe_load_json(args.plan, "update_plan.json")
    validate_pptx(args.deck)
    with zipfile.ZipFile(args.deck, "r") as zin:
        data = {item.filename: zin.read(item.filename) for item in zin.infolist()}

    misses = []

    def try_match(root, match_text, replacement_text, slide_no, kind):
        shapes = list(text_shapes(root))
        for sp in shapes:
            if shape_text(sp) == match_text:
                set_text_diff(sp, match_text, replacement_text)
                return True
        if args.lenient_whitespace:
            for sp in shapes:
                if _lenient_match(shape_text(sp), match_text):
                    print(f"WARNING: lenient whitespace match on slide {slide_no} for {match_text[:60]!r} — fix the plan's match_text to match exact shape text.")
                    actual = shape_text(sp)
                    set_text_diff(sp, actual, replacement_text)
                    return True
        candidates = [shape_text(sp) for sp in shapes]
        suggestions = _suggest_closest(match_text, candidates)
        misses.append({
            "slide_number": slide_no,
            "kind": kind,
            "match_text": match_text,
            "closest_actual_shape_texts": suggestions,
        })
        print(
            f"ERROR: no shape on slide {slide_no} matched match_text "
            f"(kind={kind}). Closest shapes:",
            file=sys.stderr,
        )
        for c in suggestions:
            print(f"  - {c!r}", file=sys.stderr)
        return False

    with zipfile.ZipFile(args.deck, "r") as z:
        order = ordered_slides(z)
        for action in plan.get("actions", []):
            atype = action.get("type")
            if atype not in {"update_existing", "knowledge_check_update", "notes_update", "fragment_replace"}:
                continue
            slide_no = action.get("slide_number")
            if not slide_no:
                slide_no = action.get("slide")
                if slide_no:
                    aid = action.get("action_id", f"#{i}")
                    print(f"WARNING: action {aid} uses 'slide' instead of 'slide_number' — fix the plan", file=sys.stderr)
            if not slide_no:
                aid = action.get("action_id", f"#{i}")
                print(f"ERROR: action {aid} has no slide_number — skipping", file=sys.stderr)
                misses.append({"slide_number": None, "kind": atype, "match_text": "", "error": "no slide_number field"})
                continue
            slide_path = order[slide_no - 1]
            root = parse(data[slide_path])

            if atype == "fragment_replace":
                hit = fragment_replace(root, action["find_fragment"], action["replace_fragment"])
                if not hit:
                    misses.append({
                        "slide_number": slide_no,
                        "kind": "fragment_replace",
                        "match_text": action["find_fragment"],
                    })
                    print(f"ERROR: fragment not found on slide {slide_no}: {action['find_fragment']!r}", file=sys.stderr)
                data[slide_path] = out_xml(root)
                continue

            if "remove_texts" in action:
                remove_shapes_by_text(root, set(action["remove_texts"]))

            if "match_text" in action and "replacement_text" in action:
                try_match(root, action["match_text"], action["replacement_text"], slide_no, "match_text")

            for repl in action.get("replacements", []):
                if repl.get("match_text"):
                    try_match(root, repl["match_text"], repl.get("replacement_text", ""), slide_no, "replacement")

            data[slide_path] = out_xml(root)

            if action.get("speaker_notes"):
                misses.append({
                    "slide_number": slide_no,
                    "kind": "speaker_notes",
                    "match_text": "",
                    "error": "speaker_notes is forbidden for existing-slide updates; use notes_changes",
                })
                print(
                    f"ERROR: action on slide {slide_no} uses speaker_notes for an existing slide; "
                    "use notes_changes instead.",
                    file=sys.stderr,
                )
                continue

            if action.get("notes_changes"):
                npath = notes_path_for(z, slide_path)
                if npath and npath in data:
                    nroot = parse(data[npath])
                    apply_notes_changes(nroot, action["notes_changes"], slide_no=slide_no, misses=misses)
                    data[npath] = out_xml(nroot)
                else:
                    misses.append({
                        "slide_number": slide_no,
                        "kind": "notes_changes",
                        "match_text": "",
                        "error": "notes slide not found",
                    })
                    print(f"ERROR: notes slide not found for slide {slide_no}", file=sys.stderr)

    with zipfile.ZipFile(args.output, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        for name, blob in data.items():
            zout.writestr(name, blob)

    misses_path = Path(args.misses_output) if args.misses_output else Path(args.output).parent / "apply_misses.json"
    misses_path.write_text(json.dumps(misses, indent=2, ensure_ascii=False), encoding="utf-8")
    print(args.output)
    if misses:
        print(f"ERROR: {len(misses)} match(es) failed; see {misses_path}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
