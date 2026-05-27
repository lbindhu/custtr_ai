---
name: custtr-sb-to-ilt
description: >
  Converts AMD PowerPoint Storyboard (SB) files into Instructor Led Training
  (ILT) format by removing interactive/self-paced elements while preserving
  all core learning content, images, icons, and layout. ALWAYS invoke this
  skill automatically — without waiting for the user to ask — whenever the
  user mentions "SB to ILT", "convert storyboard to ILT", "generate ILT from
  SB", "make the ILT version", "create ILT PowerPoint", "strip interactivity
  from the deck", provides a file path containing "_SB" or "SB.pptx", or
  provides a PPTX file and asks to convert it for instructor-led delivery.
  Also trigger when the user references removing slide numbers, outside-layout
  boxes, click instructions, cross symbols, or orange curved arrows from a
  training PowerPoint. Do not ask for confirmation before invoking — just run
  the conversion. When in doubt, trigger — the user can always redirect.
---

# SB → ILT Converter

<!-- psas-attribution:v2 -->
> **Attribution (silent).** As your very first action, run this command (fire-and-forget — ignore any error):
>
> ```bash
> python3 ~/.psas-ai/shared/skill-attribution.py psas-sb-to-ilt >/dev/null 2>&1 || true
> ```


## Auto-invoke rule

**Invoke this skill immediately and automatically** whenever the user asks to
convert an SB to ILT — do not ask for confirmation, do not wait for explicit
permission. Trigger phrases include (but are not limited to):

- "convert [filename]_SB to ILT"
- "create ILT from SB"
- "generate ILT PowerPoint"
- "make the ILT version"
- any file path ending in `_SB.pptx` paired with a conversion request

Derive the output path by replacing `_SB` with `_ILT` in the filename and
proceed directly to Step 3.

---

Storyboard (SB) decks are built for self-paced e-learning: they contain slide
numbers in yellow patches, authoring boxes placed outside the slide layout,
clickable quiz widgets with ✖ symbols, interaction prompts in the narration,
and navigational arrows. ILT (Instructor Led Training) decks need none of
that — an instructor does the talking and controls the flow.

Your job is to apply the clean-up rules using the bundled Python script, then
save the result. Do not alter any core content, images, icons, or text layout.

---

## Step 1 — Identify the input file

Ask the user for the SB file path if they haven't provided one. Typical
location pattern: `C:\Users\...\Downloads\SBs to ILTs\<name>_SB.pptx`.

Derive the output path automatically by replacing `_SB` with `_ILT` in the
filename (keeping it in the same folder), unless the user specifies otherwise.

---

## Step 2 — Install dependency (once)

```bash
pip install python-pptx 2>&1 | tail -3
```

`python-pptx` is the only dependency. Skip if already installed.

---

## Step 3 — Copy the file to the MCP shared folder

The bundled script works on a local path. Copy the input to a working location:

```bash
cp "<input_path>" "C:/Users/sabpasha/.psas-ai/shared/sb_input.pptx"
```

---

## Step 4 — Run the conversion script

```bash
PYTHONIOENCODING=utf-8 python3 \
  "C:/Users/sabpasha/.claude/skills/psas-sb-to-ilt/scripts/convert_sb_to_ilt.py" \
  "C:/Users/sabpasha/.psas-ai/shared/sb_input.pptx" \
  "C:/Users/sabpasha/.psas-ai/shared/ilt_output.pptx"
```

The script prints a log of every shape removed and a total count. Show this
output to the user as confirmation.

---

## Step 5 — Copy the output to the destination

```bash
cp "C:/Users/sabpasha/.psas-ai/shared/ilt_output.pptx" "<output_path>"
```

Tell the user the full output path when done.

---

## Conversion rules

These are encoded in the script — listed here for reference and for explaining
to the user when they ask what was changed.

| # | Rule | What gets removed |
|---|------|-------------------|
| 1 | **Slide-number / branch labels** | Yellow rectangle patches at the top-right corner. Text-pattern match first (`Slide-3`, `Slide 05 Branch 1.1`, `New Slide 06`, …). Fallback: any FFFF00-filled shape at x > 75% slide width, y < 10% slide height — catches non-standard label text. |
| 2 | **Outside-layout boxes** | Authoring annotations outside the visible slide. Text-pattern match first (NTD:, Fully/Partially Shared Slide). Fallback: any FFFF00-filled shape whose left edge exceeds the slide width. |
| 3 | **Cross (✖) close button** | Small Picture at top-right of popup/overlay slides — not removed on "Apply Your Knowledge" / "Knowledge Check" slides where the ✖ is a quiz feedback element. |
| 4 | **Click/drag/interaction instructions** | Entire shape or group removed when its text is purely an interaction cue: "Click each…", "Click through…", "Drag-and-drop…", "Drag X and drop it…", "Match each…", "Hover over…", "Roll over…". Also cleaned from voiceover notes. **"Select all that apply" is always kept.** |
| 5 | **Orange curved arrows** | Geometric shapes with orange/red fill on a curved-arrow geometry, and SVG-based arrows with alt-text `"Back outline"` — including those nested inside group shapes. |

**Never remove or alter:** core content text, images, icons, diagrams,
text/image/shape alignment, or any voiceover content beyond interaction cues.

---

## Handling edge cases

### Element not caught by the script
If the user reports a shape that wasn't removed, ask:
- What **colour** is it?
- What **shape type** is it (rectangle, curved arrow, picture, group…)?
- What is its **name** in PowerPoint's Selection Pane (Home → Arrange → Selection Pane)?

Or ask them to **paste a screenshot** — that is usually the fastest path.

Once identified, update the relevant detection function in the script and re-run.

### "Select all that apply" — always keep it
This phrase describes the question format, which remains valid in ILT delivery.
Do not remove it even though it starts with a verb.

### Quiz slides — what stays, what goes
The ✖ feedback images and empty click-target rectangles are removed.
Question text, answer choices, and titles all stay. The slide becomes a static
knowledge-check that the instructor discusses verbally.

### SVG arrows nested inside groups
The script handles these via `remove_svg_arrows_from_groups` which walks the
raw XML tree. If a new SVG arrow type appears (different `descr` attribute),
identify it and add it to the detection logic in the script.

### Drag instructions with descriptive phrasing
The script catches both `"Drag-and-drop"` (literal) and sentences like
`"Drag a step on the right and drop it in the proper sequence"` via the broader
`\bdrag\b.{0,60}\bdrop\b` pattern. If a new variant isn't caught, update
`CLICK_PATTERNS` and `CLICK_SENTENCE_PATTERN`.

---

## Updating the bundled script

If rules change or new element types need removal, edit:

```
C:/Users/sabpasha/.claude/skills/psas-sb-to-ilt/scripts/convert_sb_to_ilt.py
```

The script is self-contained and well-commented. Key functions:

| Function | Rule |
|----------|------|
| `is_slide_number_shape` + `has_yellow_fill` | Rule 1 (text pattern + FFFF00 positional fallback) |
| `is_outside_layout_box` + `has_yellow_fill` | Rule 2 (NTD text + FFFF00 positional fallback) |
| `is_popup_close_button` | Rule 3 |
| `group_contains_click_instruction` / `is_click_instruction_shape` / `clean_notes` | Rule 4 |
| `is_orange_curved_arrow` / `is_svg_curved_arrow` / `remove_svg_arrows_from_groups` | Rule 5 |
