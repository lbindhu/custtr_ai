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

### Cursor Plan Mode Gate

This skill must start in Cursor Plan mode. If the current conversation is not already in Plan mode, immediately call `SwitchMode(target_mode_id="plan")` before any deck-update workflow step, source collection that creates artifacts, plan authoring, deck mutation, execution-phase command, or validation command. Do not proceed until the mode switch is accepted.

Cursor Plan mode is separate from the storyboard `update_plan.json` approval checkpoint. Plan mode is required before starting the workflow; the Phase 3 to Phase 4 user checkpoint and approved `update_plan.json` are still required before mutating a deck.

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

### Readable Update Protocol

Source accuracy is necessary but not sufficient. The updated deck must remain clear enough for a learner to consume and for an instructor to teach from. Existing-slide OST edits still use visible review marking, but the plan author must choose update tactics that keep the marked slide readable instead of mechanically diffing every changed character.

Before finalizing `update_plan.json`, calibrate readability expectations with the user when the update is likely to change slide meaning, layout density, or narration style:

- Ask for sample before/after slides, a deck excerpt, or a description of what became hard to read in prior runs.
- Show the user the available update approaches when preferences are unclear: small marked term/value edit, full-shape marked replacement, redesigned existing slide, added clean slide, or removal/deprecation during merge.
- Confirm how visible marking should be handled for outdated text, dense tables, diagram labels, knowledge checks, version markers, and speaker notes.
- Record the selected approach in the plan `reason` or `description` for high-impact actions.

Use this action-selection rubric:

- Use `fragment_replace` for small term, value, or label corrections where yellow/strikethrough marking remains easy to parse.
- Use `update_existing` only when the full marked replacement will still read as a coherent slide. Avoid using it for long paragraph rewrites, dense table reshaping, or wholesale bullet restructuring.
- When a change alters the teaching structure of a slide, prefer a redesigned existing slide or an `add_new_slide` action that presents the updated concept cleanly and matches the surrounding visual system.
- Treat dense tables, diagrams, and knowledge checks as high-clutter risks. Review the rendered result or describe the expected marked appearance before execution.
- For version changes, update the title/version marker directly and trace old version tokens across the deck; avoid scattering noisy character-level edits where a clean version label replacement is sufficient.
- Speaker notes should be narrator-ready and easy to read. The plan should prefer clean, well-written notes text and source-backed audit documentation over noisy note-level diff artifacts. Current tooling may still apply diff-style marking to `notes_changes`; do not claim clean notes are enforced at runtime unless the scripts have been changed.

Current execution limits to account for in plan authoring:

- `update_existing` multi-edit behavior is documented with `replacements[]` and the apply script supports it, but `validate_plan.py` currently requires top-level `match_text` and `replacement_text`; include a top-level edit when using multi-edit actions until the validator is updated.
- `remove_or_deprecate` is applied during final merge composition, not as an in-place text edit by `apply_existing_updates.py`.
- Visible text matching is text-based rather than `shape_id`-based. If the same label or table value appears more than once, use a more precise fragment, split the action, or document a manual review requirement.
- `post_apply_check.py` catches stale-token leaks and apply misses; it does not judge final slide readability or clean speaker-note quality.
- Source-backed gates are strongest when `audit_gate.py --stage pre-execute --require-sources` is used. If execution is run without `--require-sources`, document why source coverage is still sufficient.

## Core Rules (48 rules)

Full text with enforcement details: `references/core_rules.md` — rule numbers must match.

1. Audit before editing — query MCP sources and read all user-provided material first.
2. Build a story model before planning.
3. No isolated keyword slides — map deltas to objectives, body, KCs, summary, and flow.
4. Plan before mutation — get user approval before writing an updated deck.
5. Execution order is fixed: update existing, remove obsolete, then add new.
6. Do not directly insert cloned slide XML — use standalone PPTX + merger.
7. New slides are authored under LLM control to match the visual flow of the existing deck; no fixed layout factory or external templating route is used.
8. Existing-slide edits are marked with OOXML change marking, but plans must avoid unreadable marked rewrites.
9. New slides must pass XML/package QA; badges or callouts are used only when they fit the deck's authoring style.
10. Narrative notes are first-class content — every slide must have full narration.
11. Knowledge checks and summaries must be updated when new content changes scope.
12. Do NOT remove authoring markers (`Fully Shared Slide`, `Slide-*`, etc.).
13. Never remove the trailing AMD logo slide.
14. Never conclude "no changes needed" without evidence.
15. Audit on two axes (topic deltas + staleness deltas), every slide, no exceptions.
16. Group-nested shapes are the most common audit miss.
17. Scope phrase + stale-term specifics on the same slide = advisory lint signal until the LLM confirms the slide-level impact.
18. Mechanical gates are non-negotiable.
19. Staleness is per-deck, authored from sources — never carried over.
20. Speaker notes use verbatim `old_speaker_notes` from `original_notes.json`.
21. Speaker-notes edits default to `notes_changes` (surgical), not wholesale replacement; notes must remain narrator-ready and readable.
22. Narrator-script style — no meta-narrative openers. See banned openers list.
23. Content-level cross-validation, not substring-level.
24. Knowledge-check slides get a dedicated audit pass.
25. Recursive source gathering during validation (Phase 2.5).
26. Pre-merge file-lock check; validate-freshness guard.
27. Mechanical sweeps run before plan approval, but heuristic sweeps produce lint signals that require LLM disposition rather than automatic semantic conclusions.
28. Structural completeness — parallel sections must receive comparable depth.
29. Summary slides must reflect the complete updated story.
30. No feature changes does not mean no content changes needed.
31. Decompose every source delta into independently teachable concepts.
32. Source deltas may introduce concepts that belong to categories not yet present.
33. Parallelism is optional and conditional — use it for expensive independent retrieval or generation, not for tightly coupled reasoning artifacts where shared context improves correctness.
34. Speaker notes must not be the sole teaching surface for any new concept.
35. Intra-slide term consistency — diagram labels must match bullet text and source canonical forms. Two-layer enforcement: a deterministic backstop `consistency_scan.py` (near-miss letter-edit variants like `A78AE`≠`A78E`, ignoring digit-only generation siblings like `CPM5`/`CPM6`), AND a mandatory LLM proofreading pass authored to `proofread_review.json` (deck-wide spelling, grammar, intra- and cross-slide consistency the script cannot find). The proofreading pass must disposition every script signal; every non-advisory violation must be reconciled (finding, action, token-naming clear, or documented proofread dismissal) before `audit_gate.py` passes.
36. Before authoring JSON artifacts, read `references/artifact_schemas.md` field-name table — subagents must receive the same instruction.
37. A clean stale-term scan (0–3 hits) is advisory lint to review scope — not a hard failure and not a reason to pad stale terms or actions.
38. Every `notes_update` action requires an explicit OST review outcome — set `ost_reviewed` to `"consistent"` (with `ost_review_note`) or `"companion_action_added"` (with qualifying companion action on the same slide).
39. Generational analysis is mandatory for every slide clear — document content generation, target changes, and why no impact. Passive clearing reasons are rejected.
40. Portfolio-scope slides require IP-block-level source queries — every named functional block (not just the deck's primary topic) must be checked against sources before clearing.
41. Delta-tracing sweep — grep old spec values (from source deltas) across ALL slides to catch cross-slide inconsistencies missed by per-slide auditing.
42. Image-detection heuristic — before marking `ost_reviewed: "consistent"`, verify the slide's OST is actually in text shapes, not an embedded image. Flag `image_limited` slides with `manual_review_required`.
43. Never write custom highlight code — import and call `add_highlight(rpr)` from `ooxml_helpers.py` for all highlight operations. OOXML requires `<a:highlight>` after `<a:effectLst>` and before `<a:uLnTx>`; PowerPoint silently ignores highlights placed elsewhere. `post_apply_check.py` validates highlight positioning and will flag violations.
44. Mandatory user checkpoint between Phase 3 and Phase 4 — write `$WORK/audit_summary.md`, present findings scope, and wait for user acknowledgement before `update_plan.json`. See `references/workflow_phases.md`.
45. Scope-depth diagnostics are advisory — `audit_gate.py` warns on suspiciously shallow stale-term, parity, concept, or action counts, while hard failures remain tied to evidence, schema, stale-hit reconciliation, notes, and package contracts.
46. Stale-hit reconciliation is mandatory — every surviving entry in `stale_term_scan.json` must be represented by a verification finding, addressed by an update-plan action, covered by an `intentionally_kept` exception, or explicitly cleared with a token/location-specific reason. A slide with a surviving stale hit cannot be cleared by generic generational analysis alone.
47. Cursor Plan mode is required before storyboard work — if the current conversation is not already in Plan mode, call `SwitchMode(target_mode_id="plan")` before any deck-update workflow step. Do not run source collection that creates artifacts, plan authoring, mutation, execution, or validation commands until the mode switch is accepted.
48. Final PPTX validation is XML/package-only — never open generated or updated `.pptx` files in PowerPoint, LibreOffice, COM automation, browser UI, or any presentation viewer after merge. Updated decks may require PowerPoint repair, so validate by inspecting the package and XML: `validate_deck.py`, `post_apply_check.py`, `extract_deck.py`, direct `zipfile` reads, `ppt/slides/*.xml`, `ppt/notesSlides/*.xml`, relationships, `[Content_Types].xml`, and merge sidecars.

## Required Story Questions

Before generating update actions, answer these across `story_model.json`, source artifacts, and the plan summary:

- What is the primary message of this deck?
- What are the key talking points derived from objectives and the full deck flow?
- What does the deck appear to teach before source research?
- What is new from AMD in this topic area according to source collection?
- Which existing content is inaccurate, incomplete, obsolete, or mis-sequenced according to Phase 3 audit artifacts?
- Does the updated deck still have a logical, instructionally sound flow?
- What does each MCP source (NABU, Confluence, JIRA) say about the topics covered in this deck?
- Are there any internal inconsistencies between slides (conflicting specs, terminology, version references)?

`story_model.json` is LLM-authored from `deck_extract.json`; Python only creates the deterministic extraction plus `story_model_prompt.md` and `story_model_scaffold.json`. The story model may identify teaching purpose, flow, candidate stale terms, and source-research hypotheses, but it must not make source-backed clears or findings. Run `validate_story_model.py` before continuing beyond Phase 1.

## Source Collection Requirements

Source collection is mandatory, but fixed channel counts are not. The LLM chooses source channels based on the deck's claim clusters, target generation, and available authoritative material. Use NABU, Confluence/Atlassian, JIRA, Web Search, Vivado documentation, and user-provided files when they are relevant to the claims being audited.

### Source sufficiency policy

- Every major claim cluster and every source-backed finding must cite at least one authoritative source entry.
- Prefer internal or official AMD/Xilinx sources when they exist; use public web sources for public specs, datasheets, or cross-checks when internal sources are unavailable or insufficient.
- Record attempted but unavailable channels in `source_inventory.json` with a short rationale. Do not run ritual searches just to satisfy a count.
- For every source used in a claim or finding, build `reference_extract.json` with verbatim source text chunks (`source_id`, `section`, `text`, `claim_keys`). `quoted_source` values in the audit must be literal substrings of `reference_extract.json`.
- Author `stale_terms.json` from the current deck and current sources during Phase 2. Do not copy stale-term lists across decks.

`detect_source_gaps.py`, stale-term scans, and parity scans are lint aids. They can suggest missing evidence or structural questions, but the LLM must decide source-to-claim entailment and document each signal as confirmed, rejected, or intentionally out of scope.

## Phase Routing Table

Read the indicated reference files before executing each phase. This keeps your working context focused on the current phase's rules instead of loading all ~2,000 lines at once.

| Phase | Read before executing | Script / Action |
|-------|----------------------|-----------------|
| 1 | `references/story_model_guide.md` | `storyboard_update.py --mode audit-plan` creates `deck_extract.json`, `story_model_prompt.md`, and `story_model_scaffold.json`; LLM authors `story_model.json`; `validate_story_model.py` gates continuation |
| 1.5 | `references/speaker_notes_guide.md` | `extract_speaker_notes.py` |
| 2 | `references/workflow_phases.md` | MCP queries (NABU, Confluence, JIRA) |
| 2.5 | `references/workflow_phases.md` | Optional advisory lint with `detect_source_gaps.py`; LLM dispositions are authoritative |
| 3 | `references/workflow_phases.md` + `references/artifact_schemas.md` | Cross-validation audit; `merge_slide_rows.py` assembles `verification_report.json`; author `concept_decomposition.json`; run the LLM proofreading pass → `proofread_review.json` (disposition every `consistency_scan.json` signal + record semantic/grammar/cross-slide issues, Rule 35); then `audit_gate.py --stage pre-plan` — low stale-hit or parity counts are warnings, not hard blockers |
| 3→4 | `references/audit_summary_guide.md` | **MANDATORY USER CHECKPOINT** — write `$WORK/audit_summary.md`, present findings scope; wait for user acknowledgement before `update_plan.json` |
| 4 | `references/artifact_schemas.md` + `references/new_slide_guide.md` | Plan authoring (update_plan.json) |
| 4.5 | `references/artifact_schemas.md` | `validate_plan.py` + `audit_gate.py --stage pre-execute` — **validates plan schema, field names, action structure, source mapping, and gate reconciliation before execution** |
| 5A | — | `apply_existing_updates.py` |
| 5A.1 | — | `post_apply_check.py` |
| 5B | `references/new_slide_guide.md` | LLM-authored additions deck (`$WORK/additions.pptx`) with XML/package QA |
| 5C | — | `merge_storyboard.py` + `validate_deck.py` |

**Performance rule — phase-specific loading only.** Read ONLY the reference files listed for the current phase. The total reference corpus is ~2,000 lines across 9 files; loading all of them at every phase boundary wastes context and slows execution. If you need a file not listed for your current phase, load it on demand when a specific question arises.

Full workflow detail including per-slide protocol, deterministic sweeps, advisory lint signals, structural parity review, and source gathering: `references/workflow_phases.md`

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
FINAL_OUTPUT="$(dirname "$DECK")/${DECK_STEM}_V1.pptx"
```

To save the final deck to a different location, override `FINAL_OUTPUT` before running Phase 5C. By default it is saved next to the original deck with a `_V1` suffix.

Always use `python3`, not `python` — Git Bash on Windows resolves `python` to the Windows Store stub, which fails silently.

### Phase 1 — Extract deck and author story model

```bash
python3 "$SKILL/scripts/storyboard_update.py" \
  --deck "$DECK" \
  --target-version "2026.1" \
  --mode audit-plan
```

Produces: `$WORK/deck_extract.json`, `$WORK/story_model_prompt.md`, and `$WORK/story_model_scaffold.json`, then stops until the LLM authors `$WORK/story_model.json`.

After authoring the story model, validate it:

```bash
python3 "$SKILL/scripts/validate_story_model.py" \
  --deck-extract "$WORK/deck_extract.json" \
  --story-model "$WORK/story_model.json"
```

Re-run `storyboard_update.py --mode audit-plan` after validation to continue to stale-term scaffolding and mechanical scans.

### Phase 1.5 — Extract speaker notes

```bash
python3 "$SKILL/scripts/extract_speaker_notes.py" \
  --deck "$DECK" \
  --output "$WORK/original_notes.json"
```

Produces: `$WORK/original_notes.json` keyed by slide number. Required before authoring any `notes_changes` fragments.

### Phase 2.5 — Advisory coverage lint

```bash
python3 "$SKILL/scripts/detect_source_gaps.py" \
  --deck-extract "$WORK/deck_extract.json" \
  --reference-extract "$WORK/reference_extract.json" \
  --output "$WORK/coverage_gaps.json"
```

Produces advisory claim-token lint signals. Use this output as search guidance; the LLM must decide whether each signal is supported, contradicted, insufficiently sourced, irrelevant, or intentionally out of scope.

### Phase 3 — Merge slide rows and pre-plan gate

After auditing all slides into `slide_rows/batch_*.json`:

```bash
python3 "$SKILL/scripts/merge_slide_rows.py" \
  --work-dir "$WORK"
```

Then run the pre-plan gate:

```bash
python3 "$SKILL/scripts/audit_gate.py" \
  --work-dir "$WORK" \
  --stage pre-plan
```

Exit 0 = proceed to the mandatory user checkpoint. Exit 1 or 2 = evidence, schema, or reconciliation failures that must be resolved first. The pre-plan gate reads `deck_extract.json`, `source_inventory.json`, `reference_extract.json`, `verification_report.json`, `cross_validation_report.json`, `stale_terms.json`, `stale_term_scan.json`, `scope_consistency.json`, and `concept_decomposition.json` from `$WORK`. `parity_matrix.json` is advisory when present. It does not require `update_plan.json`.

### Phase 4.5 — Validate plan and pre-execute gate

```bash
python3 "$SKILL/scripts/validate_plan.py" \
  --plan "$WORK/update_plan.json" \
  --story-model "$WORK/story_model.json"

python3 "$SKILL/scripts/audit_gate.py" \
  --work-dir "$WORK" \
  --stage pre-execute \
  --require-sources
```

Only proceed to Phase 5 after both commands exit 0. The pre-execute gate includes plan action mapping, source-basis checks, scope-consistency reconciliation, notes/OST coherence, original-notes validation, stale-hit reconciliation, and advisory scope-depth diagnostics.

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

### Phase 5A.2 — Execution-gap checklist

Before moving from `updated_base.pptx` to merge, review the current execution limitations:

- Confirm every `update_existing` target is unambiguous. The apply script matches by visible text, not by `shape_id`; repeated labels or table values require manual review.
- Confirm any `replacements[]` usage also satisfies the current validator's top-level `match_text`/`replacement_text` requirement, or split the edits into separate actions.
- Confirm `remove_or_deprecate` actions are expected to affect the final merge output, not the intermediate `updated_base.pptx`.
- Confirm speaker-note updates are instructionally clean even if the current tooling renders note changes with diff-style marking.
- Confirm `post_apply_check.py` was treated as a stale-token/apply-miss gate only. It does not replace rendered readability review for marked slides, dense diagrams, tables, or notes.
- Prefer running the pre-execute gate with `--require-sources`; if omitted, document the source-coverage rationale before finalizing.

### Phase 5B — Create additions deck (new slides only)

Read `references/new_slide_guide.md`, inspect the existing deck's visual
system, then create `$WORK/additions.pptx` under LLM control. The additions
deck must contain new slides in the same order as the approved `add_new_slide`
actions. Do not route new slides through fixed layout-generation scripts or
external templating backends. Perform XML/package QA before merging and keep
the final merged-output validation XML/package-only.

### Phase 5C — Merge

```bash
python3 "$SKILL/scripts/merge_storyboard.py" \
  --base "$WORK/updated_base.pptx" \
  --additions "$WORK/additions.pptx" \
  --plan "$WORK/update_plan.json" \
  --output "$FINAL_OUTPUT"
```

Omit `--additions` only when the approved plan has no `add_new_slide` actions. Confirm the output file is not open in PowerPoint before running.

### Phase 5C — Validate final deck

```bash
python3 "$SKILL/scripts/validate_deck.py" \
  "$FINAL_OUTPUT" \
  --plan "$WORK/update_plan.json" \
  --output "$WORK/validation.json"
```

Only run this after `merge_storyboard.py` exits 0.

This final validation step is XML/package-only. Do not open `$FINAL_OUTPUT` in PowerPoint or any presentation viewer for validation; inspect the PPTX as a ZIP/OOXML package instead.

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
- `scripts/build_story_model.py`: scaffold `story_model_scaffold.json` and `story_model_prompt.md`; the LLM authors the real `story_model.json`.
- `scripts/validate_story_model.py`: validate the LLM-authored story model against `deck_extract.json`.
- `scripts/build_update_plan.py`: legacy draft-plan scaffold helper; normal plans are LLM-authored and validated by `validate_plan.py`.
- `scripts/merge_slide_rows.py`: assemble `verification_report.json` from `slide_rows/batch_*.json` sidecars.
- `scripts/validate_coverage_reconciliation.py`: advisory report comparing coverage lint to reconciliation dispositions.
- `scripts/lint_skill_docs.py`: scan skill docs for stale architecture phrases.
- `scripts/detect_source_gaps.py`: advisory claim-token lint (not proof of missing sources).
- `scripts/stale_terms.py`: per-deck `stale_terms.json` loader, matcher, and mandatory sweeps.
- `scripts/stale_term_scan.py`: Axis-B scan — finds stale tokens honouring guards and `intentionally_kept`.
- `scripts/scope_consistency_scan.py`: flags slides combining scope phrases with stale-token specifics.
- `scripts/consistency_scan.py`: intra-slide term consistency (Rule 35) — detects near-miss technical-token variants (e.g. `A78AE`≠`A78E`) within one slide and advisory typos; writes `consistency_scan.json`.
- `scripts/audit_gate.py`: final mechanical gate before plan execution.
- `scripts/validate_plan.py`: validate `update_plan.json` against the v2.0 schema.
- `scripts/apply_existing_updates.py`: existing-slide text/notes edits with OOXML marking.
- `scripts/post_apply_check.py`: differential re-scan after apply; refuses merge if removals failed.
- `scripts/ascii_to_diagram.py`: parse ASCII box-drawing art into native PowerPoint shapes.
- `scripts/merge_storyboard.py`: range-based merge wrapper around `psas-pptx-merger`.
- `scripts/validate_deck.py`: package/order/content validation.
- `scripts/constants.py`: shared constants (layouts, action types, regexes, quality-bar constants).
- `scripts/ooxml_helpers.py`: shared OOXML/DrawingML helpers (namespaces, parsing, serialization).

## Dependencies

- `python3`
- `lxml` for `psas-pptx-merger`
- `python-pptx` or another LLM-chosen PPTX method for existing-slide edits and any additions that need programmatic PowerPoint manipulation
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

Final merged-output validation must remain XML/package-only because the produced deck may require PowerPoint repair. Check text presence, notes presence, shape geometry values, relationships, slide order, stale tokens, highlight placement, authoring markers, and package structure through OOXML inspection rather than by opening the deck.

## Fast-Track Mode

These optimizations reduce wall-clock time from 130-270 minutes to 50-80 minutes without sacrificing audit quality.

**What changes:**

- **Batch audit writes** — Phase 3 writes verification rows in batches of 5-10 slides per file (`batch_NN.json`) instead of one file per slide. Reduces ~42 file writes to ~5, cutting context-break overhead by ~80%.
- **1-round recursive cap** — Phase 2.5 recursive source gathering caps at 1 round per slide (was 3). After one round, all unresolved gaps are batch-escalated to the user in a single summary.
- **Template-based stale terms** — `story_model_scaffold.json` includes `stale_terms_candidates` auto-detected from deck content (version tokens, product/IP names). The LLM reviews those candidates during source-backed stale-term authoring instead of accepting them as truth.
- **Boilerplate slide shortcut** — Slides classified as `boilerplate` or `blank` in the validated LLM story model can be batch-cleared with a single generational analysis entry covering the group, rather than individual per-slide analysis. The analysis must still explain why boilerplate content is generation-agnostic.

**What does NOT change:**

- All mechanical gates (`audit_gate.py`, `post_apply_check.py`, `validate_deck.py`) run identically.
- Every slide must appear in `slides_examined` — no slide is skipped.
- `source_basis` requirements are unchanged — every finding and every clear must cite sources.
- Parallelism remains optional and should be used only when it reduces wall-clock time without fragmenting shared reasoning context.
- Generational analysis (Rule 39) is required on every cleared slide.
- Phase-specific reference loading — read only the files listed for the current phase.
