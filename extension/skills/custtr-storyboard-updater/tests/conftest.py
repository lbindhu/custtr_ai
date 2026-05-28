"""Shared fixtures for custtr-storyboard-updater tests."""

import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


# ── Minimal OOXML slide XML ──────────────────────────────────────────

SLIDE_XML_TEMPLATE = """\
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
       xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
       xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <p:cSld>
    <p:spTree>
      <p:sp>
        <p:txBody>
          {paragraphs}
        </p:txBody>
      </p:sp>
    </p:spTree>
  </p:cSld>
</p:sld>
"""


def make_slide_xml(text_lines):
    """Build a minimal slide XML string with one shape containing the given lines."""
    paras = []
    for line in text_lines:
        paras.append(
            f'<a:p><a:r><a:rPr lang="en-US"/><a:t>{line}</a:t></a:r>'
            f'<a:endParaRPr lang="en-US"/></a:p>'
        )
    return SLIDE_XML_TEMPLATE.format(paragraphs="\n".join(paras))


# ── Minimal notes XML ────────────────────────────────────────────────

NOTES_XML_TEMPLATE = """\
<p:notes xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
         xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
         xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <p:cSld>
    <p:spTree>
      <p:sp>
        <p:nvSpPr><p:nvPr><p:ph type="body"/></p:nvPr></p:nvSpPr>
        <p:txBody>
          {paragraphs}
        </p:txBody>
      </p:sp>
    </p:spTree>
  </p:cSld>
</p:notes>
"""


def make_notes_xml(text_lines):
    """Build a minimal notes XML string with one body placeholder."""
    paras = []
    for line in text_lines:
        paras.append(
            f'<a:p><a:r><a:rPr lang="en-US"/><a:t>{line}</a:t></a:r>'
            f'<a:endParaRPr lang="en-US"/></a:p>'
        )
    return NOTES_XML_TEMPLATE.format(paragraphs="\n".join(paras))


# ── Sample stale_terms documents ─────────────────────────────────────

@pytest.fixture
def sample_stale_terms():
    return {
        "stale_terms": [
            {"token": "Radeon Pro W7900", "replacement": "Radeon PRO W7900"},
            {
                "token": "ROCm 5.x",
                "replacement": "ROCm 6.x",
                "skip_if_preceded_by": ["legacy "],
                "skip_if_followed_by": [" (deprecated)"],
            },
            {"token": "MI250X", "replacement": "MI300X"},
        ],
        "intentionally_kept": [
            {"token": "MI250X", "on_slides": [3, 7]},
        ],
    }
