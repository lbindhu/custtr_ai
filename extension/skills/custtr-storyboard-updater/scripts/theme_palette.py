#!/usr/bin/env python3
"""Extract reusable color roles from a PPTX theme."""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from pathlib import Path

from pptx.dml.color import RGBColor


def _rgb(hex_value: str, fallback: tuple[int, int, int]) -> RGBColor:
    value = (hex_value or "").strip().lstrip("#")
    if not re.fullmatch(r"[0-9A-Fa-f]{6}", value):
        return RGBColor(*fallback)
    return RGBColor(int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


@dataclass(frozen=True)
class ThemePalette:
    """Color roles used by generated storyboard slides."""

    background: RGBColor
    accent: RGBColor
    sub_accent: RGBColor
    tertiary: RGBColor
    dark: RGBColor
    card: RGBColor
    neutral: RGBColor
    body_text: RGBColor
    inverted_text: RGBColor
    badge_fill: RGBColor = RGBColor(255, 255, 0)
    badge_text: RGBColor = RGBColor(0, 0, 0)

    @property
    def header(self) -> RGBColor:
        return self.sub_accent


def default_palette() -> ThemePalette:
    """Return the legacy AMD-dark fallback palette."""

    return ThemePalette(
        background=RGBColor(0, 0, 0),
        accent=RGBColor(237, 28, 36),
        sub_accent=RGBColor(0, 60, 80),
        tertiary=RGBColor(193, 169, 104),
        dark=RGBColor(22, 22, 22),
        card=RGBColor(38, 38, 38),
        neutral=RGBColor(157, 159, 162),
        body_text=RGBColor(0, 0, 0),
        inverted_text=RGBColor(255, 255, 255),
    )


def _extract_scheme(theme_xml: str) -> dict[str, str]:
    return {
        name: value
        for name, value in re.findall(
            r"<a:(\w+)>\s*<a:srgbClr\s+val=\"([0-9A-Fa-f]{6})\"",
            theme_xml,
        )
    }


def load_theme_palette(deck_path: str | Path | None) -> ThemePalette:
    """Load scheme colors from ``ppt/theme/theme1.xml``.

    Missing or malformed decks fall back to the legacy palette so one-off test
    fixtures and partially generated PPTX files remain usable.
    """

    fallback = default_palette()
    if not deck_path:
        return fallback

    try:
        with zipfile.ZipFile(deck_path) as z:
            theme_xml = z.read("ppt/theme/theme1.xml").decode("utf-8", "replace")
    except (OSError, KeyError, zipfile.BadZipFile):
        return fallback

    scheme = _extract_scheme(theme_xml)
    return ThemePalette(
        background=_rgb(scheme.get("dk1", ""), (0, 0, 0)),
        accent=_rgb(scheme.get("accent1", ""), (237, 28, 36)),
        sub_accent=_rgb(scheme.get("accent4", ""), (0, 60, 80)),
        tertiary=_rgb(scheme.get("accent5", ""), (193, 169, 104)),
        dark=_rgb(scheme.get("dk2", ""), (22, 22, 22)),
        card=_rgb(scheme.get("accent2", ""), (38, 38, 38)),
        neutral=_rgb(scheme.get("accent3", "") or scheme.get("lt2", ""), (157, 159, 162)),
        body_text=_rgb(scheme.get("dk1", ""), (0, 0, 0)),
        inverted_text=_rgb(scheme.get("lt1", ""), (255, 255, 255)),
    )
