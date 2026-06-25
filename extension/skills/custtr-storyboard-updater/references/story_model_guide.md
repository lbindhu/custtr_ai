# LLM Story Model Guide

The story model is an instructional interpretation of `deck_extract.json`.
Python extracts the deck; the LLM explains what the deck is trying to teach.
Do not use this artifact to make source-backed correctness decisions.

## Inputs

- `deck_extract.json`: deterministic slide, shape, and notes extraction.
- `story_model_scaffold.json`: heuristic starter. Revise it freely.
- User-provided context about target release, audience, or module scope.

## Required Output

Write `$WORK/story_model.json` with `schema_version: "2.0"`.

Every slide in `deck_extract.json` must have exactly one row in
`slide_interpretations`. Each row must use evidence that points to real shape
IDs or notes text from the extraction.

## Boundary

Allowed in the story model:

- Teaching purpose and slide role.
- What concepts are introduced, reinforced, or assessed.
- Whether a slide appears generation-specific or release-agnostic.
- What source queries Phase 2 should run.
- Candidate stale terms that need source confirmation later.

Forbidden in the story model:

- Source-backed clears or findings.
- Statements like "SRC-NABU-01 confirms..." or "no changes needed."
- Final decisions about correctness, completeness, or required edits.
- Update-plan actions.

Source-backed audit conclusions belong in Phase 3 artifacts after source
collection, not in `story_model.json`.

## Role Vocabulary

Use one of these roles:

- `title`
- `objectives`
- `concept_setup`
- `architecture_walkthrough`
- `deep_dive`
- `comparison`
- `recommendation`
- `knowledge_check`
- `summary`
- `boilerplate`
- `blank`
- `transition`
- `example`
- `case_study`
- `lab`

If a slide defaults to `deep_dive`, include `role_rationale` explaining why a
more specific role does not fit.

## Minimal Schema

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

## Validation

The v2 `slide_interpretations` rows are authoritative. Compatibility fields
(`slide_roles`, `knowledge_checks`, `summary_slides`, and `concept_coverage`)
must be derived from those rows and kept in sync for downstream scripts.

Run:

```bash
python3 "$SKILL/scripts/validate_story_model.py" \
  --deck-extract "$WORK/deck_extract.json" \
  --story-model "$WORK/story_model.json"
```

Validation errors must be fixed before Phase 1.5, Phase 2, stale-term scans, or
plan authoring continue.
