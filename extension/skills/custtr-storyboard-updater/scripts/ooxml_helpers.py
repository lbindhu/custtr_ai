#!/usr/bin/env python3
"""Shared OOXML / DrawingML helpers for PPTX manipulation scripts.

Extracted from apply_existing_updates.py so that post_apply_check.py
and any future consumers share the same namespace dict and utilities.
"""

import sys
import zipfile
from xml.etree import ElementTree as ET

# ── Namespaces ────────────────────────────────────────────────────────

NS = {
    "a":   "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p":   "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r":   "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}

_OOXML_NS = {
    "a":    "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p":    "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r":    "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "a14":  "http://schemas.microsoft.com/office/drawing/2010/main",
    "a16":  "http://schemas.microsoft.com/office/drawing/2014/main",
    "asvg": "http://schemas.microsoft.com/office/drawing/2016/SVG/main",
    "mc":   "http://schemas.openxmlformats.org/markup-compatibility/2006",
    "p14":  "http://schemas.microsoft.com/office/powerpoint/2010/main",
}
for _prefix, _uri in _OOXML_NS.items():
    ET.register_namespace(_prefix, _uri)


# ── Core helpers ──────────────────────────────────────────────────────

def q(ns, tag):
    """Build a Clark-notation tag: {namespace_uri}tag."""
    return f"{{{NS[ns]}}}{tag}"


def parse(blob):
    """Parse an XML byte string into an ElementTree Element."""
    return ET.fromstring(blob)


_OOXML_DECL = b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'


def out_xml(root):
    """Serialize an Element back to OOXML-compatible bytes with declaration."""
    body = ET.tostring(root, encoding="unicode")
    return _OOXML_DECL + body.encode("utf-8")


def ordered_slides(z):
    """Return a list of slide paths in presentation order from a ZipFile."""
    pres = parse(z.read("ppt/presentation.xml"))
    rels = parse(z.read("ppt/_rels/presentation.xml.rels"))
    rmap = {r.attrib["Id"]: r.attrib["Target"] for r in rels.findall(q("rel", "Relationship"))}
    return ["ppt/" + rmap[s.attrib[q("r", "id")]] for s in pres.findall(".//" + q("p", "sldId"))]


def shape_text(sp):
    """Extract all text from a shape element, joining <a:t> nodes with newlines."""
    return "\n".join((t.text or "") for t in sp.findall(".//" + q("a", "t"))).strip()


def text_shapes(root):
    """Return all <p:sp> elements that contain a <p:txBody>."""
    return [sp for sp in root.findall(".//" + q("p", "sp")) if sp.find(q("p", "txBody")) is not None]


def _force_dark_fill(rpr):
    """Force dark text (tx1) on a highlighted run so it's visible on yellow."""
    for sf in list(rpr.findall(q("a", "solidFill"))):
        rpr.remove(sf)
    sf = ET.Element(q("a", "solidFill"))
    ET.SubElement(sf, q("a", "schemeClr"), {"val": "tx1"})
    rpr.insert(0, sf)


def add_highlight(rpr):
    """Inject <a:highlight val=FFFF00> at the correct OOXML position and force dark text.

    OOXML requires <a:highlight> after <a:effectLst> and before <a:uLnTx>.
    PowerPoint silently ignores highlights placed elsewhere (e.g. appended at end).
    """
    _force_dark_fill(rpr)
    for old in list(rpr.findall(q("a", "highlight"))):
        rpr.remove(old)
    hl = ET.Element(q("a", "highlight"))
    ET.SubElement(hl, q("a", "srgbClr"), {"val": "FFFF00"})
    children = list(rpr)
    effect = rpr.find(q("a", "effectLst"))
    uln = rpr.find(q("a", "uLnTx"))
    fill = rpr.find(q("a", "solidFill"))
    if effect is not None:
        rpr.insert(children.index(effect) + 1, hl)
    elif uln is not None:
        rpr.insert(children.index(uln), hl)
    elif fill is not None:
        rpr.insert(children.index(fill) + 1, hl)
    else:
        rpr.append(hl)


def validate_pptx(path):
    """Check that *path* is a valid ZIP with core PPTX structure.

    Exits with a clear error if the file is not a ZIP, is corrupted,
    or is missing required PPTX internals.
    """
    import os
    if not os.path.isfile(path):
        print(f"ERROR: file not found: {path}", file=sys.stderr)
        raise SystemExit(2)
    if not zipfile.is_zipfile(path):
        print(f"ERROR: not a valid ZIP/PPTX file: {path}", file=sys.stderr)
        raise SystemExit(2)
    with zipfile.ZipFile(path) as z:
        bad = z.testzip()
        if bad:
            print(f"ERROR: ZIP corruption in {path} at entry: {bad}", file=sys.stderr)
            raise SystemExit(2)
        names = z.namelist()
        if "[Content_Types].xml" not in names:
            print(f"ERROR: {path} is a ZIP but not a valid PPTX (missing [Content_Types].xml)", file=sys.stderr)
            raise SystemExit(2)
        has_slides = any(n.startswith("ppt/slides/slide") and n.endswith(".xml") for n in names)
        if not has_slides:
            print(f"ERROR: {path} contains no slides (no ppt/slides/slideN.xml entries)", file=sys.stderr)
            raise SystemExit(2)
