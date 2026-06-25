# Workflow Phases

## Mandatory Workflow

This workflow has 5 phases. Phases 1-4 run before any deck mutation. Do not skip phases or reorder them.

### Parallelism Guidance

Parallelism is a performance option, not a correctness rule. Use concurrent tool calls or subagents for expensive independent retrieval, rendering, or file analysis only when outputs are independent and shared reasoning context is not harmed.

Good candidates:
- Phase 1.5 speaker-notes extraction can run while source collection starts.
- Independent source searches can run concurrently when their query intent is already clear.
- Phase 5A and Phase 5B can run concurrently only when new slides do not depend on inspecting `updated_base.pptx`.

Avoid parallelism for tightly coupled semantic work such as story modeling, source-to-claim entailment, concept decomposition, and plan authoring unless the deck is large and the artifact boundaries are explicit. Subagents do not inherit parent context and must receive exact schema and source instructions.

**Must remain sequential:**
- Phase 2.5 (coverage gaps) depends on both Phase 1 output AND Phase 2 output — cannot start until both are done.
- Phase 3 depends on Phase 1.5 (speaker notes) AND Phase 2.5 — cannot start until both are done.
- Phase 5A.1 (post-apply check) must run after Phase 5A, before Phase 5C.
- Phase 5C (merge) must wait for Phase 5A.1 and the LLM-authored additions deck when new slides are planned.

**Quality invariant:** Parallelism never substitutes for LLM judgment or mechanical validation. If coordination overhead would increase error risk, run sequentially.

### Phase 1. Extract and Author Story Model

Run:

```bash
python3 "$SKILL/scripts/storyboard_update.py" \
  --deck "$DECK" \
  --target-version "2026.1" \
  --mode audit-plan
```

(`$SKILL` and `$DECK` must be set — see "Running Scripts -> Setup" below.)

This creates `<deck_dir>/<deck_stem>/.storyboard_update/` with deterministic deck extraction plus story-model authoring materials:

- `deck_extract.json` — Python-extracted slide, text-shape, notes, relationship, and authoring-marker data.
- `story_model_prompt.md` — instructions for the LLM story-model authoring pass.
- `story_model_scaffold.json` — heuristic starter data. It is not authoritative.

The workflow then stops until the LLM authors `story_model.json` using `references/story_model_guide.md`. Run:

```bash
python3 "$SKILL/scripts/validate_story_model.py" \
  --deck-extract "$WORK/deck_extract.json" \
  --story-model "$WORK/story_model.json"
```

Only after validation passes may the workflow continue to Phase 1.5, Phase 2, stale-term authoring, or mechanical scans. `story_model.json` captures instructional meaning and source-research hypotheses only; it must not contain source-backed clears, findings, or update actions.

### Phase 1.5. Extract Speaker Notes (mandatory — may run concurrently with Phase 2)

```bash
python3 "$SKILL/scripts/extract_speaker_notes.py" \
  --deck "$DECK" \
  --output "$WORK/original_notes.json"
```

Dumps verbatim speaker notes from every slide to a JSON keyed by `slide_number`. Required input for any `notes_update` action's `old_speaker_notes` field. See "Speaker-Notes Ground Truth & Diff Semantics".

### Phase 2. Source Collection (mandatory — cannot be skipped)

Collect sources to cover the deck's claim clusters, not to satisfy fixed channel counts. The LLM chooses the relevant channels: NABU, Confluence/Atlassian, JIRA, Web Search, Vivado documentation, user-provided PDFs/docs, or other authoritative material.

Source sufficiency requirements:

- Every major claim cluster and every source-backed finding must cite at least one authoritative source entry.
- Prefer internal or official AMD/Xilinx sources when available. Use public web sources for public specs, datasheets, or cross-checks when they materially improve evidence.
- Portfolio-scope slides still need adjacent-domain review, but the LLM may batch queries and document why a block is unaffected or out of scope.
- Record attempted but unavailable channels in `source_inventory.json` with rationale. Do not run ritual searches merely to satisfy a number.

Incorporate user-provided inputs: PDFs, docs, links, notes, constraints.

Build a `source_inventory` documenting what was queried, what was found, and what was unavailable. Save it to `.storyboard_update/source_inventory.json`.

Build `reference_extract.json` from the source results before Phase 2.5. Each entry must contain verbatim source text that can support later `quoted_source` fields:

```json
{
  "entries": [
    {
      "source_id": "SRC-NABU-01",
      "section": "Release notes / feature delta",
      "text": "Verbatim source passage copied from the authoritative result.",
      "claim_keys": ["PCIe Gen 6", "64 GT/s"]
    }
  ]
}
```

Every `quoted_source` in `verification_report.json` must be a literal case-insensitive substring of one of these `text` fields. If a required source cannot be fetched, record the attempted query in `source_inventory.json` and escalate the missing evidence to the user; do not fabricate `reference_extract.json` passages.

**Gate**: Present the source inventory to the user before proceeding. If no MCP sources were queried, explain why and get explicit user approval to continue without them.

### Phase 2.5. Advisory Coverage Lint & Targeted Source Gathering

```bash
python3 <skill_dir>/scripts/detect_source_gaps.py \
  --deck-extract <work_dir>/deck_extract.json \
  --reference-extract <work_dir>/reference_extract.json \
  --output <work_dir>/coverage_gaps.json
```

`detect_source_gaps.py` emits advisory claim-token lint signals. Token overlap is not proof that a source supports a claim, and missing token overlap is not proof that no source exists. Use the output as search guidance, then let the LLM disposition each signal as supported, contradicted, insufficiently sourced, irrelevant mention, or intentionally out of scope. Audit may advance when the LLM-authored verification artifacts provide source-backed dispositions, even if the advisory lint file still contains signals.

### Phase 3. Cross-Validation Audit (mandatory — cannot be skipped)

This is a **shape-level, two-axis, every-slide-covered** audit. Every shape on every content slide must be checked individually against **both** audit axes. Finding one issue on a slide is not an audit — it is the start of an audit. Do not move on to the next slide until all shapes on the current slide have been checked against both axes.

---

> ### **STOP — Pre-Flight Checklist: Exact Field Names for Phase 3 and Phase 4 Artifacts**
>
> **Read these struct definitions before writing any JSON artifact.** The gates (`audit_gate.py`, `validate_plan.py`) reject wrong field names with no tolerance — getting them right the first time eliminates the fix→run→error→fix loop. If you are spawning a subagent to write these artifacts, **paste these struct definitions into the agent prompt** — subagents do not inherit your context.
>
> #### Part A — Phase 3 artifact structs (validated by `audit_gate.py`)
>
> **`verification_report.json`**
> ```
> { "slides": [
>     { "slide_number": <int>,          ← NOT "slide"
>       "claims_verified": [
>         { "claim": <str>,
>           "source_id": <str>,
>           "quoted_source": <str>       ← ≥30 chars, literal case-insensitive substring of reference_extract corpus
>         }
>       ],
>       "findings": [
>         { "finding_id": <str>,         ← e.g. "F-03", "NS-01"
>           "type": <str>,               ← "content_gap"|"stale_content"|"new_slide_candidate"|...
>           "recommended_action_type": <str>,
>           "action_required": <bool>,
>           "description": <str>,
>           "source_id": <str>,
>           "quoted_source": <str>       ← same ≥30 char literal substring rule
>         }
>       ],
>       "open_questions": [],            ← empty array, or all entries must have blocks_finalization: false
>       "additional_sources_needed": [], ← must be empty array
>       "knowledge_check_review": {...}, ← REQUIRED on KC slides
>       "summary_review": {...}          ← REQUIRED on summary slides
>     }
>   ]
> }
> ```
> `new_slide_candidate` findings require 7 extra fields:
> `concept`, `why_existing_slide_update_is_insufficient`, `insert_after_slide`,
> `learning_goal`, `flow_dependencies`, `visual_intent`, `qa_expectations`
>
> **`cross_validation_report.json`**
> ```
> { "slides_examined": [1, 2, ..., N],  ← must equal ALL slide numbers in deck
>   "slides_explicitly_cleared": [
>     { "slide": <int>,                 ← NOT "slide_number" — this file uses "slide"
>       "reason": <str>,                ← no banned passive phrases (see Part C)
>       "source_ids": [<str>, ...],     ← non-empty array
>       "generational_analysis": {
>         "content_generation": <str>,          ← ≥10 chars
>         "target_generation_changes": <str>,   ← ≥20 chars
>         "why_no_impact": <str>                ← ≥30 chars, no banned passive phrases
>       }
>     }
>   ],
>   "findings_cleared": [
>     { "finding_id": <str>, "reason": <str>, "source_ids": [<str>] }
>   ]
> }
> ```
>
> **`concept_decomposition.json`**
> ```
> { "source_deltas": [
>     { "delta_id": <str>,
>       "description": <str>,
>       "source_ids": [<str>],
>       "teachable_concepts": [
>         { "concept": <str>,            ← NOT "concept"
>           "current_coverage": <str>,   ← NOT "coverage"
>           "adequate": <bool>,
>           "recommended_action": <str>, ← NOT "action"
>           "target_slides": [<int>]
>         }
>       ]
>     }
>   ]
> }
> ```
>
> #### Part B — Phase 4 plan action structs (validated by `validate_plan.py`)
>
> **`update_plan.json` top-level**
> ```
> { "schema_version": "2.0",
>   "deck": <str>, "target_version": <str>, "base_slide_count": <int>,
>   "actions": [...]
> }
> ```
>
> **Common fields on every action:**
> `action_id`, `type` (NOT `action_type`), `finding_ids` (plural array, NOT `finding_id`),
> `source_basis` (non-empty array of `{source_id, rationale?}`), `description`
>
> **Per-type fields:**
> | Type | Key fields | Wrong names (rejected) |
> |------|-----------|----------------------|
> | `update_existing` | `slide_number`, top-level `match_text` / `replacement_text`, or `replacements[]` | `slide`, `edits`, `old_text`, `new_text` |
> | `fragment_replace` | `slide_number`, `find_fragment` / `replace_fragment` | `slide`, `find`, `search`, `replace` |
> | `notes_update` | `slide_number`, `old_speaker_notes`, `notes_changes[]` with `match_fragment` / `replacement_fragment`, `ost_reviewed` | `old`, `new`, `match`, `replacement`, `speaker_notes` |
> | `add_new_slide` | `insert_after_slide` (NOT `slide_number`), `title`, `learning_goal`, `why_this_slide_exists`, `what_customer_should_understand`, `visible_content_summary`, `visual_approach`, `speaker_notes`, `qa_expectations` | `slide_number`; do not rely on fixed renderer routing |
> | `knowledge_check_update` | `slide_number`, top-level `match_text` / `replacement_text`, plus `notes_changes[]` if feedback notes change | `edits`, `speaker_notes` |
> | `remove_or_deprecate` | `slide_number` | — |
>
> **New-slide authoring:** No fixed layout → data-field map exists. Describe the intended visible content and visual approach; the LLM chooses the PowerPoint construction method after studying the deck.
>
> **`ost_reviewed`** (required on every `notes_update`):
> - `"consistent"` + non-empty `ost_review_note`
> - `"companion_action_added"` + a qualifying `update_existing`/`fragment_replace` action on the same slide
>
> #### Part C — Constraint quick-reference
>
> **Banned passive phrases** (any of these in `reason` or `why_no_impact` → gate rejection):
> `"no stale terms"`, `"content is still valid"`, `"scan is clean"`, `"no findings"`,
> `"content looks correct"`, `"no changes needed"`, `"still accurate"`, `"nothing to update"`,
> `"all clear"`, `"no issues found"`
>
> **Banned speaker-notes openers** (first sentence of any speaker note must not start with):
> `"on this slide"`, `"on the previous slide"`, `"this slide"`, `"these slides"`,
> `"to recap"`, `"this is the knowledge check"`, `"here we see"`, `"here we have"`,
> `"in this section"`
>
> **`quoted_source` rules:**
> Literal substring, case-insensitive, ≥30 characters. Must exist verbatim in at least one
> `reference_extract.json` entry. Copy the passage from `reference_extract.json` — do not paraphrase.
>
> **Self-check before running gates** (do all 8 before invoking `audit_gate.py` or `validate_plan.py`):
> 1. Every slide in `deck_extract.json` has a row in `verification_report.json`
> 2. `slides_examined` == all slide numbers [1..N]
> 3. Every cleared slide has `generational_analysis` with min char counts (10/20/30)
> 4. No banned passive phrases in any `reason` or `why_no_impact`
> 5. Every `quoted_source` is ≥30 chars and is a literal substring of `reference_extract` corpus
> 6. Every action has `source_basis` (non-empty array)
> 7. Every `notes_update` has `ost_reviewed`
> 8. Every `add_new_slide` action has visible content summary, visual approach, QA expectations, and speaker notes; no fixed renderer field is required

---

**Two audit axes — both are mandatory:**

- **Axis A — Topic deltas**: what is new/changed in the target release for the deck's stated theme (e.g. "Memory Solutions" -> DDR5MC, CXL, HBM updates). This axis is driven by the source inventory you built in Phase 2.
- **Axis B — Staleness deltas**: tokens that are stale in the target release. Driven by the per-deck `stale_terms.json` you authored from sources during Phase 2 (schema: `references/stale_terms_schema.md`).

A slide cannot be "cleared" until it has been examined against both axes. Auditing only on Axis A is the most common failure mode (it produces a topic-pretty audit that misses generation drift on PS, clocking, security, and packaging slides). Do not do it.

#### Active Reasoning Chain (mandatory before clearing any slide)

You are auditing this deck because it is **probably wrong** — the target generation has changed, and slides that were correct for the previous generation may now be incomplete, misleading, or stale. Your default stance is that every slide needs updating until you can prove otherwise with source-backed reasoning.

Before clearing ANY slide, you must complete all four steps of this reasoning chain. Skipping steps or substituting mechanical scan results for reasoning is a Rule 39 violation.

**Step 1 — Identify content generation.** What generation does this slide's content belong to? Look at the specific products, IP versions, protocol revisions, and feature sets described. A slide about "CPM5 PCIe Gen 5 controller" is Gen 1 content. A slide about "DDR5 register map" may be generation-agnostic — but you must determine that, not assume it.

**Step 2 — Enumerate target-generation changes from sources.** What changed between the content generation and the target generation that could affect this slide? Consult your source inventory — not just the sources that obviously match this slide's topic, but sources for adjacent domains. Changes frequently cross domain boundaries:

- A new controller variant (e.g. CPM5 → CPM6) affects comparison tables, block diagrams, feature matrices, and line-rate figures on slides that never mention the controller by name.
- A protocol revision (e.g. PCIe Gen 5 → Gen 6) affects bandwidth calculations, lane configuration slides, and topology diagrams.
- A new IP block (e.g. CXL 3.1 support) may require updates to memory hierarchy slides, coherence model slides, and system-level architecture diagrams.
- A packaging change (e.g. new die configuration) affects thermal slides, power delivery slides, and board layout guidance.

Cite `source_ids` for every change you identify. If you cannot cite a source, you have not completed this step.

**Step 3 — Trace impact to this slide.** For each change identified in Step 2, explicitly state whether it affects this slide and why. "This slide covers DDR5 register layout, not PCIe — the CPM6 change does not affect register addresses per SRC-NABU-03 section 4.2" is valid. "No stale terms found" is not — it only tells you the mechanical scan didn't flag anything, not that the slide is correct.

**Step 4 — Document in `generational_analysis`.** Record your reasoning in the `generational_analysis` object on the `slides_explicitly_cleared` entry:
- `content_generation` — what you found in Step 1
- `target_generation_changes` — what you found in Step 2 (with source_ids)
- `why_no_impact` — your Step 3 conclusion, specific to this slide

**Examples of valid vs. invalid clearing:**

| Slide content | Clearing reason | Valid? |
|---|---|---|
| DDR5 register map | "Register layout unchanged in Gen 2 per SRC-NABU-03 §4.2. Gen 2 DDR changes (expanded ECC modes) addressed on slide 14." | Yes — source-backed, slide-specific |
| PCIe lane configuration | "No stale terms found on this slide." | **No** — mechanical result, not reasoning |
| System block diagram | "Content is still valid." | **No** — passive phrase, no analysis |
| Clocking architecture | "Gen 2 moves from DPLL to LCPLL (SRC-CONF-02). This slide shows DPLL-based clocking tree — finding needed, not clear." | Yes — correctly identified as NOT clearable |

**Mandatory mechanical step — Stale-term scan (script-driven, not prose-driven):**

```bash
python3 <skill_dir>/scripts/stale_term_scan.py \
  --deck-extract <work_dir>/deck_extract.json \
  --stale-terms <work_dir>/stale_terms.json \
  --output-json <work_dir>/stale_term_scan.json \
  --output-md <work_dir>/stale_term_scan.md
```

This runs a literal, case-insensitive, word-boundary substring scan of every token in `stale_terms.json` against every shape and every speaker-notes block in `deck_extract.json` (group-nested shapes included). Hits inside `skip_if_preceded_by` / `skip_if_followed_by` context windows are skipped; hits on slides listed in `intentionally_kept.on_slides` for that token are also dropped. Every surviving hit becomes a candidate finding for Axis B. Resolution for each hit is one of: (a) update via a plan action, (b) add the slide to `intentionally_kept` for that token with a slide-specific justification, or (c) explicitly clear the slide in `cross_validation_report.json` with a reason that mentions the token or location.

**Mandatory mechanical step — Stale-hit reconciliation:**

After `stale_term_scan.json` is written and before the Phase 3 checkpoint, reconcile every surviving hit:

1. Load `stale_term_scan.json`.
2. For each hit, confirm one of:
   - `verification_report.json` has a finding on the same slide that names the hit token or its exact shape text/location.
   - `update_plan.json` has an action tied to that finding.
   - `stale_terms.json` has an `intentionally_kept` entry for that token and slide.
   - `cross_validation_report.json` explicitly clears the slide with a reason naming the token or location and citing `source_ids`.
3. Record total stale hits and reconciled stale hits in the Phase 3 checkpoint.

Do not rely on a generic `slides_explicitly_cleared` row for any slide with a surviving stale-term hit. A clear such as "slide checked against target deltas" is not sufficient unless it names the hit token or location and explains why that hit is intentionally retained.

**Mandatory mechanical step — Scope-consistency scan:**

```bash
python3 <skill_dir>/scripts/scope_consistency_scan.py \
  --deck-extract <work_dir>/deck_extract.json \
  --stale-terms <work_dir>/stale_terms.json \
  --output <work_dir>/scope_consistency.json
```

This flags slides that combine a portfolio-scope phrase (from `stale_terms.portfolio_scope_phrases`) with a stale-token specific from `stale_terms.stale_terms[].token`. Every signal must be dispositioned by the LLM: confirmed as a finding, addressed by a plan action, explicitly cleared with source-backed rationale, or marked intentionally out of scope.

**Mandatory mechanical step — Intra-slide consistency scan (Rule 35):**

```bash
python3 <skill_dir>/scripts/consistency_scan.py \
  --deck-extract <work_dir>/deck_extract.json \
  --output <work_dir>/consistency_scan.json
```

This detects near-miss technical-token variants *within a single slide* — the class of bug that mechanical stale-term scanning and topic-pretty per-slide audits both miss. The canonical example shipped in a real run: a callout said `A78AE`, a diagram label said `A78E`, and the notes said `A78AE`. The stale-term scan did not fire (`A78E` ≠ `A78AE` and neither is a generation-delta token), and the slide was batch-cleared as "already the target generation", so the one-letter label typo shipped.

The scan flags two distinct tokens on the same slide only when they differ by an **internal letter edit** (insert/delete/substitute) within a 2-character distance. Tokens that differ only by digits (e.g. `CPM5` vs `CPM6`, `DDR4` vs `DDR5`, `A72` vs `A78`) are legitimate generation siblings and are **not** flagged; prefix/suffix variants (e.g. `LPDDR5` vs `DDR5`) are not flagged either. A small curated list of common misspellings is emitted as `advisory: true` signals.

Every non-advisory violation must be reconciled before the pre-plan gate passes: confirmed as a verification finding, addressed by a plan action, or explicitly cleared in `cross_validation_report.json` with a reason that names one of the implicated tokens (e.g. "`A78E` is an intentional shorthand for `A78AE` on this slide"). `audit_gate.py` rejects any unreconciled violation. Advisory typo signals surface as warnings.

All three scans are run automatically by `storyboard_update.py --mode audit-plan`; you do not need to invoke them manually unless you are running the workflow in pieces.

**Mandatory LLM step — Proofreading & consistency pass (Rule 35):**

The scans above are deterministic backstops; they only catch near-miss letter typos and known misspellings. They cannot catch a *semantic* inconsistency ("the diagram shows 3 cores but the bullet says quad-core"), a contradiction across slides ("slide 8 says 64 GT/s, slide 23's knowledge-check answer still says 32 GT/s"), awkward grammar, or a wrong-but-correctly-spelled term. That is the LLM's job, and it must be an explicit, named deliverable — not an implicit hope folded into the per-slide audit (which is exactly what got skipped when the `A78AE`/`A78E` typo shipped).

After the per-slide audit and the mechanical scans, author **`proofread_review.json`** (schema: `references/artifact_schemas.md`). In this pass you:

1. **Disposition every non-advisory `consistency_scan.json` signal.** For each, record `confirmed_finding` (it is a real typo/mismatch — also raise a finding/action/clear), or `rejected_lint` / `intentionally_kept` / `out_of_scope` with a note (a legitimate scanner false positive, e.g. two genuinely distinct SKUs). This is the sanctioned way to dismiss a false positive — do not fabricate a clear to silence the scan.
2. **Read every slide deck-wide for the issues the script cannot find:** spelling (beyond the curated list), grammar and clarity in OST and notes, intra-slide term consistency (diagram labels vs bullets vs notes), and cross-slide consistency (specs, figures, knowledge-check answers, terminology, capitalization). List each as an `issues[]` entry with `severity: "fix"` or `"advisory"`.
3. Every `severity: "fix"` issue must be turned into a finding/plan action/clear; `audit_gate.py` warns at pre-plan and hard-fails at pre-execute if a `fix` issue is left unaddressed.

`audit_gate.py` requires `proofread_review.json` to exist and to cover every slide at both stages. Treat it as the intelligent half of Rule 35; the deterministic scan is the floor that guarantees the obvious near-miss can never silently ship even if this pass is shallow.

> **TRAP — A clean scan is not a pass signal.**
> 0–3 stale-term hits means the mechanical scan found few keyword matches.
> It does NOT mean the deck is current. It often means the scope in `stale_terms.json`
> is too narrow, or that the most important gaps are structural (missing slides for a variant)
> rather than terminological. When stale-term hits are low:
> - Re-examine `stale_terms.json` — does it cover all product variants in the deck?
> - Use `build_parity_matrix.py` as optional advisory lint if product variants are central to the deck.
> - Complete concept decomposition regardless of hit count.
>
> Proceeding to plan authoring without concept decomposition and source-backed coverage review after a
> clean scan is the most common cause of missed structural gaps. `audit_gate.py` will
> refuse to advance until `concept_decomposition.json` is present in the work directory.

**Per-slide protocol:**

1. Open `deck_extract.json` and enumerate every shape for the current slide — titles, body bullets, diagram labels, table cells, callout text, footer text.
2. **Axis A check** — Check each shape's text against the topic sources collected in Phase 2. Flag anything that: uses outdated specs, names a feature/series that has changed or been renamed, omits a variant or generation that sources show is relevant, contradicts content on another slide, or uses terminology inconsistent with AMD's current naming conventions. **After checking each shape against sources, also compare it against every other shape on the same slide** — a subtitle, callout, or body bullet that names a different generation/processor/interface than the diagram labels on the same slide is an intra-slide contradiction and must be flagged regardless of whether any external source was consulted. Confirming that diagram labels are correct is not sufficient; the non-diagram text shapes must be explicitly verified to match them.
3. **Axis B check** — Check each shape's text against `stale_terms.json`. Flag every hit that is not covered by a `skip_if_*` guard and not on an `intentionally_kept` slide.
4. Check the speaker notes separately against the slide's shape content under both axes.
5. Log all findings for that slide before moving on. Each finding must include the shape ID (e.g., `Shape 20`) or the exact shape text it refers to — not just the slide number — and must tag which axis it came from (`axis: "A_topic"` or `axis: "B_platform"`).

> **Write in batches of 5–10 slides:**
> After auditing a batch of 5–10 slides, write all their verification rows to a single
> batch file: `<work_dir>/slide_rows/batch_NN.json` (zero-padded: `batch_01.json`,
> `batch_02.json`). Each batch file is a JSON array of slide row objects:
> ```json
> [
>   {"slide_number": 3, "status": "cleared", ...},
>   {"slide_number": 4, "status": "finding", ...},
>   ...
> ]
> ```
> Do not accumulate more than 10 slides before writing — this ensures compaction cannot
> cause excessive work loss while avoiding the per-slide context-break overhead of 42
> separate file writes. For a typical 42-slide deck this produces ~5 batch files instead
> of 42 sidecars.
>
> Legacy per-slide sidecars (`sNN_verification.json`) are still supported by
> `merge_slide_rows.py` for backward compatibility, but new audits should use batch files.
>
> After all slides are audited, run `merge_slide_rows.py` to assemble
> `verification_report.json`, then proceed to concept decomposition:
> ```bash
> python3 "$SKILL/scripts/merge_slide_rows.py" --work-dir "$WORK"
> ```
> After compaction during Phase 3: run `storyboard_update.py --deck "$DECK" --mode status`
> to see how many slides are done, then resume from the next unaudited slide.

6. **Delta-tracing sweep (mandatory — after per-slide audit, before concept decomposition)**

   For every source delta that identifies a changed specification (e.g. OCM 256 KB → 2 MB, line rate 32 GT/s → 64 GT/s, A72 → A78AE, CCIX → CXL), grep `deck_extract.json` for the OLD value across ALL slides. This catches cross-slide inconsistencies that per-slide auditing misses because the auditor focused on each slide's primary topic.

   Procedure:
   - From `source_inventory.json` and `reference_extract.json`, extract every old→new value pair (spec changes, renamed protocols, updated processor names, changed capacities).
   - For each old value, search all shapes in `deck_extract.json` (case-insensitive, word-boundary). Record every hit as a candidate finding with `type: "delta_trace_hit"`.
   - Cross-reference hits against existing findings from the per-slide audit. Any hit not already covered by a finding or plan action is a NEW finding that must be added to `verification_report.json`.
   - Common examples: a slide that teaches the Gen 2 value (slide 8: "OCM 2 MB") while another slide still shows the Gen 1 value (slide 4: "256 KB"). The per-slide audit may clear slide 4 because its primary topic is the SoC overview, but the delta-tracing sweep catches the stale "256 KB" across the entire deck.

   This step is enforced by Rule 41. Skip it only if zero source deltas identify changed specifications (rare — document why).

7. **Concept decomposition (mandatory — after delta-tracing sweep, before parity matrix)**

   For each source delta in `source_inventory.json`, decompose into teachable concepts per Rule 31. Author a standalone **`concept_decomposition.json`** in the work directory (schema: `references/artifact_schemas.md` — do not embed this array in `verification_report.json`).

   ```json
   {
     "schema_version": "1.0",
     "deck": "<deck filename>",
     "source_deltas": [
       {
         "delta_id": "D1",
         "description": "CPM6 added to Versal Premium Gen 2",
         "source_ids": ["SRC-WEB-02"],
         "teachable_concepts": [
           {
             "concept": "CPM6 controller architecture",
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

   Feed the decomposition into LLM-authored concept coverage decisions. A concept marked `adequate: false` with `recommended_action: add_new_slide` is a strong candidate for a `new_slide_candidate` finding, but the LLM must still decide whether a new slide, existing-slide update, or explicit out-of-scope rationale is correct.

8. **Structural parity check** — After completing the per-slide audit, identify every parallel concept group in the deck (variants of the same category taught at different depths). For each group, compare the depth of coverage across variants. Build a parity matrix. Examples across different deck types:

   *PCIe deck — controller variants:*

   | Variant | Dedicated slides | Architecture diagram | Feature detail | Knowledge check | Notes depth |
   |---------|-----------------|---------------------|---------------|----------------|-------------|
   | CPM4    | 15, 16          | Yes (slide 15)      | Yes (slide 16)| N/A            | ~150 words  |
   | CPM5    | 17              | Yes (slide 17)      | Inline        | slide 18       | ~120 words  |
   | CPM6    | None            | No                  | Table row only| None           | ~30 words   |

   *Memory deck — memory technologies:*

   | Variant     | Dedicated slides | Architecture diagram | Feature detail | Knowledge check | Notes depth |
   |-------------|-----------------|---------------------|---------------|----------------|-------------|
   | DDR4        | 8, 9            | Yes                 | Yes           | slide 10       | ~140 words  |
   | DDR5        | 11, 12, 13      | Yes                 | Yes           | slide 14       | ~180 words  |
   | LPDDR5X     | None            | No                  | Table row only| None           | ~20 words   |

   *Processing System deck — processor clusters:*

   | Variant | Dedicated slides | Architecture diagram | Feature detail | Knowledge check | Notes depth |
   |---------|-----------------|---------------------|---------------|----------------|-------------|
   | APU     | 6, 7, 8         | Yes                 | Yes           | slide 9        | ~200 words  |
   | RPU     | 10, 11          | Yes                 | Yes           | slide 12       | ~150 words  |
   | PMC     | None            | No                  | Bullet only   | None           | ~40 words   |

   Any variant with fewer dedicated slides or missing structural elements (diagram, features, assessment) compared to its peers is a parity signal requiring LLM disposition. The LLM may confirm a `new_slide_candidate` finding, choose a smaller existing-slide update, or document an intentional exclusion (e.g., "variant is under NDA", "variant is out of this deck's stated scope per objectives slide"). Absence of justification is a plan-quality problem, not a script-authored semantic conclusion.

**Bias-break rule:** Do not assume a slide is unchanged because its title is off-theme. PS, clocking, security, packaging, and summary slides change across generations even in topic-specific decks. The most common audit miss is leaving a Processing System slide at Gen 1 values inside a Memory or PCIe deck.

**Audit categories (all apply to every shape, not just the title):**

- **Factual accuracy**: Every technical claim in every shape against source material.
- **Internal consistency**: Same spec or concept stated differently across slides.
- **Completeness**: Features, series, or variants visible in sources but absent from the slide.
- **Currency**: Content accurate for the previous version that has changed in the target version.
- **Grammar, clarity, terminology**: Errors, unclear phrasing, inconsistent capitalization or naming in any shape.
- **Instructional flow**: Slides that reference concepts not yet introduced, or that could be reordered.
- **Structural depth**: Parallel variants taught at comparable depth — no variant has dedicated slides while a peer has only table mentions.
- **Summary coherence**: Summary/recap slides reflect the full deck scope including all planned new content.

Produce a `cross_validation_report` with findings organized by slide number. Each finding must include the shape ID or shape text it refers to, the audit axis (`A_topic` or `B_platform`), and a citation to either the source inventory entry or the `stale_terms.json` entry ID (`ST-NN`) that triggered it. Save to `.storyboard_update/cross_validation_report.json`.

**Mandatory slide-coverage output (gate):**

The report's top-level object must include **all three** of these arrays, and together they must cover every slide in the deck exactly once:

```json
{
  "deck_slide_count": 42,
  "slides_examined":          [1, 2, 3, ..., 42],
  "slides_with_findings":     [1, 8, 14, 17, 23, 38],
  "slides_explicitly_cleared":[
    {"slide": 2,  "reason": "Title slide — version updated under finding for slide 1."},
    {"slide": 3,  "reason": "Objectives slide — already covers new content via finding 14."},
    ...
  ],
  "axes_checked_per_slide": "both A_topic and B_platform"
}
```

Validation rules — the plan is rejected and the audit must be re-run if **any** of these fail:

- `len(slides_examined) == deck_slide_count`
- `set(slides_with_findings) | set(s.slide for s in slides_explicitly_cleared) == set(slides_examined)`
- Every entry in `slides_explicitly_cleared` has a non-empty `reason`
- Every Axis B stale-term hit from the mechanical scan appears in either `slides_with_findings` or `slides_explicitly_cleared` (with a reason explaining why the hit is OK)

**Gate**: A report that clears every slide with no findings is a red flag — present it to the user for confirmation, because it almost certainly means the audit was superficial. Also flag the inverse: an audit that produces findings only on slides whose title matches the deck theme is a red flag for missing Axis B.

**Pre-plan mechanical gate — `audit_gate.py`:**

```bash
python3 <skill_dir>/scripts/audit_gate.py --work-dir <work_dir> --stage pre-plan [--require-sources]
```

Replaces the prose Validation Rules above with an executable audit-artifact gate before `update_plan.json` exists. It asserts:

- All required audit artifacts exist: `deck_extract.json`, `source_inventory.json`, `reference_extract.json`, `verification_report.json`, `cross_validation_report.json`, `stale_terms.json`, `stale_term_scan.json`, `scope_consistency.json`, `consistency_scan.json`, `proofread_review.json`, and `concept_decomposition.json`.
- `slides_examined == [1..N]`.
- `slides_with_findings | slides_explicitly_cleared == [1..N]`.
- Every `slides_explicitly_cleared` entry has a non-empty reason.
- Every stale-term hit is represented by a finding, an `intentionally_kept` entry, or cleared with a reason that mentions the token or location.
- Every scope-consistency finding is represented by a verification finding or explicitly cleared.
- **Intra-slide term consistency (Rule 35):** Every non-advisory violation in `consistency_scan.json` (mechanically detected near-miss token variant such as `A78AE`≠`A78E`) must be represented by a verification finding, addressed by a plan action, explicitly cleared with a reason that names one of the implicated tokens, or dismissed via a documented `proofread_review.json` disposition. Unreconciled violations are a hard failure. Any `intra_slide_inconsistency` finding the LLM authors directly is held to the same rule.
- **Proofreading pass (Rule 35):** `proofread_review.json` must exist, list every slide in `slides_reviewed`, and disposition every non-advisory `consistency_scan.json` signal. Each `issues[]` entry marked `severity: "fix"` must map to a finding/action/clear (warning at pre-plan, hard error at pre-execute).
- With `--require-sources`: source entries must be documented with source IDs; fixed channel counts are not enforced.

Exit code 1 or 2 means the audit is rejected. **Do not present the Phase 3 checkpoint until the pre-plan gate exits 0.**

### MANDATORY USER CHECKPOINT — Phase 3 → Phase 4 Transition

**Before writing `update_plan.json`, present the following to the user and wait for acknowledgement:**

Write `$WORK/audit_summary.md` using `references/audit_summary_guide.md`, then present:

1. **Stale terms authored**: count and list of stale terms from `stale_terms.json` — if fewer than 3 on a 15+ slide deck, explain why scope is intentionally narrow.
2. **Concept decomposition summary**: number of source deltas, number of teachable concepts, and which are marked `adequate: false`.
3. **Parity review results**: which product variants or peer concepts have comparable coverage, and how any advisory parity lint signals were dispositioned.
4. **Total findings count**: number of findings from `verification_report.json`, broken down by type (stale_token, content_gap, new_slide_candidate, etc.).
5. **Proofreading results**: from `proofread_review.json` — how many `consistency_scan.json` signals were confirmed vs dismissed as false positives, and the count of `fix` vs `advisory` proofreading issues (spelling, grammar, intra/cross-slide consistency).
6. **Proposed plan scope**: 1-2 sentence summary of what the plan will contain.

**Do NOT proceed to Phase 4 until the user explicitly acknowledges.** This checkpoint exists because the most common failure mode is a shallow audit that clears all slides with mechanical-only reasoning and produces a 1-action plan on a 30+ slide deck. The user is the last line of defense before plan authoring begins.

### Phase 4.5 — Plan validation and pre-execute gate

After writing `update_plan.json`, run:

```bash
python3 "$SKILL/scripts/validate_plan.py" \
  --plan "$WORK/update_plan.json" \
  --story-model "$WORK/story_model.json"

python3 "$SKILL/scripts/audit_gate.py" \
  --work-dir "$WORK" \
  --stage pre-execute \
  --require-sources
```

The pre-execute gate includes all pre-plan checks plus plan action mapping, source-basis checks, notes-structure checks, notes/OST coherence, `original_notes.json` matching for `notes_update`, stale-hit reconciliation against actions, new-slide schema checks, and advisory scope-depth diagnostics.

### Phase 5 — XML/package-only final validation

After Phase 5A applies existing-slide edits, Phase 5A.1 runs `post_apply_check.py`, and Phase 5C merges the final output, `validate_deck.py --require-fresh-merge is the final validation path`. Never open the final merged `.pptx` in PowerPoint, LibreOffice, COM automation, browser UI, or any presentation viewer for validation because the produced deck may require PowerPoint repair.

Final validation must inspect the `.pptx` as a ZIP/OOXML package: run `validate_deck.py`, review `validation.json`, and inspect package parts when needed (`ppt/slides/*.xml`, `ppt/notesSlides/*.xml`, `ppt/_rels/*.rels`, `[Content_Types].xml`, presentation order, merge status sidecars). Check text presence, notes presence, shape geometry values, relationships, stale tokens, highlight placement, authoring markers, slide order, and package structure through XML/package inspection only.

> **Before writing `update_plan.json` (Phase 4):** Review the **Part B action structs** in the
> Phase 3 pre-flight checklist above. If spawning a subagent, paste the Part B struct definitions
> and the Part C constraint quick-reference into the agent prompt — subagents do not inherit your
> context and will invent wrong field names without it.
>
> **OST review is mandatory on every `notes_update` action.** For each `notes_update`, set `ost_reviewed` to `"consistent"` (with a non-empty `ost_review_note`) or `"companion_action_added"` (with a qualifying `update_existing` or `fragment_replace` action on the same slide also present in the plan). `validate_plan.py` rejects the plan if any `notes_update` is missing this field or the companion is absent. If the Phase 3 finding that prompted the notes update had `recommended_action_type` pointing to an OST edit, set `"companion_action_added"` — not `"consistent"`. See Rule 38.
>
> **Image-detection check before marking `ost_reviewed: "consistent"` (Rule 42).** Before writing `"consistent"`, count the meaningful text shapes on the slide in `deck_extract.json` (exclude title, authoring markers like "Fully Shared Slide", and slide-number labels like "Slide-24"). If the speaker notes describe a table, feature matrix, or multi-row comparison but the slide has fewer than 4 meaningful text shapes, the visible content is likely an embedded image. In this case, `ost_review_note` must: (a) acknowledge the image limitation explicitly, (b) list which concepts from the notes update cannot be verified against OST, and (c) include `manual_review_required` specifying what the image should be checked for. A generic note like "OST is consistent" on a slide with 0 meaningful text shapes is a Rule 42 violation.

---

## Advisory Source-Gap Lint (Phase 2.5)

The Phase 2 source set is the *starting* corpus, not the final one. `detect_source_gaps.py` can identify claim-token lint signals that may need more research, but it cannot decide whether a source supports a claim. The LLM-authored audit must judge entailment.

### Run after Phase 2, before Phase 3

```bash
python3 <skill_dir>/scripts/detect_source_gaps.py \
  --deck-extract <work_dir>/deck_extract.json \
  --reference-extract <work_dir>/reference_extract.json \
  --output <work_dir>/coverage_gaps.json
```

`coverage_gaps.json` lists advisory claim-token lint signals (rate values, IP names, feature names, channel counts, protocol versions, recommendations) that have no matching token in `reference_extract.json`, along with suggested source candidates.

### Source follow-up loop

For each entry in `coverage_gaps.json`:

1. **Identify the authoritative source** — AMD PG (product guide) number, AMD docs.amd.com page, AMD product brief, PCIe/CXL/JEDEC/Arm spec document, internal Confluence page, JIRA issue, or Nabu corpus.
2. **Fetch and ingest** — extend `reference_extract.json` with the new source chunk(s), each entry tagged with `source_id`, `section`, `claim_keys: [...]`, and `claim_supported: [...]`.
3. **LLM-disposition the signal** as supported, contradicted, insufficiently sourced, irrelevant mention, or intentionally out of scope.
4. **Escalate unresolved evidence** to the user when an authoritative source cannot be found after a targeted search.
5. **Cap at 1 follow-up round per slide.** After one round, batch-escalate remaining unresolved signals with slide number, claim token, queries tried, and why no source was found.

### Three-state clear semantics

`audit_gate.py` enforces three terminal states per slide:

| State | Conditions | Promoted to plan? |
|---|---|---|
| `cleared_with_source` | LLM verifies the slide's claims against cited source text and no source contradicts the claim cluster | Yes — listed in `slides_explicitly_cleared` with `source_ids: [...]` |
| `cleared_no_source` | One or more important claim clusters still lack authoritative support after targeted gathering | **No — must escalate to user; cannot auto-clear** |
| `findings` | Source contradicts at least one claim, or new tech in module scope invalidates an existing answer/recap | Listed in `slides_with_findings` with at least one action in the plan |

### Schema additions

- `reference_extract.json`: each entry must include `claim_keys: [...]` so claims can be reverse-looked-up by the gap detector.
- `cross_validation_report.json`: every `slides_explicitly_cleared` entry must include a non-empty `source_ids: [...]` array. An empty array fails `audit_gate.py`.
- `update_plan.json`: every action must include a `source_basis` field (URL or `source_id` + section/page). `audit_gate.py` rejects actions missing this field.

### Why this matters

In the PCIe-deck 2026.1 update, slides 23-37 covered QDMA/XDMA internals, MDB5 channel counts, AXI bridge master/slave behavior, line-rate enumerations, MSI-X vector counts, and SR-IOV details. None of those topics had an entry in `reference_extract.json` because Phase 2 only fetched CPM6/CXL/PCIe-Gen-6 sources. The audit cleared every one of those slides on the basis that stale-term hits were substrings of correctly-scoped Gen-2 phrases. The audit was wrong: slide 23's knowledge-check correct answer ("2.5 - 32 GT/s") is invalidated because PCIe Gen 6 added 64 GT/s to the module's scope. A recursive gather of PG346/PG347/PCIe 6.1 spec would have surfaced this immediately.

Structural completeness failures follow the same pattern across deck types. In a PCIe deck, older controller variants had dedicated architecture slides while the newest variant appeared only as a table row — the table content was factually correct, but the deck failed to teach the new variant at comparable depth. In a memory deck, the same pattern can occur when DDR5 gets multiple deep-dive slides but LPDDR5X gets only a bullet point. In a processing system deck, APU and RPU might each get architecture walkthroughs while PMC gets a passing mention. A parallel-section parity check would immediately flag any such imbalance. This is a structural completeness failure, not a factual accuracy failure — the mentions may be correct, but the deck doesn't teach the topic. Similarly, summary slides must be re-validated after any new content is planned: a summary that was complete before new slides were added becomes stale after them. Every new capability introduced by an `add_new_slide` action (new protocol, new bandwidth tier, new IP block, new processor mode) must trigger a dependent summary update.
