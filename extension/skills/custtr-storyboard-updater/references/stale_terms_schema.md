# `stale_terms.json` Schema

Per-deck staleness contract. Authored by the LLM during Phase 2 from the
live source inventory and the deck's own content. Consumed by
`stale_term_scan.py`, `scope_consistency_scan.py`, and `post_apply_check.py`.

The `--mode audit-plan` orchestrator scaffolds an empty `stale_terms.json`
from `references/stale_terms.example.json` and exits. The LLM must author
per-deck entries before re-running.

## Top-Level Fields

```json
{
  "schema_version": "1.0",
  "target_release": "2026.1",
  "deck": "sources/17. AMD Versal Adaptive SoC - PCI Express_SB.pptx",
  "portfolio_scope_phrases": ["Versal architecture", "Versal devices"],
  "product_variants": ["CPM5", "CPM6", "MDB"],
  "stale_terms": [ ... ],
  "intentionally_kept": [ ... ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | string | yes | Always `"1.0"` |
| `target_release` | string | yes | Target Vivado/Vitis release (e.g. `"2026.1"`). Used by the version sweep to flag mismatched `YYYY.N` tokens. |
| `deck` | string | yes | Path to the source PPTX being audited. |
| `portfolio_scope_phrases` | string[] | yes | Phrases that indicate portfolio-level scope (e.g. `"Versal Adaptive SoC"`, `"Versal architecture"`). Used by `scope_consistency_scan.py` — a slide using one of these without a `Gen 1`/`Gen 2` qualifier cannot also carry a stale-token specific. |
| `product_variants` | string[] | **yes** | Ordered list of product variant names taught in parallel in this deck (e.g. `["CPM5", "CPM6", "MDB"]`). Used by `build_parity_matrix.py` to detect variants with zero dedicated slides while peers have ≥1. Author this from slide titles and source inventory during Phase 2. Omitting it disables structural parity detection. |
| `stale_terms` | object[] | yes | Array of stale-term entries. Each describes one token that may be stale in the target release. |
| `intentionally_kept` | object[] | yes | Array of exceptions — tokens that legitimately survive on specific slides. |

## `stale_terms[]` Entry

```json
{
  "id": "ST-01",
  "token": "CCIX",
  "skip_if_preceded_by": ["CPM4 ", "CPM5 "],
  "skip_if_followed_by": [],
  "replace_with": "CXL 3.1 (CPM6 context)",
  "source_ids": ["SRC-PDF-01"],
  "rationale": "CPM6 replaces CCIX with CXL 3.1; CPM4/CPM5 mentions stay correct."
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Unique identifier (e.g. `"ST-01"`, `"ST-02"`). |
| `token` | string | yes | The literal text to scan for. Case-insensitive substring match against every shape and speaker-notes block. |
| `skip_if_preceded_by` | string[] | yes | Context guards. If any of these strings appear immediately before the token match, the hit is suppressed. Include trailing spaces where needed (e.g. `"CPM5 "`). |
| `skip_if_followed_by` | string[] | yes | Context guards. If any of these strings appear immediately after the token match, the hit is suppressed. Include leading spaces where needed (e.g. `" Series Gen 2"`). |
| `replace_with` | string | yes | Suggested replacement text. Informational — used by the LLM when authoring plan actions. |
| `source_ids` | string[] | yes | References to `source_inventory.json` entries that justify this staleness judgment. `audit_gate.py` cross-checks that these exist. |
| `rationale` | string | yes | Why this token is stale and how the guards work. Human-readable. |

## `intentionally_kept[]` Entry

```json
{
  "token": "CCIX",
  "on_slides": [17],
  "why": "CPM5 PCIE slide — legacy fact."
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `token` | string | yes | The stale token that is permitted to survive. Must match a `stale_terms[].token`. |
| `on_slides` | int[] | yes | Slide numbers where this token is allowed. Hits on these slides are excluded from scan findings. |
| `why` | string | yes | Slide-specific justification for keeping the token. |

## Authoring Rules

1. **Every entry must trace to at least one source.** `source_ids` references
   entries in `source_inventory.json`. `audit_gate.py` cross-checks.

2. **Use `skip_if_preceded_by` / `skip_if_followed_by` for context-dependent
   staleness.** Example: `CCIX` is correct on a CPM5 slide and stale on a CPM6
   slide — the guard `skip_if_preceded_by: ["CPM5 "]` expresses this. Example:
   `Versal Premium` is stale only when not already qualified as `Series Gen 2`
   — use `skip_if_followed_by: [" Series Gen 2"]`.

3. **Always list previous release versions explicitly.** Add a `2025.2`-style
   entry whenever the deck carries a version marker. The version sweep also
   catches missed cases, but listing it gives the audit a paper trail with
   sources.

4. **Use `intentionally_kept` for tokens that legitimately survive on specific
   slides** (e.g. a legacy CPM5 reference on a CPM5 topology slide). Without
   this list, `post_apply_check.py` will flag every surviving occurrence as a
   regression.

5. **Author `product_variants` from slide titles and sources, not from memory.**
   Scan `deck_extract.json` slide titles for names taught in parallel (controller
   variants, IP families, device generations). Cross-check against source inventory
   to include any variant that sources mention but the deck does not yet cover.
   A missing `product_variants` list silently disables parity detection —
   `build_parity_matrix.py` will emit no candidates and the structural gap will go
   undetected. An empty array `[]` is treated the same as a missing field.

6. **Never copy-paste a `stale_terms.json` from a previous deck run.**
   Re-author from sources; the deltas change per release.

## Consumers

| Script | What it reads | What it does |
|--------|--------------|--------------|
| `stale_term_scan.py` | `stale_terms[]`, `intentionally_kept[]` | Scans every shape and notes block for stale tokens, honoring guards and exceptions. Writes `stale_term_scan.json` + `.md`. |
| `scope_consistency_scan.py` | `portfolio_scope_phrases[]`, `stale_terms[].token` | Flags slides that combine a scope phrase with a stale-token specific. Writes `scope_consistency.json`. |
| `post_apply_check.py` | `stale_terms[]`, `intentionally_kept[]` | Re-scans the updated deck after Phase 5A. Refuses to advance if a promised removal failed or a new stale token was introduced. |
| `audit_gate.py` | `target_release` | Version sweep checks every `YYYY.N` token against `target_release`. |
| `build_parity_matrix.py` | `product_variants[]` | Identifies which variants have dedicated slides, architecture diagrams, and feature detail. Emits `new_slide_candidates` for variants with 0 dedicated slides while peers have ≥1. Writes `parity_matrix.json`. |
