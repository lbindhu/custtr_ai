# Artifact Schema Reference

> **STOP — Read the field-name table below before writing any JSON artifact.**
> Do not rely on memory. These are the exact field names checked by `validate_plan.py`
> and `audit_gate.py`. Wrong names produce "missing required field" errors.

## Field-Name Quick Reference

| Artifact | Wrong (common mistake) | Correct |
|----------|----------------------|---------|
| Any action | `slide` | `slide_number` |
| Any action | `action_type` | `type` |
| Any action | `finding_id` | `finding_ids` (array) |
| `update_existing`, `fragment_replace` | `old_text`, `match` | `match_text` |
| `update_existing`, `fragment_replace` | `new_text`, `replacement` | `replacement_text` |
| `fragment_replace` | `find`, `search` | `find_fragment` |
| `fragment_replace` | `replace` | `replace_fragment` |
| `notes_update` | `notes`, `speaker_notes` | `notes_changes` (array) |
| `notes_update` items | `old`, `match` | `match_fragment` |
| `notes_update` items | `new`, `replacement` | `replacement_fragment` |
| `notes_update` | `ost_review` (missing the `d`) | `ost_reviewed` |
| `notes_update` | `ost_note`, `ost_rationale` | `ost_review_note` |
| `add_new_slide` | `slide_number` | `insert_after_slide` |
| `add_new_slide` | `body`, `content` | layout-specific field (`cards`, `table`, `columns`, `diagram`) |
| `source_inventory` queries | `id`, `query_id` | `source_id` |
| `verification_report` slides | `slide`, `number` | `slide_number` |
| `concept_decomposition` concepts | `coverage` | `current_coverage` |
| `concept_decomposition` concepts | `action` | `recommended_action` |

All field names are **case-sensitive**. Any field not in this table is almost certainly wrong —
check the schema below before inventing a new field name.

---

## Artifact Schema Reference — LLM-Authored Artifacts

These are the exact JSON schemas that `audit_gate.py` validates. Use these templates to build correct artifacts in a single pass — do not read script source code to discover field names.

### `source_inventory.json`

```json
{
  "queries": [
    {
      "source_id": "SRC-NABU-01",
      "server": "nabu",
      "query": "search query text",
      "timestamp": "2026-05-22T10:00:00Z",
      "summary": "what was found or 'no results'",
      "results_count": 5
    }
  ]
}
```

**Validation rules:**
- Top-level key can be `queries`, `entries`, or `sources`
- With `--require-sources`: minimum 3 entries with `server` containing "nabu", 1 containing "confl", 1 containing "jira" (case-insensitive)
- Each entry needs `source_id` (or `id`) — this ID is referenced by all downstream artifacts

### `reference_extract.json`

```json
{
  "entries": [
    {
      "source_id": "SRC-NABU-01",
      "section": "relevant section heading",
      "text": "verbatim source passage, minimum 30 chars per quoted claim",
      "claim_keys": ["PCIe Gen 6", "64 GT/s"]
    }
  ]
}
```

**Critical — corpus building rules:**
- `audit_gate.py` builds the verification corpus by scanning each entry for keys in this priority order: `text`, `body`, `content`, `summary`, `excerpt`, `title`
- The corpus is lowercased; every `quoted_source` in `verification_report.json` must be a **literal case-insensitive substring** of this corpus, minimum 30 characters
- If the corpus is empty -> hard error: "reference_extract.json contains no source text"
- **Use `text` as the primary key** — not `source_text`, not `quoted_text`, not `passage`

### `verification_report.json`

```json
{
  "slides": [
    {
      "slide_number": 1,
      "claims_verified": [
        {
          "claim": "human-readable claim statement",
          "source_id": "SRC-NABU-01",
          "quoted_source": "literal substring of reference_extract corpus, >=30 chars"
        }
      ],
      "findings": [
        {
          "finding_id": "F-01",
          "type": "stale_token|content_gap|notes_gap|new_slide_candidate|intra_slide_inconsistency|...",
          "recommended_action_type": "update_existing|notes_update|add_new_slide|...",
          "action_required": true,
          "description": "what is wrong and why",
          "source_id": "SRC-NABU-01",
          "quoted_source": "literal substring >=30 chars"
        }
      ],
      "knowledge_check_review": null,
      "summary_review": null,
      "open_questions": [],
      "additional_sources_needed": []
    }
  ]
}
```

**Per-slide rules:**
- Must have one row per slide in the deck — missing slides cause a hard error
- `additional_sources_needed` must be empty (non-empty is a hard error)
- Every `claims_verified` entry and every `findings` entry requires `source_id` + `quoted_source` (>=30 chars, literal corpus substring)

**KC slides** (title matches `Apply Your Knowledge|Knowledge Check|Quiz|Review Question`):
- Row MUST have a `knowledge_check_review` object OR at least one finding — otherwise hard error
- `knowledge_check_review` schema: `{"question_still_valid": bool, "answer_set_exhaustive": bool, "correct_answer_still_correct": bool, "scope_clarification_needed": bool, "note": "..."}`

**Summary slides** (title matches `Summary|Recap|Key Takeaways|Wrap-Up`):
- Row MUST have a `summary_review` object OR at least one finding — otherwise hard error

**`new_slide_candidate` findings require 7 additional fields:**
```json
{
  "finding_id": "NS-01",
  "type": "new_slide_candidate",
  "concept": "what the new slide teaches",
  "why_existing_slide_update_is_insufficient": "why a bullet/note is not enough",
  "insert_after_slide": 17,
  "learning_goal": "what the learner should understand after this slide",
  "flow_dependencies": {"connects_from": "...", "connects_to": "...", "objectives_affected": [2], "knowledge_checks_affected": [23], "summary_slides_affected": [38]},
  "recommended_layout": "ascii_diagram|bullet_with_diagram|knowledge_check|...",
  "visual_intent": "what the diagram or visual should show"
}
```

### `cross_validation_report.json`

```json
{
  "slides_examined": [1, 2, 3, 4, 5],
  "slides_with_findings": [
    {
      "slide": 1,
      "finding_id": "F-01",
      "issue": "description of the issue",
      "disposition": "UPDATE"
    }
  ],
  "slides_explicitly_cleared": [
    {
      "slide": 2,
      "reason": "non-empty reason why this slide needs no changes — must not use passive phrases (see below)",
      "source_ids": ["SRC-NABU-01"],
      "generational_analysis": {
        "content_generation": "Gen 1 Versal Premium — CPM5 PCIe controller",
        "target_generation_changes": "Gen 2 adds CPM6 with PCIe Gen 6, CXL 3.1 (SRC-NABU-03, SRC-PDF-01)",
        "why_no_impact": "Slide covers DDR5 register map (not PCIe). Register layout unchanged per SRC-NABU-03 section 4.2. Gen 2 DDR changes (expanded ECC modes) are addressed on slide 14, not here."
      }
    }
  ],
  "findings_cleared": [
    {
      "finding_id": "F-03",
      "reason": "non-empty reason why this finding is superseded",
      "source_ids": ["SRC-NABU-01"]
    }
  ]
}
```

**Validation rules:**
- `slides_examined` is REQUIRED — must equal the set of ALL slide numbers from `deck_extract.json`
- Every slide must appear in either `slides_with_findings` or `slides_explicitly_cleared`
- `reason` and `source_ids` are required on each cleared entry
- `generational_analysis` is REQUIRED on each `slides_explicitly_cleared` entry (Rule 38):
  - `content_generation` (string, min 10 chars) — what generation/version the slide's content belongs to
  - `target_generation_changes` (string, min 20 chars) — what changed between that generation and the target, with source_ids
  - `why_no_impact` (string, min 30 chars) — why those changes do not affect this slide
  - **Banned passive phrases** in `reason` and `why_no_impact` (audit_gate.py rejects these): "no stale terms", "content is still valid", "scan is clean", "no findings", "content looks correct", "no changes needed", "still accurate", "nothing to update", "all clear", "no issues found"
- `findings_cleared` is for findings that were identified but superseded (e.g., notes already contain the needed content)

### `update_plan.json`

```json
{
  "schema_version": "2.0",
  "deck": "path/to/deck.pptx",
  "target_version": "2026.1",
  "base_slide_count": 38,
  "actions": [
    {
      "action_id": "A-01",
      "type": "update_existing",
      "slide": 7,
      "finding_ids": ["F-01"],
      "source_basis": [{"source_id": "SRC-NABU-01", "rationale": "why this source supports this change"}],
      "description": "what this action does",
      "edits": [
        {
          "shape_id": "11",
          "match_text": "old text to find",
          "replacement_text": "new text to replace with"
        }
      ]
    }
  ]
}
```

**Critical field-name rules:**
- Use `type`, NOT `action_type` — the gate checks `action.get("type")`
- Use `finding_ids` (PLURAL, array), NOT `finding_id` (singular string) — also accepts: `verification_ids`, `addresses_findings`
- **`base_slide_count`** (integer, REQUIRED): The number of slides in the original deck before any additions. Read this from `deck_extract.json` (`total_slides` field) or count slides in the extraction. If omitted, `merge_storyboard.py` will auto-detect from the base deck but emit a warning — always supply it explicitly.
- `source_basis` (or `audit_basis`) is REQUIRED on ALL mutating actions — array of `{"source_id": "SRC-..."}` objects

**Mutating action types** (all require `source_basis`):
`update_existing`, `add_new_slide`, `notes_update`, `knowledge_check_update`, `remove_or_deprecate`, `fragment_replace`

**`notes_update` actions** — use `notes_changes`, NOT wholesale `speaker_notes`.
Every `notes_update` must also carry `ost_reviewed` (see Rule 37).

**Variant A — OST already consistent (`ost_reviewed: "consistent"`):**
```json
{
  "action_id": "A-03",
  "type": "notes_update",
  "slide_number": 17,
  "finding_ids": ["F-04"],
  "source_basis": [{"source_id": "SRC-NABU-01"}],
  "description": "Extend notes to clarify 64 GT/s raw signaling rate; OST already shows this.",
  "old_speaker_notes": "verbatim original notes from original_notes.json",
  "notes_changes": [
    {
      "match_fragment": "verbatim original fragment to find",
      "replacement_fragment": "new replacement text"
    }
  ],
  "ost_reviewed": "consistent",
  "ost_review_note": "Slide 17 OST already contains '64 GT/s' in the spec table (Shape 11). Notes are elaborating on a value already visible on screen — no OST change needed."
}
```

**Variant B — companion OST action present (`ost_reviewed: "companion_action_added"`):**
```json
{
  "action_id": "A-05",
  "type": "notes_update",
  "slide_number": 22,
  "finding_ids": ["F-09"],
  "source_basis": [{"source_id": "SRC-NABU-02"}],
  "description": "Update notes to reference CPM6; companion action A-04 updates the OST bullet.",
  "old_speaker_notes": "verbatim original notes from original_notes.json",
  "notes_changes": [
    {
      "match_fragment": "CPM5 supports",
      "replacement_fragment": "CPM6 supports"
    }
  ],
  "ost_reviewed": "companion_action_added"
}
```
Both `match_fragment` and `replacement_fragment` must be non-empty strings.
`ost_review_note` is required when `ost_reviewed` is `"consistent"`; omit it for `"companion_action_added"`.

> **Notes paragraph boundaries:** PPTX notes are stored as individual `<a:p>` paragraphs. Each `match_fragment` must target text within a single paragraph — it cannot span across paragraph breaks. Use `original_notes.json` to see the exact paragraph structure. If a slide's notes are completely empty, `notes_changes` cannot match anything — use post-processing instead.

> **Extraction artifact:** `extract_speaker_notes.py` appends the slide number as a trailing string in `original_notes.json` (e.g., slide 36's notes end with `"36"`). This is a tracking artifact, NOT actual notes content. Do not include it in `match_fragment` or `old_speaker_notes` values.

**`fragment_replace` actions** — substring edit within a shape:

Use when you need to change text that is one paragraph (or part of a paragraph) inside a **multi-paragraph shape**. Do NOT use `update_existing` with `match_text` for this — `match_text` requires the **entire shape text** (all paragraphs concatenated with `\n`).

```json
{
  "action_id": "A-02",
  "type": "fragment_replace",
  "slide": 6,
  "find_fragment": "exact substring to find within any <a:t> run",
  "replace_fragment": "replacement text",
  "source_basis": [{"source_id": "SRC-NABU-01"}],
  "description": "what this fragment change does"
}
```

> **Important:** `notes_changes` is NOT processed for `fragment_replace` actions. If you need both a shape fragment edit AND a notes edit on the same slide, use two separate actions: one `fragment_replace` for the shape, one `notes_update` for the notes.

### Field-Name Quick Reference

| Action type | Shape fields | Notes fields |
|---|---|---|
| `update_existing` | `match_text` + `replacement_text` | `notes_changes: [{match_fragment, replacement_fragment}]` |
| `update_existing` (multi-edit) | `replacements: [{match_text, replacement_text}]` | same |
| `fragment_replace` | `find_fragment` + `replace_fragment` | *(not processed — use separate `notes_update`)* |
| `notes_update` | *(none)* | `notes_changes: [{match_fragment, replacement_fragment}]` |
| `knowledge_check_update` | `match_text` + `replacement_text` | `notes_changes: [{match_fragment, replacement_fragment}]` |

**Common field-name mistakes (all silently skipped without this warning):**
- `shape_match` -> use `match_text`
- `replacement` -> use `replacement_text`
- `old_text` -> use `match_text`
- `new_text` -> use `replacement_text`
- `find_text` -> use `find_fragment`
- `replace_text` -> use `replace_fragment`
- `match` (in notes_changes) -> use `match_fragment`
- `replace` (in notes_changes) -> use `replacement_fragment`
- `additional_replacements` -> use `replacements`

**`add_new_slide` actions** — 8 required fields beyond standard:
```json
{
  "action_id": "A-07",
  "type": "add_new_slide",
  "finding_ids": ["NS-01"],
  "source_basis": [{"source_id": "SRC-NABU-01"}],
  "insert_after_slide": 17,
  "slide_layout": "cards|ascii_diagram|comparison_table|block_diagram|two_column|key_takeaway",
  "title": "Slide Title",
  "description": "what this slide covers",
  "learning_goal": "what the learner should understand after this slide",
  "why_this_slide_exists": "structural justification (e.g., parity gap)",
  "what_customer_should_understand": "key takeaways for the customer",
  "speaker_notes": "full narration text for the instructor",
  "content": {
    "bullets": ["bullet 1", "bullet 2"]
  },
  "key_points": {
    "heading": "Key Specs",
    "bullets": ["DDR5MC: DDR5, LPDDR5, LPDDR5X", "DDRMC: DDR4, LPDDR4"]
  }
}
```

Optional field `key_points` (for `block_diagram` and `ascii_diagram` layouts): `{heading?: string, bullets: string[]}`. Renders a right-side dark panel with 3-6 visible bullet points as on-screen text (OST). Recommended for narrated storyboards. Every bullet's key term must appear in `speaker_notes` (OST-notes sync, Rule 34).

Missing any of `insert_after_slide`, `slide_layout`, `title`, `learning_goal`, `why_this_slide_exists`, `what_customer_should_understand`, `speaker_notes`, `source_basis` causes a hard error.

### User-provided material

If the user provided documents, PDFs, or links, every one must be read and its findings recorded in the source inventory. Do not skip user-provided material.

User-provided sources define *additional* content to check — they do not narrow the overall audit scope. If the user provides a document about feature X, search MCP for feature X but also independently search for all other topics covered in the deck. Do not let a user-provided source become the only lens for MCP queries.

---

## concept_decomposition.json

**Required before `audit_gate.py` will advance.** Author this during Phase 3 after reading `references/workflow_phases.md`. Maps every source delta to its independently teachable concepts and checks whether the current deck provides adequate coverage for each.

```json
{
  "schema_version": "1.0",
  "deck": "<deck filename>",
  "source_deltas": [
    {
      "delta_id": "D1",
      "description": "<what changed in the source — one sentence>",
      "source_ids": ["src-001"],
      "teachable_concepts": [
        {
          "concept": "<independently teachable concept name>",
          "current_coverage": "none",
          "adequate": false,
          "recommended_action": "add_new_slide",
          "target_slides": []
        }
      ]
    }
  ]
}
```

**Field rules:**
- `delta_id`: unique string per source delta (e.g., "D1", "D2")
- `current_coverage`: `"none"` if zero slides address the concept; `"partial"` if mentioned but not taught; `"adequate"` if fully covered
- `adequate`: `false` means a finding must exist in `verification_report.json` or `cross_validation_report.json` for this concept, OR an `add_new_slide` action in `update_plan.json`
- `recommended_action`: `"add_new_slide"` | `"update_existing"` | `"no_change"`
- `target_slides`: existing slide numbers this concept maps to; empty array `[]` means no existing slide covers it — an `add_new_slide` action is required
