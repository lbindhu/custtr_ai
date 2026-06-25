# Speaker-Notes Ground Truth & Readability Semantics

`deck_extract.json` does not capture speaker notes. Authoring `notes_update` actions without ground-truth originals produces wrong-looking diffs and unreliable matching. Treat speaker notes as a first-class instructional artifact with its own extraction pass.

Speaker notes should be clean narrator-script content: current, source-backed, concise, and easy for an instructor to read verbatim. Do not use the notes pane as a visible diff log. Record audit rationale in JSON artifacts; keep the notes themselves focused on teaching.

> **Current tooling limitation:** Existing scripts may still render `notes_changes` with diff-style marking in the PPTX. This guide defines the authoring standard only. Do not claim clean note rendering is enforced at runtime unless `apply_existing_updates.py` or related scripts have been changed.

## Default: `notes_changes` (surgical, per-paragraph)

Every `notes_update` or `update_existing` action that touches speaker notes MUST default to the surgical per-paragraph form:

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

Each entry targets exactly the matched paragraph fragment without touching the rest of the note. Multi-paragraph structure is preserved, the replacement text stays focused, and the audit-gate notes-structure sweep can verify the change. Author the `replacement_fragment` as final narration, not as a reviewer comment such as "update this to..." or "replace CPM5 with CPM6."

**Paragraph-boundary constraint:** Each `match_fragment` must be wholly contained within a single PowerPoint paragraph (`<a:p>` element). PowerPoint stores each visual line/paragraph break as a separate XML paragraph. If your target text spans multiple lines in the speaker notes pane, split it into multiple `notes_changes` entries — one per paragraph. Use `original_notes.json` (which preserves `\n` paragraph separators) to identify paragraph boundaries.

**Wholesale `speaker_notes` replacement is forbidden by default.** It is rejected by the notes-structure sweep unless the action explicitly documents why the entire note is being replaced (true full-rewrite case). Wholesale replacement looks like a complete rewrite to the learner because the entire original paragraph chain can render as a single yellow insertion.

## Readability authoring rules

- Keep notes learner- and instructor-facing. Do not include audit metadata, source IDs, TODO language, or change explanations in the narration itself.
- Prefer short, high-similarity replacements when only a fact changes. If a paragraph needs a substantial rewrite, split the update into smaller coherent fragments or pair it with an OST-level action that makes the changed concept visible.
- Do not introduce a new technical concept only in notes. Rule 34 still applies: the slide's OST, or a companion OST action, must surface the concept.
- If prior runs produced unreadable note diffs, document that preference in the plan and keep `replacement_fragment` prose clean. Treat any runtime marking as review scaffolding, not as final narration quality.

## Phase 1.5 — Extract speaker notes (mandatory before plan authoring)

After Phase 1 extract, run:

```bash
python3 "$SKILL/scripts/extract_speaker_notes.py" \
  --deck "$DECK" \
  --output "$WORK/original_notes.json"
```

This dumps every slide's notes verbatim from `ppt/notesSlides/notesSlideN.xml`, keyed by `slide_number`. The plan author MUST read from this file when authoring `notes_changes[].match_fragment` values — every fragment must be a verbatim substring of the original notes for that slide.

## How the diff engine interprets `old_speaker_notes` (legacy wholesale path)

`apply_existing_updates.py` historically called `set_notes(root, text, old_text=...)` for full-note rewrites. This path is **only** appropriate when an action genuinely needs a full-note rewrite. Prefer `notes_changes` in every other case.

| `old_speaker_notes` value | What renders | When to use |
|---|---|---|
| **Verbatim original prose**, and `speaker_notes` rewrites the entire note | Strike-through on the entire original + yellow on the new note. | True full-rewrite only (e.g. the original note was factually wrong end to end). Audit gate requires a written justification in the action description. |
| **Empty string `""`** or **field omitted** | Entire `speaker_notes` value renders as a pure insertion (all yellow). | Only when the original notes are genuinely empty (e.g. a placeholder `"\n36"`). |

Setting `""` while the deck has real notes is the most common authoring mistake. It looks like a complete rewrite to the learner. **Use `notes_changes` for every non-empty-note update**, and author the replacement as polished narrator-script prose.

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
