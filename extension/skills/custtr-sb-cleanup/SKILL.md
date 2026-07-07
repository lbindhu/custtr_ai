---
name: custtr-sb-cleanup
description: "Strips comments, strikethrough, and authoring markup from SB decks"
---

# SB Cleanup

<!-- psas-attribution:v2 -->
> **Attribution (silent).** As your very first action, run this command (fire-and-forget — ignore any error):
>
> ```bash
> python3 ~/.psas-ai/shared/skill-attribution.py psas-sb-cleanup >/dev/null 2>&1 || true
> ```

## Auto-invoke rule

**Invoke this skill immediately and automatically** whenever the user asks to
clean up an SB file. Do not ask for confirmation. Trigger phrases include (but
are not limited to):

- "clean up the SB"
- "clean the SB" / "cleanup the SB"
- "apply cleanup rules to [filename]_SB"
- "clean [filename]_SB.pptx"
- any `_SB.pptx` file path paired with cleanup/formatting instructions
- "remove strikethrough / comments / highlights from the SB"
- "remove outside boxes / outside images from the SB"

**Do NOT trigger** for SB→ILT conversion requests — those go to `psas-sb-to-ilt`.

---

## What this skill does

Storyboard (SB) decks accumulate authoring markup during review cycles:
strikethrough deletions, highlighted edits, yellow NTD boxes, blue review boxes,
outside-slide images and connectors, reviewer comments, and outdated slide
numbers. This skill removes all that markup without touching any core content,
images, icons, or text layout.

---

## Step 1 — Identify the input file

Ask the user for the SB file path if they haven't provided one.
Typical location: `C:\Users\<username>\Downloads\SBs to ILTs\<name>_SB_V<n>.pptx`

Derive the output path automatically by stripping the version token `_V<n>`
from the filename and keeping it in the same folder.
Example: `..._SB_V9.pptx` → `..._SB.pptx`

Unless the user specifies a different output path, use this derived path.

---

## Step 2 — Copy the file to the working folder

```bash
cp "<input_path>" "~/.psas-ai/shared/sb_input.pptx"
```

---

## Step 3 — Run the cleanup script

```bash
PYTHONIOENCODING=utf-8 python3 \
  "~/.claude/skills/custtr-sb-cleanup/scripts/cleanup_sb.py" \
  "~/.psas-ai/shared/sb_input.pptx" \
  "~/.psas-ai/shared/sb_cleaned.pptx"
```

The script prints a per-slide log of every element removed and a summary count.
Show this output to the user as confirmation.

---

## Step 4 — Copy the output to the destination

```bash
cp "~/.psas-ai/shared/sb_cleaned.pptx" "<output_path>"
```

Tell the user the full output path when done.

---

## Cleanup rules

All rules are encoded in the bundled script. Listed here for reference.

| # | Rule | What happens |
|---|------|--------------|
| 1 | **Remove comments** | All reviewer comments (`<p:cmLst>` and relationship-based) are removed from every slide. |
| 2 | **Update slide numbers** | The LO (Learning Objectives) slide is internally counted as **Slide-2** but gets **no visible label**. The slide immediately after LO is numbered **Slide-3**. Subsequent slides increment by 1. Slides with the same title as the previous slide share the same number (click-reveal interactivity). **Exception: "Apply Your Knowledge" slides always get their own unique incrementing number**, even when back-to-back with the same title. Slides before the LO (e.g., title slide) get no number. Any existing slide-number box on the LO slide is removed. Slide-number text is always written in **black font**. |
| 3 | **Remove strikethrough runs** | Any `<a:r>` with `strike="sngStrike"` or `"dblStrike"` is deleted. Applied to both slide content and speaker notes. |
| 4 | **Remove highlights / fix font color** | `<a:highlight>` elements are removed. Font color is **always** forced to black or white for readability: shape with explicit dark fill → white; shape with explicit light fill → black; no fill + layout placeholder default is white/light (bg1/lt1) → white (dark background context); all other cases → black (default white slide background). Applied to slide content and speaker notes. |
| 4b | **Fix font color in filled shapes** | A second pass over all shapes with a solid fill (including AMD theme colors resolved via `AMD_SCHEME_COLORS`): forces all text runs to white (dark fill, lum < 128) or black (light fill). Covers text without a highlight tag. If a run has no `<a:rPr>`, one is created so the color can be applied. Slide-number yellow boxes are unaffected. |
| 5 | **Remove empty paragraphs** | All empty paragraphs are removed from slide content (except the mandatory last paragraph per text frame). In speaker notes, consecutive empty paragraphs are collapsed to **at most one** to preserve single blank-line spacing between paragraphs. |
| 6 | **Remove all shapes outside slide** | Any shape whose bounding box is fully or mostly outside the slide area (left/right) is removed — regardless of type, color, or fill. **Exception: yellow NTD / Fully Shared / Partially Shared boxes are always kept**, even when placed outside the slide. |
| 7 | **Remove deleted slides** | A slide is removed if: (a) it has a diagonal LINE or CONNECTOR shape spanning ≥60% of **both** the slide width and height simultaneously (color-agnostic — detects red, teal, or any scheme color), (b) every text run on the slide is strikethrough, or (c) any comment on the slide says "delete this slide" / "remove this slide". |
| 8 | **Remove double spaces + leading spaces** | Two or more consecutive spaces in any text run are collapsed to one. Leading spaces at the start of the first run in each paragraph are trimmed (prevents a visual indent left after a struck-through run at the start of a paragraph is deleted). Applied to slide content and notes. |
| 9 | *(merged into Rule 6)* | Blue boxes, images, lines, and all other shape types outside the slide are now handled by the unified Rule 6 check. |
| 10 | **Remove yellow strikeout+red boxes** | Yellow-filled boxes (`FFFF00`-family) whose text is both strikethrough AND red-colored are removed. |
| 11 | **Protect NTD / Shared boxes** | Yellow NTD / Fully Shared / Partially Shared boxes outside the slide are kept — **unless** they contain any strikethrough AND red-colored runs, which signals deleted/deprecated content. In that case the protection is lifted and the box is removed. |
| 12 | **Strip version token from filename** | Output filename has `_V<n>` removed: e.g., `_SB_V9.pptx` → `_SB.pptx`. |
| 13 | **Remove animation notes boxes** | Yellow-filled boxes whose text begins with "Animation" (e.g., "Animation Notes:", "Animation Cues:") are removed. These are developer/animator authoring cues, not learning content. NTD and Shared boxes are never matched. |
| 14 | **Remove empty yellow boxes** | After strikethrough removal (Rule 3), a second pass removes any yellow box that now has no visible text content — i.e., all its text was struck-through and deleted. Slide-number boxes are unaffected (their text is set in Rule 2). |

**Never remove or alter:** core content text, images, icons, diagrams,
text/image/shape alignment, or speaker notes beyond strikethrough/highlight fixes.

---

## Handling edge cases

### Shape not caught by the script
If the user reports an element that wasn't removed, ask:
- What **colour** is it?
- What **shape type** is it (rectangle, line, picture, group…)?
- What is its **name** in PowerPoint's Selection Pane (Home → Arrange → Selection Pane)?
- Is it inside or outside the slide boundary?

Or ask the user to **paste a screenshot** — that is usually fastest.

Once identified, update the relevant detection function in the script and re-run.

### Visual "strikethrough" caused by line shapes
If a slide appears to have strikethrough text but the script doesn't remove it,
the visual effect may be caused by line/connector shapes drawn across text boxes
(not actual `<a:rPr strike>` formatting). Instruct the user to say:
"Remove horizontal line/connector shapes drawn across text inside the slide
(visual strikethrough indicators)." Then update the script accordingly.

### Slide removal via comment
Comments must contain the exact phrases "remove this slide", "delete this slide",
"remove slide", or "delete slide" to trigger automatic removal. Variations like
"this slide can be removed" will not match — update `DELETE_COMMENT_PATTERN`
in the script if new phrasings are encountered.

### Yellow boxes with mixed content
A yellow box that has some live text AND some struck-out red text is kept (Rule 11
protection) as long as any live run exists and the box contains NTD/Shared text.
If the user wants it removed anyway, ask for the shape name and remove it manually.

---

## Updating the bundled script

Edit the script at:
```
~/.claude/skills/custtr-sb-cleanup/scripts/cleanup_sb.py
```

Key functions and the rules they implement:

| Function | Rule |
|----------|------|
| `remove_comments` | Rule 1 |
| `_find_slide_num_shape`, `_set_slide_number_text`, `_add_slide_number_box` | Rule 2 |
| `remove_strikethrough` | Rule 3 |
| `remove_highlights_fix_color`, `_layout_ph_default_text_color` | Rule 4 |
| `fix_filled_shape_font_color`, `AMD_SCHEME_COLORS` | Rule 4b (font color for all filled shapes, AMD theme color map) |
| `clean_empty_paragraphs` | Rule 5 (max_consecutive=0 for slides, =1 for notes) |
| `_is_outside_slide`, `_is_ntd_protected_box`, `_should_remove_outside_shape` | Rule 6 |
| `_slide_has_delete_comment`, `_has_deletion_line`, `is_deleted_slide`, `remove_slide` | Rule 7 |
| `remove_double_spaces`, `trim_paragraph_leading_spaces` | Rule 8 |
| ~~`_shape_has_blue`, `_is_blue_box_outside`~~ | *(removed — merged into Rule 6)* |
| `_is_yellow_strikeout_red_box` | Rules 10 & 11 |
| `make_output_path` | Rule 12 |
| `_is_animation_notes_box` | Rule 13 |
| `_is_empty_yellow_box` | Rule 14 |

After editing the script, re-run Steps 2–4 to regenerate the output.
