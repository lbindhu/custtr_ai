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


def resolve(base_part, target):
    parts = []
    for part in (base_part.rsplit("/", 1)[0] + "/" + target).split("/"):
        if part == "..":
            if parts:
                parts.pop()
        elif part and part != ".":
            parts.append(part)
    return "/".join(parts)


def text_of_shape(sp):
    return "\n".join((t.text or "") for t in sp.findall(".//" + q("a", "t"))).strip()


def text_items(root, include_placeholders=True):
    items = []
    for sp in root.findall(".//" + q("p", "sp")):
        if sp.find(q("p", "txBody")) is None:
            continue
        ph = sp.find(".//" + q("p", "ph"))
        ph_type = ph.attrib.get("type") if ph is not None else None
        if not include_placeholders and ph_type in {"sldImg", "hdr", "ftr", "dt", "sldNum"}:
            continue
        c = sp.find(".//" + q("p", "cNvPr"))
        txt = text_of_shape(sp)
        if txt:
            items.append({
                "shape_id": c.attrib.get("id") if c is not None else None,
                "shape_name": c.attrib.get("name") if c is not None else None,
                "placeholder_type": ph_type,
                "text": re.sub(r"\n{3,}", "\n\n", txt),
            })
    return items


def rels(z, part):
    rel_path = part.rsplit("/", 1)[0] + "/_rels/" + part.rsplit("/", 1)[1] + ".rels"
    if rel_path not in z.namelist():
        return []
    root = parse(z.read(rel_path))
    return [
        {
            "id": r.attrib.get("Id"),
            "type": r.attrib.get("Type"),
            "target": r.attrib.get("Target"),
            "resolved": resolve(part, r.attrib.get("Target", "")) if r.attrib.get("Target") else None,
        }
        for r in root.findall(q("rel", "Relationship"))
    ]


def ordered_slides(z):
    pres = parse(z.read("ppt/presentation.xml"))
    pres_rels = parse(z.read("ppt/_rels/presentation.xml.rels"))
    rmap = {r.attrib["Id"]: r.attrib["Target"] for r in pres_rels.findall(q("rel", "Relationship"))}
    return ["ppt/" + rmap[s.attrib[q("r", "id")]] for s in pres.findall(".//" + q("p", "sldId"))]


def notes_text(z, slide_path):
    for r in rels(z, slide_path):
        if r["type"] and r["type"].endswith("/notesSlide") and r["resolved"] in z.namelist():
            root = parse(z.read(r["resolved"]))
            return "\n\n".join(i["text"] for i in text_items(root, include_placeholders=False))
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("deck")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    deck = Path(args.deck)
    validate_pptx(deck)
    with zipfile.ZipFile(deck) as z:
        pres = parse(z.read("ppt/presentation.xml"))
        sldsz = pres.find(q("p", "sldSz"))
        slides = []
        for idx, spath in enumerate(ordered_slides(z), 1):
            root = parse(z.read(spath))
            texts = text_items(root)
            title = texts[0]["text"].splitlines()[0] if texts else ""
            visible_text = "\n".join(i["text"] for i in texts)
            slides.append({
                "slide_number": idx,
                "part": spath,
                "title": title,
                "texts": texts,
                "notes": notes_text(z, spath),
                "authoring_labels": [
                    i["text"] for i in texts
                    if "Fully Shared Slide" in i["text"]
                    or "Partially Shared Slide" in i["text"]
                    or re.search(r"Slide-\d+", i["text"])
                ],
                "is_blank": not bool(visible_text.strip()),
                "has_highlight": b"<a:highlight" in z.read(spath),
                "relationships": rels(z, spath),
            })

    out = {
        "deck": str(deck),
        "slide_count": len(slides),
        "slide_size": {
            "cx": int(sldsz.attrib.get("cx", 0)) if sldsz is not None else None,
            "cy": int(sldsz.attrib.get("cy", 0)) if sldsz is not None else None,
        },
        "slides": slides,
    }
    Path(args.output).write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
