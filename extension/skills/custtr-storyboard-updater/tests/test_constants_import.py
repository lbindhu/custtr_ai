"""Smoke test: verify all consumer scripts import without error."""

import importlib


def test_constants_importable():
    mod = importlib.import_module("constants")
    assert hasattr(mod, "VALID_ACTION_TYPES")
    assert hasattr(mod, "MUTATING_ACTIONS")
    assert hasattr(mod, "VERSION_RE")
    assert hasattr(mod, "SUMMARY_RE")
    assert hasattr(mod, "KNOWLEDGE_RE")
    assert hasattr(mod, "BANNED_OPENERS")
    assert hasattr(mod, "DATASHEET_HEADINGS")
    assert hasattr(mod, "DATASHEET_BULLET_RE")


def test_ooxml_helpers_importable():
    mod = importlib.import_module("ooxml_helpers")
    assert hasattr(mod, "NS")
    assert hasattr(mod, "q")
    assert hasattr(mod, "parse")
    assert hasattr(mod, "out_xml")
    assert hasattr(mod, "ordered_slides")
    assert hasattr(mod, "shape_text")
    assert hasattr(mod, "text_shapes")

def test_layout_constants_removed():
    mod = importlib.import_module("constants")
    assert not hasattr(mod, "VALID_SLIDE_LAYOUTS")
    assert not hasattr(mod, "LAYOUT_DATA_FIELDS")
