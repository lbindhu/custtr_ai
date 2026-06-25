"""Tests for extracting deck theme colors for generated slides."""

import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from pptx.dml.color import RGBColor  # noqa: E402
from theme_palette import ThemePalette, load_theme_palette  # noqa: E402


def test_load_theme_palette_reads_scheme_colors(tmp_path):
    deck = tmp_path / "deck.pptx"
    theme_xml = """\
<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
  <a:themeElements>
    <a:clrScheme name="Custom">
      <a:dk1><a:srgbClr val="010203"/></a:dk1>
      <a:lt1><a:srgbClr val="FEFDFC"/></a:lt1>
      <a:dk2><a:srgbClr val="111213"/></a:dk2>
      <a:accent1><a:srgbClr val="AABBCC"/></a:accent1>
      <a:accent2><a:srgbClr val="223344"/></a:accent2>
      <a:accent3><a:srgbClr val="556677"/></a:accent3>
      <a:accent4><a:srgbClr val="8899AA"/></a:accent4>
      <a:accent5><a:srgbClr val="BBCCDD"/></a:accent5>
    </a:clrScheme>
  </a:themeElements>
</a:theme>
"""
    with zipfile.ZipFile(deck, "w") as z:
        z.writestr("ppt/theme/theme1.xml", theme_xml)

    palette = load_theme_palette(deck)

    assert isinstance(palette, ThemePalette)
    assert palette.accent == RGBColor(0xAA, 0xBB, 0xCC)
    assert palette.dark == RGBColor(0x11, 0x12, 0x13)
    assert palette.card == RGBColor(0x22, 0x33, 0x44)
    assert palette.body_text == RGBColor(0x01, 0x02, 0x03)
    assert palette.inverted_text == RGBColor(0xFE, 0xFD, 0xFC)


def test_load_theme_palette_falls_back_for_missing_theme(tmp_path):
    deck = tmp_path / "deck.pptx"
    with zipfile.ZipFile(deck, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")

    palette = load_theme_palette(deck)

    assert palette.accent == RGBColor(237, 28, 36)
    assert palette.inverted_text == RGBColor(255, 255, 255)
