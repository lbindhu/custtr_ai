"""Tests for apply_existing_updates.apply_notes_changes()."""

from xml.etree import ElementTree as ET

from conftest import make_notes_xml
from ooxml_helpers import q
from apply_existing_updates import apply_notes_changes


def _notes_text(root):
    """Concatenate all non-struck <a:t> text in the notes body."""
    parts = []
    for sp in root.findall(".//" + q("p", "sp")):
        ph = sp.find(".//" + q("p", "ph"))
        if ph is not None and ph.attrib.get("type") == "body":
            for r in sp.findall(".//" + q("a", "r")):
                rpr = r.find(q("a", "rPr"))
                if rpr is not None and rpr.attrib.get("strike") == "sngStrike":
                    continue
                t = r.find(q("a", "t"))
                if t is not None and t.text:
                    parts.append(t.text)
    return "".join(parts)


class TestApplyNotesChanges:
    def test_single_match(self):
        xml = make_notes_xml(["ROCm 5.x enables HPC workloads on AMD GPUs."])
        root = ET.fromstring(xml)
        changes = [{"match_fragment": "ROCm 5.x", "replacement_fragment": "ROCm 6.x"}]
        apply_notes_changes(root, changes)
        assert "ROCm 6.x" in _notes_text(root)

    def test_not_found_records_miss(self):
        xml = make_notes_xml(["Nothing relevant here."])
        root = ET.fromstring(xml)
        changes = [{"match_fragment": "nonexistent", "replacement_fragment": "replacement"}]
        misses = []
        apply_notes_changes(root, changes, slide_no=5, misses=misses)
        assert len(misses) == 1
        assert misses[0]["kind"] == "notes_changes"

    def test_empty_fragment_records_miss(self):
        xml = make_notes_xml(["Some notes text."])
        root = ET.fromstring(xml)
        changes = [{"match_fragment": "", "replacement_fragment": "something"}]
        misses = []
        apply_notes_changes(root, changes, slide_no=1, misses=misses)
        assert len(misses) == 1

    def test_multi_paragraph(self):
        xml = make_notes_xml([
            "First paragraph with ROCm 5.x info.",
            "Second paragraph is unchanged.",
        ])
        root = ET.fromstring(xml)
        changes = [{"match_fragment": "ROCm 5.x", "replacement_fragment": "ROCm 6.2"}]
        apply_notes_changes(root, changes)
        text = _notes_text(root)
        assert "ROCm 6.2" in text
        assert "Second paragraph is unchanged." in text

    def test_no_body_placeholder(self):
        xml = """\
<p:notes xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
         xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld><p:spTree></p:spTree></p:cSld>
</p:notes>"""
        root = ET.fromstring(xml)
        changes = [{"match_fragment": "foo", "replacement_fragment": "bar"}]
        misses = []
        apply_notes_changes(root, changes, slide_no=1, misses=misses)
        assert len(misses) == 1
        assert "not found" in misses[0]["error"]
