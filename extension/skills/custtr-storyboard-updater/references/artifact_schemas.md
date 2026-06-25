# Artifact Schema Reference

> **STOP — Read the field-name table below before writing any JSON artifact.**
> Do not rely on memory. These are the exact field names checked by `validate_plan.py`
> and `audit_gate.py`. Wrong names produce "missing required field" errors.

## Field-Name Quick Reference

| Artifact | Wrong (common mistake) | Correct |
|----------|----------------------|---------|
| Existing-slide actions | `slide` | `slide_number` |
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
| `add_new_slide` | hard-coded renderer routing | LLM-authored `visual_approach` + `visible_content_summary` + `qa_expectations` |
| `source_inventory` queries | `id`, `query_id` | `source_id` |
| `verification_report` slides | `slide`, `number` | `slide_number` |
| `concept_decomposition` concepts | `coverage` | `current_coverage` |
| `concept_decomposition` concepts | `action` | `recommended_action` |

All field names are **case-sensitive**. Any field not in this table is almost certainly wrong —
check the schema below before inventing a new field name.

---

## Artifact Schema Reference — LLM-Authored Artifacts

These are the exact JSON schemas that `audit_gate.py` validates. Use these templates to build correct artifacts in a single pass — do not read script source code to discover field names.

### `story_model.json`

`story_model.json` is LLM-authored from `deck_extract.json`. Python creates the extraction and a scaffold; the LLM performs the instructional interpretation. This artifact is not source-backed audit evidence and must not contain clears, findings, or claims such as "SRC-NABU-01 confirms..." or "no changes needed."

```json
{
  "schema_version": "2.0",
  "deck_identity": {
    "deck": "path/to/deck.pptx",
    "title": "Module title",
    "target_version": "2026.1",
    "audience": "AMD customer training learners",
    "module_scope": "What this module covers"
  },
  "primary_message": "What the deck is trying to teach.",
  "key_talking_points": ["concept 1", "concept 2"],
  "slide_interpretations": [
    {
      "slide_number": 1,
      "title": "Slide title",
      "role": "objectives",
      "role_rationale": "Why this role fits.",
      "teaching_purpose": "What this slide does for the learner.",
      "core_claims": ["Claim visible or narrated on this slide."],
      "concepts_introduced": ["concept"],
      "concepts_reinforced": [],
      "generation_specificity": "unknown",
      "visual_dependency": "medium",
      "notes_dependency": "low",
      "evidence": [
        {
          "type": "shape",
          "slide_number": 1,
          "shape_id": "12",
          "quote": "Literal text from the shape."
        }
      ]
    }
  ],
  "learning_objectives": [
    {
      "objective": "Objective text",
      "source_slide": 2,
      "covered_by_slides": [5, 6],
      "assessed_by_slides": [9]
    }
  ],
  "concept_flow": [
    {
      "concept": "concept name",
      "introduced_on": 3,
      "reinforced_on": [4, 5],
      "depends_on": []
    }
  ],
  "knowledge_check_alignment": [
    {
      "slide_number": 9,
      "assesses_concepts": ["concept name"],
      "depends_on_generation_specific_facts": true,
      "alignment_note": "What the question appears to test."
    }
  ],
  "summary_alignment": [
    {
      "slide_number": 20,
      "summarizes_concepts": ["concept name"],
      "alignment_note": "How the summary maps to the deck flow."
    }
  ],
  "source_research_hypotheses": [
    {
      "query": "Primary technology plus target generation",
      "why": "What deck claim or gap this query should validate.",
      "target_sources": ["NABU", "Vivado docs"]
    }
  ],
  "stale_terms_candidates": [
    {
      "token": "candidate term",
      "reason": "Why this needs source confirmation.",
      "slides": [3, 4]
    }
  ],
  "slide_roles": [
    {"slide_number": 1, "title": "Slide title", "role": "objectives"}
  ],
  "knowledge_checks": [9],
  "summary_slides": [20],
  "concept_coverage": [
    {"concept": "concept name", "covered_on": [3, 4], "assessed_on": [9]}
  ]
}
```

**Validation rules:**
- `schema_version` must be `"2.0"`.
- `slide_interpretations` must contain exactly one row for every slide in `deck_extract.json`.
- Each row must have a non-empty `teaching_purpose`, valid `role`, valid `generation_specificity`, and valid visual/notes dependency values.
- Every `evidence` reference must point to a real shape ID or notes quote from `deck_extract.json`.
- Source-backed audit language is rejected. Use `source_research_hypotheses` for queries that Phase 2 should run.
- Compatibility fields `primary_message`, `key_talking_points`, `slide_roles`, `knowledge_checks`, `summary_slides`, and `concept_coverage` remain required because downstream scripts consume them.

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
- With `--require-sources`: entries must document source coverage with `source_id` (or `id`); fixed channel counts are not enforced
- Each entry needs `source_id` (or `id`) — this ID is referenced by all downstream artifacts
- If a channel is intentionally not used, record the rationale in the source inventory or checkpoint summary instead of running ritual searches

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
          "claim_disposition": "supported",
          "source_entailment": "Source directly supports this claim.",
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
          "lint_signal_disposition": "confirmed_finding",
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
- Every `claims_verified` entry requires `claim_disposition` (`supported|contradicted|insufficient|out_of_scope`) and `source_entailment` (min 20 chars)
- Lint-derived `findings` (`stale_token`, `content_gap`, etc.) require `lint_signal_disposition` (`confirmed_finding|rejected_lint|intentionally_kept|out_of_scope`)

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
  "visual_intent": "what the slide visual should show",
  "qa_expectations": ["rendered slide has no cutoffs or overlaps", "visual style matches neighboring slides"]
}
```

### `cross_validation_report.json`

```json
{
  "slides_examined": [1, 2, 3, 4, 5],
  "stale_hit_reconciliation": {
    "total_hits": 12,
    "reconciled_hits": 12,
    "unresolved_hits": []
  },
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
- If `stale_term_scan.json` exists, every surviving hit must be reconciled. Use optional `stale_hit_reconciliation` to record total/reconciled counts, but `audit_gate.py` enforces the source of truth directly from `stale_term_scan.json`.
- A slide with a surviving stale-term hit may be explicitly cleared only when the clear reason names the token or location and explains why that hit is retained; generic generation analysis is not enough.
- `generational_analysis` is REQUIRED on each `slides_explicitly_cleared` entry (Rule 39):
  - `content_generation` (string, min 10 chars) — what generation/version the slide's content belongs to
  - `target_generation_changes` (string, min 20 chars) — what changed between that generation and the target, citing `SRC-...` source_ids
  - `why_no_impact` (string, min 30 chars) — why those changes do not affect this slide
  - `generational_analysis.source_ids` (optional array) — may duplicate IDs cited in `target_generation_changes`
  - **Gate checks:** non-empty `source_ids` on clear row; cited IDs must exist in inventory/reference extract; at least one >=20 char substring of `target_generation_changes` or `why_no_impact` must appear verbatim (case-insensitive) in `reference_extract.json`
  - **Banned passive phrases** in `reason` and `why_no_impact` (audit_gate.py rejects these): "no stale terms", "content is still valid", "scan is clean", "no findings", "content looks correct", "no changes needed", "still accurate", "nothing to update", "all clear", "no issues found"
- `findings_cleared` is for findings that were identified but superseded (e.g., notes already contain the needed content)

### `consistency_scan.json` (script-generated — Rule 35)

Written by `consistency_scan.py` (auto-run by `storyboard_update.py --mode audit-plan`). A flat JSON array of intra-slide consistency violations:

```json
[
  {
    "slide_number": 12,
    "title": "Versal Gen 2 Processing System",
    "type": "intra_slide_variant",
    "advisory": false,
    "tokens": ["A78AE", "A78E"],
    "locations": {
      "A78AE": ["shape 20 (Callout 3)", "notes"],
      "A78E": ["shape 14 (Diagram label)"]
    },
    "issue": "Slide uses near-identical technical tokens 'A78AE' and 'A78E' that differ only by an internal letter edit — likely a typo or a label/bullet mismatch (Rule 35)."
  },
  {
    "slide_number": 5,
    "title": "Programmable Logic",
    "type": "advisory_typo",
    "advisory": true,
    "tokens": ["programable"],
    "suggested": "programmable",
    "locations": {"programable": ["shape 7 (Body)"]},
    "issue": "Possible misspelling 'programable' (did you mean 'programmable'?) — advisory only (Rule 35)."
  }
]
```

**Reconciliation rules (enforced by `audit_gate.py`):**
- Each entry with `advisory: false` must be reconciled or the pre-plan/pre-execute gate fails: a verification finding on that slide naming one of `tokens`, a plan action on that slide naming one of `tokens`, or a `slides_explicitly_cleared` entry whose reason names one of `tokens`.
- Entries with `advisory: true` (common misspellings) surface as gate **warnings**, not hard failures.
- The scanner only flags **internal letter edits** within edit-distance 2; digit-only generation siblings (`CPM5`/`CPM6`, `DDR4`/`DDR5`) and prefix/suffix family variants (`LPDDR5`/`DDR5`) are intentionally not flagged.

### `proofread_review.json` (LLM-authored — Rule 35)

The explicit, deck-wide **LLM proofreading pass**. The deterministic `consistency_scan.py` only catches near-miss letter typos; this artifact is where the model records the spelling, grammar, intra-slide, and **cross-slide** consistency issues a regex can never find — and explicitly dispositions every script signal. `audit_gate.py` requires it at both the pre-plan and pre-execute stages.

```json
{
  "schema_version": "1.0",
  "deck": "<deck filename>",
  "slides_reviewed": [1, 2, 3, "...every slide number..."],
  "scan_signals_dispositioned": [
    {
      "slide_number": 12,
      "tokens": ["A78AE", "A78E"],
      "disposition": "confirmed_finding",
      "note": "Diagram label 'A78E' is a typo for 'A78AE' (matches callout + notes + PG SRC-PG-02).",
      "finding_id": "S12-F01"
    },
    {
      "slide_number": 30,
      "tokens": ["X1A", "X1B"],
      "disposition": "rejected_lint",
      "note": "X1A and X1B are two distinct valid product SKUs per SRC-WEB-04; not a typo."
    }
  ],
  "issues": [
    {
      "slide_number": 8,
      "type": "cross_slide_inconsistency",
      "severity": "fix",
      "shapes": ["shape 14 (Diagram)"],
      "description": "Diagram shows 3 cores but slide 6 bullet and notes say 'quad-core'.",
      "recommended_action": "update_existing"
    },
    {
      "slide_number": 22,
      "type": "grammar",
      "severity": "advisory",
      "shapes": ["notes"],
      "description": "Run-on sentence in second narration paragraph."
    }
  ]
}
```

**Field rules:**
- `slides_reviewed` MUST cover every slide number in `deck_extract.json` (proves the pass was deck-wide, not sampled).
- `scan_signals_dispositioned` MUST contain an entry for every **non-advisory** signal in `consistency_scan.json`, matched by `slide_number` + overlapping `tokens`.
  - `disposition` is one of `confirmed_finding | rejected_lint | intentionally_kept | out_of_scope` and requires a non-empty `note`.
  - `confirmed_finding` → the signal must ALSO be represented by a finding, plan action, or token-naming clear (the existing reconciliation rule still applies).
  - `rejected_lint | intentionally_kept | out_of_scope` → the documented `note` dismisses the script signal. This is the sanctioned escape hatch for legitimate scanner false positives — do not fabricate a clear just to silence the scan.
- `issues[]` are LLM-discovered problems the script could not detect. `type` is free-form (`spelling | grammar | intra_slide_inconsistency | cross_slide_inconsistency | terminology | ...`). `severity` is `fix` or `advisory`.
  - Every `severity: "fix"` issue must be represented by a finding, plan action, or clear on that slide — a **warning** at pre-plan, a hard **error** at pre-execute.
  - `advisory` issues surface as warnings only.

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
      "slide_number": 7,
      "finding_ids": ["F-01"],
      "source_basis": [{"source_id": "SRC-NABU-01", "rationale": "why this source supports this change"}],
      "reason": "why this change is required",
      "description": "what this action does",
      "match_text": "old full shape text to find",
      "replacement_text": "new full shape text"
    }
  ]
}
```

**Critical field-name rules:**
- Use `type`, NOT `action_type` — the gate checks `action.get("type")`
- Use `slide_number`, NOT `slide`, on existing-slide actions.
- Use top-level `match_text`/`replacement_text` or `replacements[]` for `update_existing`; there is no `edits[]` field.
- Use `finding_ids` (PLURAL, array), NOT `finding_id` (singular string) — also accepts: `verification_ids`, `addresses_findings`
- **`base_slide_count`** (integer, REQUIRED): The number of slides in the original deck before any additions. Read this from `deck_extract.json` (`total_slides` field) or count slides in the extraction. If omitted, `merge_storyboard.py` will auto-detect from the base deck but emit a warning — always supply it explicitly.
- `source_basis` (or `audit_basis`) is REQUIRED on ALL mutating actions — array of `{"source_id": "SRC-..."}` objects

**Mutating action types** (all require `source_basis`):
`update_existing`, `add_new_slide`, `notes_update`, `knowledge_check_update`, `remove_or_deprecate`, `fragment_replace`

**Readable action-selection guidance:**

Choose the action type based on the rendered learner experience, not just on whether a string can be matched.

- `fragment_replace`: preferred for small visible edits such as version tokens, IP names, protocol names, rates, capacities, or short diagram labels. The marked result should remain readable in context.
- `update_existing`: use for full-shape replacement only when the old struck text plus highlighted new text will still be easy to scan. Avoid using it for long paragraph rewrites, dense tables, or slide-level restructuring.
- `add_new_slide`: prefer when a source delta introduces a concept that needs a clean explanation, a diagram, a comparison, or parallel depth with nearby sections. New slides should be polished training content, not diff artifacts.
- `notes_update`: use for narrator-script updates that support visible content. Notes should be clean, readable, and instructor-ready. Current execution tooling may still render note changes with diff-style marking; do not imply clean note rendering is enforced unless scripts have been updated.
- `remove_or_deprecate`: use for final deck composition during merge. It removes/deprecates slides from the final merged output; it is not an in-place text edit handled by `apply_existing_updates.py`.

For high-clutter slides (tables, diagrams, dense bullets, knowledge checks), include a readability rationale in `reason` or `description`: why this action is enough, or why a redesigned/new slide is required. If repeated labels or table values make text matching ambiguous, call that out and use a more precise `fragment_replace` or a manual review note.

> **Current validator caveat:** Although the apply script supports `replacements[]` for `update_existing`, `validate_plan.py` currently requires top-level `match_text` and `replacement_text`. Until the validator is updated, include a top-level edit on each `update_existing` action or split multi-edit work into separate actions.

**`notes_update` actions** — use `notes_changes`, NOT wholesale `speaker_notes`.
Every `notes_update` must also carry `ost_reviewed` (see Rule 38).

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
  "slide_number": 6,
  "find_fragment": "exact substring to find within any paragraph (text is concatenated across runs)",
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

**`add_new_slide` actions** ? required fields beyond standard:
```json
{
  "action_id": "A-07",
  "type": "add_new_slide",
  "finding_ids": ["NS-01"],
  "source_basis": [{"source_id": "SRC-NABU-01"}],
  "insert_after_slide": 17,
  "title": "Slide Title",
  "description": "what this slide covers",
  "learning_goal": "what the learner should understand after this slide",
  "why_this_slide_exists": "structural justification (for example, parity gap)",
  "what_customer_should_understand": "key takeaways for the customer",
  "visible_content_summary": "what must be visible on the slide itself",
  "visual_approach": "how the LLM will match the surrounding deck and construct the slide",
  "qa_expectations": ["no text cutoffs", "no overlaps", "visual style matches neighboring slides"],
  "speaker_notes": "full narration text for the instructor"
}
```

Do not require fixed renderer fields. Implementation details may appear as notes for the LLM, but validators must not route behavior or fail plans based on them. New slides are created in an LLM-authored additions deck and validated through XML/package inspection before merge.

Missing any of `insert_after_slide`, `title`, `learning_goal`, `why_this_slide_exists`, `what_customer_should_understand`, `visible_content_summary`, `visual_approach`, `speaker_notes`, `qa_expectations`, or `source_basis` causes a hard error.

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

---

## coverage_gap_reconciliation.json

**Advisory disposition artifact for Phase 2.5.** After running `detect_source_gaps.py`, the LLM documents how each claim-token lint signal was dispositioned. This file does not block `audit_gate.py`; missing reconciliation emits a warning when `coverage_gaps.json` still lists signals.

```json
{
  "schema_version": "1.0",
  "advisory": true,
  "reconciled_items": [
    {
      "slide_numbers": [3],
      "detector_claim": "32 gbps",
      "disposition": "covered_by_source_with_canonical_unit",
      "source_ids": ["SRC-WEB-05"],
      "rationale": "Detector tokenized deck label; AMD source uses canonical 32.75 Gb/s form."
    }
  ]
}
```

**Disposition values (non-exhaustive):** `covered_by_source_with_canonical_unit`, `not_a_fact_claim`, `out_of_scope`, `confirmed_finding`, `rejected_lint`, `escalated_to_user`.

Optional validator: `scripts/validate_coverage_reconciliation.py` — advisory report comparing detector output to reconciliation entries.
