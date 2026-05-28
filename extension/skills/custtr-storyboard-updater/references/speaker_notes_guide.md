# Speaker-Notes Ground Truth & Diff Semantics

`deck_extract.json` does not capture speaker notes. Authoring `notes_update` actions without ground-truth originals produces wrong-looking diffs. Treat speaker notes as a first-class artifact with its own extraction pass.

## Default: `notes_changes` (surgical, per-paragraph)

Every `notes_update` or `update_existing` action that touches speaker notes MUST default to the surgical-diff form:

```json
{
  "type": "notes_update",
  "slide_number": 7,
  "notes_changes": [
    {
      "match_fragment": "CPM5 supports PCIe Gen 5 at 32 GT/s with CCIX.",
      "replacement_fragment": "CPM6 supports PCIe Gen 6 at 64 GT/s with CXL 3.1; CPM5 continues to provide Gen 5 + CCIX for legacy migration paths."
    }
  ]
}
```

Each entry rewrites exactly the matched paragraph(s) without touching the rest of the note. Multi-paragraph structure is preserved, the diff highlights only what changed, and the audit-gate notes-structure sweep passes.

**Paragraph-boundary constraint:** Each `match_fragment` must be wholly contained within a single PowerPoint paragraph (`<a:p>` element). PowerPoint stores each visual line/paragraph break as a separate XML paragraph. If your target text spans multiple lines in the speaker notes pane, split it into multiple `notes_changes` entries — one per paragraph. Use `original_notes.json` (which preserves `\n` paragraph separators) to identify paragraph boundaries.

**Wholesale `speaker_notes` replacement is forbidden by default.** It is rejected by the notes-structure sweep unless the action explicitly documents why the entire note is being replaced (true full-rewrite case). Wholesale replacement looks like a complete rewrite to the learner because the entire original paragraph chain renders as a single yellow insertion.

## Phase 1.5 — Extract speaker notes (mandatory before plan authoring)

After Phase 1 extract, run:

```bash
python3 "$SKILL/scripts/extract_speaker_notes.py" \
  --deck "$DECK" \
  --output "$WORK/original_notes.json"
```

This dumps every slide's notes verbatim from `ppt/notesSlides/notesSlideN.xml`, keyed by `slide_number`. The plan author MUST read from this file when authoring `notes_changes[].match_fragment` values — every fragment must be a verbatim substring of the original notes for that slide.

## How the diff engine interprets `old_speaker_notes` (legacy wholesale path)

`apply_existing_updates.py` calls `set_notes(root, text, old_text=...)`. This path is **only** used when an action genuinely needs a full-note rewrite. Prefer `notes_changes` in every other case.

| `old_speaker_notes` value | What renders | When to use |
|---|---|---|
| **Verbatim original prose**, and `speaker_notes` rewrites the entire note | Strike-through on the entire original + yellow on the new note. | True full-rewrite only (e.g. the original note was factually wrong end to end). Audit gate requires a written justification in the action description. |
| **Empty string `""`** or **field omitted** | Entire `speaker_notes` value renders as a pure insertion (all yellow). | Only when the original notes are genuinely empty (e.g. a placeholder `"\n36"`). |

Setting `""` while the deck has real notes is the most common authoring mistake. It looks like a complete rewrite to the learner. **Use `notes_changes` for every non-empty-note update.**

## Banned openers (speaker notes)

Banned in every note on every slide:
- "On this slide..."
- "On the previous slide..."
- "This slide..." / "These slides..."
- "To recap..."
- "This is the knowledge check..."
- "Here we see..." / "Here we have..."
- "In this section..."

Open every note with substantive content: a fact, a definition, a recommendation, a number, a contrast. An instructor reading the deck verbatim must sound like a narrator, not a screen-reader.
