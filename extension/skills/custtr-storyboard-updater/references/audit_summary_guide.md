# Audit Summary Guide (Phase 3 → 4 Checkpoint)

Before writing `update_plan.json`, author **`$WORK/audit_summary.md`** — a human-readable rollup for the mandatory user checkpoint. JSON artifacts remain the source of truth for gates; this file makes the checkpoint fast to review.

## Template

```markdown
# Audit Summary — <deck name>

**Target version:** <target_release>
**Slides examined:** <N>
**Audit date:** <YYYY-MM-DD>

## Stale-term scope

- **Terms authored:** <count> — <comma-separated list or "see stale_terms.json">
- **Scan hits:** <count> reconciled / <count> total
- **Shallow-count note:** (if applicable) why low hit count is intentional

## Concept decomposition

- **Source deltas:** <count>
- **Teachable concepts:** <count>
- **Inadequate concepts:** <list concept names with adequate: false>

## Parity / structural review

- **Product variants:** <list or N/A>
- **Advisory parity lint:** how signals were dispositioned

## Proofreading & consistency (Rule 35)

- **consistency_scan signals:** <count confirmed> confirmed / <count dismissed> dismissed as false positives
- **Proofreading issues:** <count "fix"> to fix / <count "advisory"> advisory (spelling, grammar, intra/cross-slide consistency)

## Findings rollup

| Type | Count |
|------|------:|
| stale_token | |
| content_gap | |
| new_slide_candidate | |
| other | |

**Total findings:** <N>
**Slides cleared with evidence:** <N>
**Slides with open findings:** <N>

## Proposed plan scope

1–2 sentences describing expected update_plan actions (updates, notes, new slides, removals).

## Unresolved evidence

- (List escalations, missing sources, or user decisions needed — or "None")
```

## Rules

- Do not substitute this file for `verification_report.json`, `cross_validation_report.json`, or `concept_decomposition.json`.
- Include enough specificity that the user can reject a shallow audit without opening every JSON file.
- After the user acknowledges, proceed to Phase 4 plan authoring.
