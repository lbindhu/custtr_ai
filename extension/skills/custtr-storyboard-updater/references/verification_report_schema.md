# `verification_report.json` Schema (Legacy)

`references/artifact_schemas.md` is the canonical schema reference for new runs.
This file is retained only for older audits that still reference the legacy
verification-report taxonomy. Do not use it when authoring new artifacts.

`verification_report.json` is the source-backed audit contract for this skill.
It replaces legacy token-list scanning. Every slide must have one row, and every row
must validate both on-slide text (OST) and speaker notes against
`reference_extract.json`.

The file may be either:

```json
{"slides": [ ... rows ... ]}
```

or a bare array of rows.

## Slide Row

```json
{
  "slide_number": 18,
  "slide_role": "deep_dive",
  "claims_verified": [
    {
      "claim": "CPM6 supports PCIe Gen 6 at 64 GT/s.",
      "location": "OST",
      "quoted_source": "literal source text of at least thirty characters...",
      "source_id": "SRC-NABU-04",
      "audit_basis": "slide+notes+corpus"
    }
  ],
  "findings": [
    {
      "id": "S18-F01",
      "type": "contradicted_claim",
      "location": "OST",
      "current_text": "PCIe Gen 5 at 32 GT/s",
      "proposed_text": "PCIe Gen 6 at 64 GT/s",
      "quoted_source": "literal source text of at least thirty characters...",
      "source_id": "SRC-NABU-04",
      "ost_parity": "both",
      "recommended_action_type": "update_existing",
      "action_required": true,
      "audit_basis": "slide+notes+corpus"
    }
  ],
  "knowledge_check_review": null,
  "summary_review": null,
  "open_questions": [],
  "recursive_gather_round": 0,
  "additional_sources_needed": []
}
```

## Finding Types

Allowed `type` values:

- `outdated_label`
- `contradicted_claim`
- `missing_fact`
- `ost_notes_mismatch`
- `knowledge_check_invalid`
- `summary_gap`
- `new_slide_candidate`
- `remove_or_deprecate`

Allowed `recommended_action_type` values:

- `update_existing`
- `notes_update`
- `knowledge_check_update`
- `add_new_slide`
- `remove_or_deprecate`

## New-Slide Candidate

Use `type: "new_slide_candidate"` sparingly. It is not permission to add a
slide by itself; it is evidence that the plan may add one after approval.

Each candidate must include:

```json
{
  "id": "S18-F03",
  "type": "new_slide_candidate",
  "concept": "CXL Type-3 memory expansion",
  "why_existing_slide_update_is_insufficient": "The current memory options slide is already dense and does not explain protocol roles or customer use cases.",
  "insert_after_slide": 18,
  "learning_goal": "Explain how CXL Type-3 extends the memory story and when customers should consider it.",
  "flow_dependencies": {
    "connects_from": "CPM6 overview",
    "connects_to": "memory hierarchy and customer use cases",
    "objectives_affected": [2],
    "knowledge_checks_affected": [23],
    "summary_slides_affected": [38]
  },
  "visual_intent": "Show host, CPM6/CXL path, Type-3 memory device, and coherency/memory expansion relationship.",
  "qa_expectations": ["Rendered slide has no text cutoffs or overlaps", "Visual style matches the surrounding section"],
  "quoted_source": "literal source text of at least thirty characters...",
  "source_id": "SRC-NABU-04",
  "recommended_action_type": "add_new_slide",
  "action_required": true
}
```

## Structural Parity Matrix

Every verification report must include a `structural_parity` section when the deck
teaches parallel variants of the same concept category:

```json
{
  "structural_parity": [
    {
      "group": "<category name, e.g. 'PCIe Controllers', 'Memory Technologies', 'Processor Clusters'>",
      "variants": [
        {"name": "Variant A", "dedicated_slides": [15, 16], "has_diagram": true, "has_feature_detail": true, "has_knowledge_check": false, "depth_tier": "full"},
        {"name": "Variant B", "dedicated_slides": [17], "has_diagram": true, "has_feature_detail": true, "has_knowledge_check": true, "depth_tier": "full"},
        {"name": "Variant C", "dedicated_slides": [], "has_diagram": false, "has_feature_detail": false, "has_knowledge_check": false, "depth_tier": "mention_only"}
      ],
      "parity_violation": true,
      "finding_ids": ["S17-F01", "S17-F02", "S17-F03"]
    }
  ]
}
```

The group name and variant names are deck-specific. Examples:
- PCIe deck: group "PCIe Controllers", variants "CPM4", "CPM5", "CPM6", "MDB5"
- Memory deck: group "Memory Technologies", variants "DDR4", "DDR5", "LPDDR5X", "HBM"
- Processing System deck: group "Processor Clusters", variants "APU", "RPU", "PMC"
- Security deck: group "Protection Units", variants "XMPU", "XPPU", "SMMU"

Depth tiers:
- `full` — dedicated slide(s) with architecture diagram or feature detail + speaker notes >=80 words
- `partial` — dedicated slide but missing diagram or detail
- `mention_only` — appears in table row, bullet list, or speaker notes only
- `absent` — not mentioned at all

A `parity_violation: true` is an advisory signal that requires LLM disposition.
The LLM may confirm it as a finding, address it with an existing-slide update,
add a new-slide candidate, or explicitly justify exclusion (e.g., "variant is
under NDA", "variant is out of deck scope per objectives slide").

## Concept Decomposition

> **Deprecated:** Author standalone **`concept_decomposition.json`** in the work directory.
> Do not nest concept decomposition inside `verification_report.json`.
> Schema: `references/artifact_schemas.md` (section `concept_decomposition.json`).
> `audit_gate.py` requires the standalone file before pre-plan advance.

The legacy embedded array below is retained for reference only when reading older work dirs:

```json
{
  "concept_decomposition": [
    {
      "parent_delta": "CPM6 added to Versal Premium Gen 2",
      "source_id": "SRC-WEB-02",
      "concepts": [
        {
          "concept": "CPM6 controller architecture",
          "independently_teachable": true,
          "current_coverage": "absent",
          "adequate": false,
          "finding_id": "NS-01"
        },
        {
          "concept": "CXL 3.1 protocol and device types",
          "independently_teachable": true,
          "current_coverage": "absent",
          "adequate": false,
          "finding_id": "NS-03"
        },
        {
          "concept": "GTM2 transceiver family",
          "independently_teachable": false,
          "current_coverage": "notes mention on slide 8",
          "adequate": true,
          "finding_id": null
        }
      ]
    }
  ]
}
```

**Fields:**
- `parent_delta` — the source delta this decomposition comes from
- `source_id` — which source inventory entry backs this delta
- `concepts[].concept` — the teachable concept extracted
- `concepts[].independently_teachable` — would a learner have a meaningful knowledge gap without this concept? (Rule 31 test)
- `concepts[].current_coverage` — how the deck currently covers it: `dedicated slide`, `table row`, `bullet`, `notes mention`, or `absent`
- `concepts[].adequate` — is current coverage sufficient?
- `concepts[].finding_id` — linked finding ID if `independently_teachable: true` AND `adequate: false`; null otherwise

Every concept with `independently_teachable: true` and `adequate: false` must have a
corresponding `new_slide_candidate` finding in the verification report. This is the
mechanism that prevents treating "CXL 3.1" as merely a CPM6 feature bullet when it is
a protocol that warrants its own teaching surface.

## Clear Evidence

Slides with no findings must still be defensible. Put clear evidence in
`cross_validation_report.json`:

```json
{
  "slides_examined": [1, 2, 3],
  "slides_with_findings": [2],
  "cleared_with_evidence": [
    {
      "slide": 1,
      "source_ids": ["SRC-NABU-01"],
      "reason": "Title slide only; target version confirmed separately."
    }
  ],
  "findings_cleared": [
    {
      "finding_id": "S12-F02",
      "source_ids": ["SRC-PDF-03"],
      "reason": "The source confirms this statement is intentionally scoped to legacy CPM5."
    }
  ],
  "version_exceptions": [
    {
      "slide": 17,
      "token": "2025.2",
      "reason": "Historical release reference in migration note."
    }
  ]
}
```

## Gate Invariants

`scripts/audit_gate.py` enforces:

- every deck slide has a verification row
- every verified claim/finding has `source_id` and a >=30-character literal
  `quoted_source` present in `reference_extract.json`
- no blocking `open_questions`
- no `additional_sources_needed`
- every required finding maps to a plan action through `verification_ids` /
  `finding_ids`, or is cleared in `cross_validation_report.json`
- every mapped action cites the same `source_id`
- every `add_new_slide` action maps to a `new_slide_candidate`
- knowledge-check slides include `knowledge_check_review` or findings
- summary slides include `summary_review` or findings
- non-target version strings require `version_exceptions`
