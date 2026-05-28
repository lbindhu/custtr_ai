#!/usr/bin/env python3
"""
Generate a standalone additions PPTX from plan actions using the MARP pipeline.

Handles layouts that produce visually superior output via MARP + AMD theme:
  - comparison_table: markdown table with teal header styling
  - cards:            styled card layout with bold headings and bullets
  - two_column:       two-column layout using <!-- _class: cols --> with divs
  - key_takeaway:     centered bold statement with teal accent

Diagram layouts (ascii_diagram, block_diagram) are NOT handled here —
they stay in create_additions_deck.py which produces native PPT shapes.

Pipeline:
  1. Read update_plan.json, filter for MARP-eligible actions
  2. Generate MARP markdown from structured data fields
  3. Export editable PPTX via gen_pptx_pdf.ps1
  4. Inject speaker notes via inject_notes.py
  5. Output final PPTX
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from constants import MARP_ELIGIBLE_LAYOUTS  # noqa: E402
from json_helpers import safe_load_json  # noqa: E402

FRONTMATTER = """\
---
marp: true
theme: amd
paginate: true
---
"""

TITLE_SLIDE_TEMPLATE = """\
<!-- _class: title -->

<style scoped>
section {{ background: #000000; }}
</style>

![w:180]({logo_path})

# {title}
## {subtitle}

{dateline}
"""

CLOSING_SLIDE_TEMPLATE = """\
<!-- _class: closing -->

<style scoped>
section {{ background: #000000; }}
</style>

![w:700]({watermark_path})
"""


def _resolve_image_path(skill_dir: str, relative: str) -> str:
    """Resolve an image path relative to the psas-amd-marp skill directory."""
    candidate = Path(skill_dir) / relative
    if candidate.exists():
        return candidate.as_posix()
    home = os.environ.get("USERPROFILE", os.environ.get("HOME", ""))
    candidate = Path(home) / ".claude/skills/psas-amd-marp" / relative
    if candidate.exists():
        return candidate.as_posix()
    return relative


def _render_comparison_table(action: dict) -> str:
    """Generate MARP markdown for a comparison_table layout."""
    table_spec = action.get("table", {})
    headers = table_spec.get("headers", ["Criteria", "Option A", "Option B"])
    rows = table_spec.get("rows", [])

    lines = []
    lines.append('<style scoped>')
    lines.append('section h1 { color: #00C2DE; }')
    lines.append('table { font-size: 0.72em; }')
    lines.append('</style>')
    lines.append('')
    lines.append('| ' + ' | '.join(str(h) for h in headers) + ' |')
    lines.append('|' + '|'.join('---' for _ in headers) + '|')
    for row in rows:
        cells = []
        for i, h in enumerate(headers):
            val = row[i] if i < len(row) else ""
            cells.append(str(val))
        lines.append('| ' + ' | '.join(cells) + ' |')

    return '\n'.join(lines)


def _render_cards(action: dict) -> str:
    """Generate MARP markdown for a cards layout."""
    cards = action.get("cards", [])

    lines = []
    lines.append('<style scoped>')
    lines.append('section h1 { color: #00C2DE; }')
    lines.append('</style>')
    lines.append('')
    for card in cards:
        heading = card.get("heading", "")
        lines.append(f'**{heading}**')
        for bullet in card.get("bullets", []):
            lines.append(f'- {bullet}')
        lines.append('')

    return '\n'.join(lines)


def _render_two_column(action: dict) -> str:
    """Generate MARP markdown for a two_column layout using cols class."""
    columns = action.get("columns", [{}, {}])

    lines = []
    lines.append('<!-- _class: cols -->')
    lines.append('')
    lines.append('<style scoped>')
    lines.append('section h1 { color: #00C2DE; }')
    lines.append('h2 { color: #00C2DE; font-size: 1.1em; }')
    lines.append('</style>')
    lines.append('')

    lines.append('<div>')
    lines.append('')
    col = columns[0] if columns else {}
    if col.get("heading"):
        lines.append(f'## {col["heading"]}')
        lines.append('')
    for bullet in col.get("bullets", []):
        lines.append(f'- {bullet}')
    lines.append('')
    lines.append('</div>')
    lines.append('')

    lines.append('<div>')
    lines.append('')
    col = columns[1] if len(columns) > 1 else {}
    if col.get("heading"):
        lines.append(f'## {col["heading"]}')
        lines.append('')
    for bullet in col.get("bullets", []):
        lines.append(f'- {bullet}')
    lines.append('')
    lines.append('</div>')

    return '\n'.join(lines)


def _render_key_takeaway(action: dict) -> str:
    """Generate MARP markdown for a key_takeaway layout."""
    statement = action.get("statement", action.get("learning_goal", ""))
    subtext = action.get("subtext", "")

    lines = []
    lines.append('<style scoped>')
    lines.append('section h1 { color: #00C2DE; }')
    lines.append('section { display: flex; flex-direction: column; justify-content: center; text-align: center; }')
    lines.append('p { font-size: 1.4em; }')
    lines.append('</style>')
    lines.append('')
    lines.append(f'**{statement}**')
    if subtext:
        lines.append('')
        lines.append(subtext)

    return '\n'.join(lines)


LAYOUT_RENDERERS = {
    "comparison_table": _render_comparison_table,
    "cards": _render_cards,
    "two_column": _render_two_column,
    "key_takeaway": _render_key_takeaway,
}


def generate_marp_markdown(actions: list[dict], skill_dir: str) -> str:
    """Assemble all MARP-eligible actions into a single .md file."""
    logo_path = _resolve_image_path(skill_dir, "images/amd-logo-dark.jpg")
    watermark_path = _resolve_image_path(skill_dir, "images/amd-text-watermark.png")

    parts = [FRONTMATTER]

    parts.append(TITLE_SLIDE_TEMPLATE.format(
        logo_path=logo_path,
        title="New Slides — MARP Additions",
        subtitle="Auto-generated from update plan",
        dateline="Generated by create_marp_additions.py",
    ))

    for action in actions:
        layout = action.get("slide_layout", "cards")
        renderer = LAYOUT_RENDERERS.get(layout)
        if not renderer:
            print(f"WARNING: no MARP renderer for layout '{layout}', skipping", file=sys.stderr)
            continue

        slide_lines = []
        slide_lines.append('---')
        slide_lines.append('')
        slide_lines.append(f'# {action.get("title", "Untitled")}')
        slide_lines.append('')
        slide_lines.append(renderer(action))

        source = action.get("source_footer") or action.get("source_basis")
        if source:
            if isinstance(source, list):
                source = ", ".join(str(s) for s in source)
            slide_lines.append('')
            slide_lines.append(f'*Source: {source}*')

        notes = action.get("speaker_notes", "")
        if notes:
            slide_lines.append('')
            slide_lines.append('<!--')
            slide_lines.append(notes)
            slide_lines.append('-->')

        parts.append('\n'.join(slide_lines))

    parts.append('\n---\n')
    parts.append(CLOSING_SLIDE_TEMPLATE.format(watermark_path=watermark_path))

    return '\n'.join(parts)


def export_marp_pptx(md_path: str, output_dir: str) -> str:
    """Run gen_pptx_pdf.ps1 to produce editable PPTX. Returns the PPTX path."""
    home = os.environ.get("USERPROFILE", os.environ.get("HOME", ""))
    script = Path(home) / ".claude/skills/psas-marp-export/gen_pptx_pdf.ps1"
    if not script.exists():
        raise FileNotFoundError(f"MARP export script not found: {script}")

    cmd = [
        "powershell.exe", "-ExecutionPolicy", "Bypass",
        "-File", str(script),
        "-InputFile", md_path,
        "-OutputDir", output_dir,
        "-SkipPdf",
        "-NoTimestamp",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(
            f"MARP export failed (rc={result.returncode}):\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    md_stem = Path(md_path).stem
    pptx_path = Path(output_dir) / f"{md_stem}.pptx"
    if not pptx_path.exists():
        candidates = list(Path(output_dir).glob(f"{md_stem}*.pptx"))
        if candidates:
            pptx_path = candidates[0]
        else:
            raise FileNotFoundError(
                f"Expected PPTX not found at {pptx_path}. "
                f"Export stdout: {result.stdout}"
            )

    return str(pptx_path)


def inject_speaker_notes(md_path: str, pptx_path: str, output_path: str) -> None:
    """Run inject_notes.py to add speaker notes to the PPTX."""
    home = os.environ.get("USERPROFILE", os.environ.get("HOME", ""))
    inject_script = Path(home) / ".claude/skills/psas-amd-marp/scripts/inject_notes.py"
    if not inject_script.exists():
        raise FileNotFoundError(f"inject_notes.py not found: {inject_script}")

    cmd = [
        sys.executable, str(inject_script),
        md_path, pptx_path,
        "--output", output_path,
    ]
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, env=env)
    if result.returncode != 0:
        raise RuntimeError(
            f"inject_notes failed (rc={result.returncode}):\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
    print(result.stdout, end="")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plan", required=True, help="Path to update_plan.json")
    ap.add_argument("--output", required=True, help="Output PPTX path")
    ap.add_argument("--skill-dir", default=None,
                    help="Path to psas-amd-marp skill directory (for images)")
    ap.add_argument("--keep-md", action="store_true",
                    help="Keep the intermediate .md file instead of cleaning up")
    args = ap.parse_args()

    skill_dir = args.skill_dir
    if not skill_dir:
        home = os.environ.get("USERPROFILE", os.environ.get("HOME", ""))
        skill_dir = str(Path(home) / ".claude/skills/psas-amd-marp")

    plan = safe_load_json(args.plan, "update_plan.json")
    all_actions = [a for a in plan.get("actions", []) if a.get("type") == "add_new_slide"]
    marp_actions = [a for a in all_actions if a.get("slide_layout") in MARP_ELIGIBLE_LAYOUTS]

    if not marp_actions:
        print("create_marp_additions: no MARP-eligible actions found, nothing to do.")
        sys.exit(0)

    print(f"create_marp_additions: {len(marp_actions)} MARP-eligible slides "
          f"(of {len(all_actions)} total add_new_slide actions)")

    md_content = generate_marp_markdown(marp_actions, skill_dir)

    output_dir = str(Path(args.output).parent)
    md_stem = Path(args.output).stem
    md_path = str(Path(output_dir) / f"{md_stem}.md")

    Path(md_path).write_text(md_content, encoding="utf-8")
    print(f"create_marp_additions: wrote MARP markdown -> {md_path}")

    try:
        raw_pptx = export_marp_pptx(md_path, output_dir)
        print(f"create_marp_additions: MARP export -> {raw_pptx}")

        inject_speaker_notes(md_path, raw_pptx, args.output)
        print(f"create_marp_additions: final PPTX -> {args.output}")

        if Path(raw_pptx).resolve() != Path(args.output).resolve() and Path(raw_pptx).exists():
            Path(raw_pptx).unlink()

    finally:
        if not args.keep_md and Path(md_path).exists():
            Path(md_path).unlink()


if __name__ == "__main__":
    main()
