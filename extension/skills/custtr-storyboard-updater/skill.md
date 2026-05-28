---
name: custtr-storyboard-updater
description: >
  Audit and update AMD storyboard or training PowerPoint decks against current sources,
  then produce a repair-resistant updated deck. Use for SB_Update-style deck refreshes,
  storyboard modernization, release-version updates, source-backed content additions,
  CPM/MDB/AI Engine/NoC/PMC or similar AMD training modules, and any request that asks
  to audit, plan, update, remove, or add slides while preserving instructional flow.
---

> **Canonical variant.** If multiple copies of this skill exist, the one at `$SKILL` (set during session setup) is authoritative. Do not mix scripts or references across variants.

# PSAS Storyboard Updater

Use this skill to update AMD customer-training storyboards/decks in a controlled, source-backed, repair-resistant way. The skill applies to any AMD technology domain — PCIe, memory, processing system, security, clocking, AI Engine, NoC, or any other topic. The skill is not a keyword-to-slide generator. It must first understand what the deck is trying to teach, then update every dependent part of the learning story.

### Active Update Mindset

The default assumption is that every slide needs updating — the burden of proof is on "no changes needed." Before clearing ANY slide, answer these four questions explicitly:

1. **What generation does this slide's content belong to?** Identify the product generation, release version, or technology revision the slide currently describes (e.g., "Gen 1 Versal Premium", "CPM5-era PCIe", "2025.2 release").
2. **What changed between that generation and the target?** List specific changes from your source inventory — new IP blocks, renamed interfaces, updated specs, added protocols, deprecated features. Cite `source_id` for each.
3. **What do those changes mean for THIS slide?** Trace the impact: a new controller variant may invalidate a comparison table, a protocol upgrade may change line-rate figures on a different slide, a renamed interface may affect diagram labels three slides away.
4. **What is missing?** Even if existing content is still correct, is there a gap? A slide that correctly describes CPM5 but says nothing about CPM6 has a content gap — "still correct" is not "complete."

**Valid clearing reasons** (each requires source citations):
- "Slide covers DDR5 controller register map. Sources SRC-NABU-03, SRC-PDF-01 confirm register layout unchanged between Gen 1 and Gen 2. No new registers added, no addresses changed. Gen 2 changes (expanded ECC modes) are covered on slide 14, not here."
- "Slide is a boilerplate disclaimer. Content is legal text with no technical claims."

**Invalid clearing reasons** (these are rejected by `audit_gate.py`):
- "No stale terms found" — this only means the substring scan found no keyword hits. It says nothing about content gaps.
- "Content is still valid" — valid for which generation? What changed? Why doesn't it matter here?
- "Scan is clean" / "No findings" — mechanical scans check tokens, not concepts.
- "Content looks correct" — compared to what source? At what depth?

### Universal Deck Structure

All AMD storyboard decks follow a consistent structure regardless of technology domain:

1. **Title slide** — deck name, version marker, AMD branding
2. **Objectives slide** — 3-6 learning objectives for the module
3. **Content/body slides** — technical deep-dives, architecture diagrams, feature comparisons, knowledge checks interspersed throughout
4. **Summary/recap slide** — key takeaways reflecting the full scope of the deck
5. **Disclaimer slide** — legal/attributions boilerplate
6. **AMD logo slide** — trailing slide for legal/compliance; must always remain last

## Core Rules (41 rules)

Full text with enforcement details: `references/core_rules.md`

1. Audit before editing — query MCP sources and read all user-provided material first.
2. Build a story model before planning.
3. No isolated keyword slides — map deltas to objectives, body, KCs, summary, and flow.
4. Plan before mutation — get user approval before writing an updated deck.
5. Execution order is fixed: update existing, remove obsolete, then add new.
6. Do not directly insert cloned slide XML — use standalone PPTX + merger.
7. New slides use a structured layout routed to the correct pipeline (MARP or Script).
8. Existing-slide edits are marked with OOXML change marking.
9. New slides get a yellow `New Slide` badge (auto-applied by script).
10. Narrative notes are first-class content — every slide must have full narration.
11. Knowledge checks and summaries must be updated when new content changes scope.
12. Do NOT remove authoring markers (`Fully Shared Slide`, `Slide-*`, etc.).
13. Never remove the trailing AMD logo slide.
14. Never conclude "no changes needed" without evidence.
15. Audit on two axes (topic deltas + staleness deltas), every slide, no exceptions.
16. Group-nested shapes are the most common audit miss.
17. Scope phrase + stale-term specifics on the same slide = automatic finding.
18. Mechanical gates are non-negotiable.
19. Staleness is per-deck, authored from sources — never carried over.
20. Speaker notes use verbatim `old_speaker_notes` from `original_notes.json`.
21. Speaker-notes edits default to `notes_changes` (surgical), not wholesale replacement.
22. Narrator-script style — no meta-narrative openers. See banned openers list.
23. Content-level cross-validation, not substring-level.
24. Knowledge-check slides get a dedicated audit pass.
25. Recursive source gathering during validation (Phase 2.5).
26. Pre-merge file-lock check; validate-freshness guard.
27. Five mandatory sweeps run before plan approval.
28. Structural completeness — parallel sections must receive comparable depth.
29. Summary slides must reflect the complete updated story.
30. "No feature changes" does not mean "no content changes needed."
31. Decompose every source delta into independently teachable concepts.
32. Source deltas may introduce concepts that belong to categories not yet present.
33. Documented parallelism groups 1, 2, and 4 are mandatory, not optional.
34. Speaker notes must not be the sole teaching surface for any new concept.
35. Intra-slide term consistency — diagram labels must match bullet text and source canonical forms.
36. A clean stale-term scan (0–3 hits) is a red flag of insufficient scope, not approval to skip concept decomposition and parity analysis.
37. Every `notes_update` action requires an explicit OST review outcome — set `ost_reviewed` to `"consistent"` (with `ost_review_note`) or `"companion_action_added"` (with qualifying companion action on the same slide).
38. Generational analysis is mandatory for every slide clear — document content generation, target changes, and why no impact. Passive clearing reasons are rejected.
39. Portfolio-scope slides require IP-block-level source queries — every named functional block (not just the deck's primary topic) must be checked against sources before clearing.
40. Delta-tracing sweep — grep old spec values (from source deltas) across ALL slides to catch cross-slide inconsistencies missed by per-slide auditing.
41. Image-detection heuristic — before marking `ost_reviewed: "consistent"`, verify the slide's OST is actually in text shapes, not an embedded image. Flag `image_limited` slides with `manual_review_required`.

## Required Story Questions

Before generating update actions, answer these in `story_model.json` or the plan summary:

- What is the primary message of this deck?
- What are the key talking points derived from objectives and the full deck flow?
- What is new from AMD in this topic area?
- Which existing content is inaccurate, incomplete, obsolete, or mis-sequenced?
- Does the updated deck still have a logical, instructionally sound flow?
- What does each MCP source (NABU, Confluence, JIRA) say about the topics covered in this deck?
- Are there any internal inconsistencies between slides (conflicting specs, terminology, version references)?

## Source Collection Requirements

Source collection is mandatory. The LLM must query external sources before any planning decisions.

### Minimum queries

- **NABU**: At least 3 distinct queries — (1) the deck's overall topic, (2) key technical components mentioned in slides, (3) target version features and changes.
- **Confluence/Atlassian**: At least 1 search for internal documentation, release notes, or training material updates.
- **JIRA**: At least 1 search for relevant tickets — bugs, feature requests, or completed work items for the target version.
- **Web Search**: At least 2 queries using the `WebSearch` tool — (1) the deck's primary technology + target generation (e.g. "AMD Versal Gen 2 memory controller"), (2) specific technical features or protocols covered in the deck (e.g. "LPDDR5X CXL 3.1 specifications"). Web search surfaces public datasheets, product briefs, application notes, and conference presentations that may not be in NABU or Confluence. Particularly valuable for cross-referencing specs, finding updated bandwidth/frequency figures, and catching publicly announced changes not yet in internal docs.
- **Vivado Doc Search**: At least 2 queries using the `vivado_doc_search` tool — (1) the deck's primary IP or technology (e.g. "DDR5 memory controller", "AXI NoC"), (2) target-generation architecture or feature changes (e.g. "Versal Gen 2 processing system"). Searches official Xilinx/AMD documentation including UG/PG guides, product pages, and technical wikis. Record results as `SRC-VDOC-NN` entries in `source_inventory.json`.

Search for corrections, deprecations, known issues, and updated specs — not just "what's new." Record every query and its results in `source_inventory.json`. Author `stale_terms.json` from sources during Phase 2 (schema: `references/stale_terms_schema.md`, example: `references/stale_terms.example.json`).

## Phase Routing Table

Read the indicated reference files before executing each phase. This keeps your working context focused on the current phase's rules instead of loading all ~2,000 lines at once.

| Phase | Read before executing | Script / Action |
|-------|----------------------|-----------------|
| 1 | — | `storyboard_update.py --mode audit-plan` |
| 1.5 | `references/speaker_notes_guide.md` | `extract_speaker_notes.py` |
| 2 | `references/workflow_phases.md` | MCP queries (NABU, Confluence, JIRA) |
| 2.5 | `references/workflow_phases.md` | `detect_source_gaps.py` |
| 3 | `references/workflow_phases.md` + `references/artifact_schemas.md` | Cross-validation audit + `audit_gate.py` — **0–3 stale-term hits = narrow-scope warning, not a pass. Author `concept_decomposition.json` and run parity check before advancing.** |
| 4 | `references/artifact_schemas.md` + `references/new_slide_guide.md` | Plan authoring (update_plan.json) |
| 5A | — | `apply_existing_updates.py` |
| 5A.1 | — | `post_apply_check.py` |
| 5B.1 | `references/new_slide_guide.md` | `create_additions_deck.py` (diagram layouts) |
| 5B.2 | `references/new_slide_guide.md` | `create_marp_additions.py` (MARP layouts) |
| 5C | — | `merge_storyboard.py` + `validate_deck.py` |

**Performance rule — phase-specific loading only.** Read ONLY the reference files listed for the current phase. The total reference corpus is ~2,000 lines across 9 files; loading all of them at every phase boundary wastes context and slows execution. If you need a file not listed for your current phase, load it on demand when a specific question arises.

Full workflow detail including parallelism rules, per-slide protocol, mandatory sweeps, structural parity checks, and recursive source gathering: `references/workflow_phases.md`

Artifact JSON schemas (source_inventory, reference_extract, verification_report, cross_validation_report, update_plan, field-name quick reference): `references/artifact_schemas.md`

New slide authoring (6 layouts, quality bar, training vs datasheet, hard schema constraints): `references/new_slide_guide.md`

Speaker notes (surgical diffs, paragraph boundaries, banned openers, extraction): `references/speaker_notes_guide.md`

## Running Scripts

### Setup — resolve paths once before any phase

All scripts live inside the skill directory. Set two shell variables at the start of every session so the phase commands below work without modification:

```bash
# Git Bash on Windows — run this once per session
SKILL="<path-to-custtr-storyboard-updater>"   # e.g. "$USERPROFILE/.claude/skills/custtr-storyboard-updater"

# Derive work dir from your deck path (adjust DECK to your actual file)
DECK="<path-to-your-deck.pptx>"
DECK_STEM="<deck-filename-without-extension>"
WORK="$(dirname "$DECK")/${DECK_STEM}/.storyboard_update"
```

Always use `python3`, not `python` — Git Bash on Windows resolves `python` to the Windows Store stub, which fails silently.

### Phase 1 — Extract deck

```bash
python3 "$SKILL/scripts/storyboard_update.py" \
  --deck "$DECK" \
  --target-version "2026.1" \
  --mode audit-plan
```

Produces: `$WORK/deck_extract.json`, `$WORK/story_model.json`.

### Phase 1.5 — Extract speaker notes

```bash
python3 "$SKILL/scripts/extract_speaker_notes.py" \
  --deck "$DECK" \
  --output "$WORK/original_notes.json"
```

Produces: `$WORK/original_notes.json` keyed by slide number. Required before authoring any `notes_changes` fragments.

### Phase 2.5 — Coverage gap detection

```bash
python3 "$SKILL/scripts/detect_source_gaps.py" \
  --deck-extract "$WORK/deck_extract.json" \
  --reference-extract "$WORK/reference_extract.json" \
  --output "$WORK/coverage_gaps.json"
```

### Phase 3 gate — Audit gate (run before writing the plan)

```bash
python3 "$SKILL/scripts/audit_gate.py" \
  --work-dir "$WORK"
```

Exit 0 = proceed. Exit 2 = hard failures that must be resolved first. The gate reads `stale_terms.json`, `stale_term_scan.json`, `scope_consistency.json`, `cross_validation_report.json`, and `update_plan.json` from `$WORK`.

### Phase 5A — Apply existing-slide edits

```bash
python3 "$SKILL/scripts/apply_existing_updates.py" \
  --deck "$DECK" \
  --plan "$WORK/update_plan.json" \
  --output "$WORK/updated_base.pptx"
```

On any unmatched `match_text` the script exits non-zero and writes `$WORK/apply_misses.json` with the closest actual shape text to help fix the plan. Use `--lenient-whitespace` only if whitespace normalisation is knowingly acceptable.

### Phase 5A.1 — Post-apply check

```bash
python3 "$SKILL/scripts/post_apply_check.py" \
  --original "$DECK" \
  --updated "$WORK/updated_base.pptx" \
  --stale-terms "$WORK/stale_terms.json" \
  --plan "$WORK/update_plan.json" \
  --output "$WORK/post_apply_check.json"
```

Must be run against the just-produced `updated_base.pptx`, not an older file. Exits non-zero if a promised stale-token removal silently failed.

### Phase 5B — Create additions deck (new slides only)

**5B.1 — Diagram layouts** (`ascii_diagram`, `block_diagram`):

```bash
python3 "$SKILL/scripts/create_additions_deck.py" \
  --plan "$WORK/update_plan.json" \
  --output "$WORK/additions.pptx"
```

**5B.2 — MARP-eligible layouts** (`comparison_table`, `cards`, `two_column`, `key_takeaway`):

```bash
python3 "$SKILL/scripts/create_marp_additions.py" \
  --plan "$WORK/update_plan.json" \
  --output "$WORK/marp_additions.pptx" \
  --skill-dir "$USERPROFILE/.claude/skills/psas-amd-marp"
```

### Phase 5C — Merge

```bash
python3 "$SKILL/scripts/merge_storyboard.py" \
  --base "$WORK/updated_base.pptx" \
  --additions "$WORK/additions.pptx" \
  --marp-additions "$WORK/marp_additions.pptx" \
  --plan "$WORK/update_plan.json" \
  --output "$WORK/final.pptx"
```

Either `--additions` or `--marp-additions` can be omitted if that category produced no slides. Confirm the output file is not open in PowerPoint before running.

### Phase 5C — Validate final deck

```bash
python3 "$SKILL/scripts/validate_deck.py" \
  "$WORK/final.pptx" \
  --plan "$WORK/update_plan.json" \
  --output "$WORK/validation.json"
```

Only run this after `merge_storyboard.py` exits 0.

### Common failure causes

| Error | Cause | Fix |
|---|---|---|
| `python: command not found` or Windows Store opens | `python` resolves to Store stub | Use `python3` |
| `ModuleNotFoundError: No module named 'pptx'` | python-pptx not installed | `pip3 install python-pptx` |
| `apply_misses.json` written | `apply_existing_updates.py` found unmatched shape text | Check file for closest matches; fix the plan |
| `PermissionError` on output `.pptx` | File open in PowerPoint | Close the deck and re-run |
| `audit_gate.py` exits 2 | Mechanical findings unresolved | Resolve findings, then re-run |

## Scripts

- `scripts/storyboard_update.py`: top-level CLI. Modes: `audit-plan`, `audit-only`, `execute`.
- `scripts/extract_deck.py`: PPTX extraction (flattens group-nested shapes).
- `scripts/extract_speaker_notes.py`: dump verbatim speaker notes to JSON.
- `scripts/build_story_model.py`: infer objectives, primary message, talking points, generational questions, and stale-terms template from the deck.
- `scripts/build_update_plan.py`: story-model-driven plan generation from extraction and source deltas.
- `scripts/detect_source_gaps.py`: identify uncovered factual claims per slide.
- `scripts/stale_terms.py`: per-deck `stale_terms.json` loader, matcher, and mandatory sweeps.
- `scripts/stale_term_scan.py`: Axis-B scan — finds stale tokens honouring guards and `intentionally_kept`.
- `scripts/scope_consistency_scan.py`: flags slides combining scope phrases with stale-token specifics.
- `scripts/audit_gate.py`: final mechanical gate before plan execution.
- `scripts/validate_plan.py`: validate `update_plan.json` against the v2.0 schema.
- `scripts/apply_existing_updates.py`: existing-slide text/notes edits with OOXML marking.
- `scripts/post_apply_check.py`: differential re-scan after apply; refuses merge if removals failed.
- `scripts/create_additions_deck.py`: new slides for diagram layouts (native PPT shapes).
- `scripts/create_marp_additions.py`: new slides for MARP-eligible layouts (table/cards/column/takeaway).
- `scripts/ascii_to_diagram.py`: parse ASCII box-drawing art into native PowerPoint shapes.
- `scripts/merge_storyboard.py`: range-based merge wrapper around `psas-pptx-merger`.
- `scripts/validate_deck.py`: package/order/content validation.
- `scripts/constants.py`: shared constants (layouts, action types, regexes, quality-bar constants).
- `scripts/ooxml_helpers.py`: shared OOXML/DrawingML helpers (namespaces, parsing, serialization).

## Dependencies

- `python3`
- `lxml` for `psas-pptx-merger`
- `python-pptx` for new slide generation and existing-slide edits
- Imported skills: `psas-pptx-merger` for merging slides between decks

## Validation Checklist

Mechanical checks are enforced by `audit_gate.py` (pre-apply) and `post_apply_check.py` + `validate_deck.py` (post-apply). These are the **human-judgement** checks:

- Instructional flow still reads correctly — slides build on each other, no forward-references.
- Narration on new/updated slides matches the deck's existing voice (orient, walk, connect, transition).
- Diagrams visually parse — boxes aligned, connectors land correctly, colors consistent.
- Knowledge-check questions still have a unique correct answer after content changes.
- Summary slide reflects the actual final talking points of the updated deck.
- `stale_terms.json` was authored from sources this run (not copied from a previous deck).
- Speaker-notes edits use `notes_changes` (surgical) — no wholesale replacement without justification.
- Title-slide version equals `target_version` exactly.
- Authoring markers (`Fully Shared Slide`, `Partially Shared Slide`, `Slide-*`) are preserved.
- Trailing AMD logo slide is preserved as the last slide.

`validate_deck.py` enforces the rest automatically: zipfile integrity, slide/notes counts, insertion point correctness, version-label hygiene, new-slide badge presence, edit-highlight markup, merger audit cleanliness, and speaker-notes presence on new/updated content slides.

## Fast-Track Mode

These optimizations reduce wall-clock time from 130-270 minutes to 50-80 minutes without sacrificing audit quality.

**What changes:**

- **Batch audit writes** — Phase 3 writes verification rows in batches of 5-10 slides per file (`batch_NN.json`) instead of one file per slide. Reduces ~42 file writes to ~5, cutting context-break overhead by ~80%.
- **1-round recursive cap** — Phase 2.5 recursive source gathering caps at 1 round per slide (was 3). After one round, all unresolved gaps are batch-escalated to the user in a single summary.
- **Template-based stale terms** — `build_story_model.py` outputs a `stale_terms_template` with candidate entries auto-detected from deck content (version tokens, product/IP names). The LLM reviews and adjusts the template instead of authoring from scratch.
- **Boilerplate slide shortcut** — Slides classified as `boilerplate` or `blank` by `build_story_model.py` can be batch-cleared with a single generational analysis entry covering the group, rather than individual per-slide analysis. The analysis must still explain why boilerplate content is generation-agnostic.

**What does NOT change:**

- All mechanical gates (`audit_gate.py`, `post_apply_check.py`, `validate_deck.py`) run identically.
- Every slide must appear in `slides_examined` — no slide is skipped.
- `source_basis` requirements are unchanged — every finding and every clear must cite sources.
- Parallelism groups 1, 2, and 4 remain mandatory.
- Generational analysis (Rule 38) is required on every cleared slide.
- Phase-specific reference loading — read only the files listed for the current phase.
