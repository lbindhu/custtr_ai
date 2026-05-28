"""Tests for apply_existing_updates.fragment_replace()."""

from xml.etree import ElementTree as ET

from conftest import make_slide_xml
from ooxml_helpers import q
from apply_existing_updates import fragment_replace


def _slide_text(root):
    """Concatenate all <a:t> text in a root, excluding struck-through runs."""
    parts = []
    for r in root.findall(".//" + q("a", "r")):
        rpr = r.find(q("a", "rPr"))
        strike = rpr is not None and rpr.attrib.get("strike") == "sngStrike"
        t = r.find(q("a", "t"))
        if t is not None and t.text:
            if not strike:
                parts.append(t.text)
    return "".join(parts)


def _has_highlight(root):
    return len(root.findall(".//" + q("a", "highlight"))) > 0


class TestFragmentReplace:
    def test_basic_replacement(self):
        xml = make_slide_xml(["Radeon Pro W7900 delivers performance"])
        root = ET.fromstring(xml)
        result = fragment_replace(root, "Pro W7900", "PRO W7900")
        assert result is True
        assert "PRO W7900" in _slide_text(root)
        assert _has_highlight(root)

    def test_not_found_returns_false(self):
        xml = make_slide_xml(["Nothing matches here"])
        root = ET.fromstring(xml)
        result = fragment_replace(root, "nonexistent fragment", "replacement")
        assert result is False

    def test_fragment_at_start(self):
        xml = make_slide_xml(["ROCm 5.x platform overview"])
        root = ET.fromstring(xml)
        result = fragment_replace(root, "ROCm 5.x", "ROCm 6.x")
        assert result is True
        text = _slide_text(root)
        assert "ROCm 6.x" in text
        assert "platform overview" in text

    def test_fragment_at_end(self):
        xml = make_slide_xml(["Powered by ROCm 5.x"])
        root = ET.fromstring(xml)
        result = fragment_replace(root, "ROCm 5.x", "ROCm 6.x")
        assert result is True
        text = _slide_text(root)
        assert text.startswith("Powered by ")
        assert "ROCm 6.x" in text

    def test_first_occurrence_only(self):
        xml = make_slide_xml(["MI250X vs MI250X comparison"])
        root = ET.fromstring(xml)
        result = fragment_replace(root, "MI250X", "MI300X")
        assert result is True
        text = _slide_text(root)
        assert "MI300X" in text
        assert "MI250X" in text

    def test_whitespace_preserved(self):
        xml = make_slide_xml(["  leading spaces and trailing  "])
        root = ET.fromstring(xml)
        result = fragment_replace(root, "leading spaces", "LEADING SPACES")
        assert result is True
        text = _slide_text(root)
        assert "LEADING SPACES" in text
