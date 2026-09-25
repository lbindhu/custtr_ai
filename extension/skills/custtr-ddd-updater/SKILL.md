---
name: custtr-ddd-updater
description: Updates AMD Customer Training Detailed Design Documents (DDDs) with new release content. Use this skill when the user wants to update a DDD Word document (.docx) with new release information, version history entries, curriculum module updates, or 2026.1 content. Trigger on: "update the DDD", "add to DDD", "update the design document", "add version history", "update curriculum", or any request to modify a course DDD file. Always reads the provided DDD first to learn its exact template style (version format, bullet style, column structure, content description style) before making any changes. Uses the previous release DDD as the clean base, adds only the new version entry to version history, and adds new bullet points to the correct curriculum module columns — all matching the existing template style so updates are indistinguishable in format from original content.
owner: akanapur
---

# AMD Customer Training DDD Updater

**Owner:** akanapur

This skill updates AMD Customer Training Detailed Design Documents (DDDs) for new releases.

---

## Rules — ALWAYS follow these

1. **Use the previous release DDD as the base** — never start from a partially updated file
2. **Version history** — add ONLY the new version entry (e.g. V2.3, V7) at the end. Never modify existing version rows
3. **Curriculum updates** — add new bullet points ONLY in the **Related Objectives column** (2nd cell) of the correct module row
4. **No UG link dumps** — write meaningful sentences, not "UG1273 2026.1 (Jun 24, 2026):..."
5. **No "2026.1:" prefix** — yellow background highlight is sufficient to identify new content
6. **Yellow highlight only on new content** — existing content stays unchanged
7. **Only 2026.1 content** — do not add content from any other release

---

## Template Format

Each curriculum module row has these columns:

| Column | What goes there |
|---|---|
| Topic Cluster | Module name |
| Related Objectives | PPT bullet points — what's taught on slides and labs |
| Content Description | Short narrative sentence about what students learn |
| Content Source(s) | UG numbers only |
| Duration | Minutes |

**New 2026.1 bullet points go into the Related Objectives column only.**

Write bullets as action statements:
- Good: *"New FP8 data types for AIE-ML v2"*
- Bad: *"2026.1: UG1304 2026.1 (Jun 24, 2026): AI Engine Development..."*

---

## Version History Format

Match the existing style exactly:

```
V2.3 | Jun 2026 | Updated for 2026.1:
• Module name: brief description of what was added
• Module name: brief description of what was added
```

---

## Footer Version Update (MANDATORY)

Every DDD has a footer showing the document version (e.g. `Detailed Design Document v2025.2`).

**Always update ALL footer files** (`word/footer1.xml` through `word/footer9.xml`) — every single one must be checked and updated.

### The version string is split across multiple XML runs — handle all patterns:

The version number is never stored as a single string. It is fragmented across multiple `<w:r>` runs. You must handle ALL of these patterns:

| Pattern | Example XML |
|---|---|
| 2 runs | `v202` + `5.2` |
| 3 runs | `v202` + `5` + `.2` |
| 4 runs | `v202` + `5` + `.` + `2` |
| 5 runs (footer3) | `Document v20` + `2` + `5` + `.` + `2` — **this one is always missed** |
| Compact | `v2025.1` or `v2024.1` as single string |

Use `re.sub()` with `re.DOTALL` to match across runs, OR use direct string replacement for the exact footer3 pattern.

**footer3 exact fix** (copy this verbatim):
```python
footer = footer.replace(
    'Document v20</w:t></w:r><w:r w:rsidR="000752DC"><w:t>2</w:t></w:r><w:r w:rsidR="00A25EC3"><w:t>5</w:t></w:r><w:r w:rsidR="004E380A"><w:t>.</w:t></w:r><w:r w:rsidR="004D4D64"><w:t>2</w:t></w:r>',
    'Document v2026.1</w:t></w:r><w:r w:rsidR="000752DC"><w:t></w:t></w:r>'
)
```

**After updating, ALWAYS verify** all footers show the correct version before saving.

---

## Highlighting

- **New bullet points in curriculum** — yellow background (`w:val="yellow"`)
- **New version history row** — yellow background
- **Footer version update** — no highlight needed (it is a factual version update)
- Existing content — no changes, no highlighting

---

## Step 0 — Read and Learn the DDD Template First (MANDATORY)

Before making ANY changes, always read the provided DDD file and extract:

1. **Version history style** — What format is used? (e.g. V1, V2 or V1.1, V1.2 — date format — bullet style inside version rows)
2. **Table column structure** — How many columns? What are the exact column headers?
3. **Bullet style in curriculum** — What `<w:pStyle>` and `<w:numId>` are used for bullets in Related Objectives cells?
4. **Content Description style** — Is it a full sentence? Short phrase? Does it start with a verb?
5. **Content Source style** — Is it "UG1273" or "UG1273, UG1388" or written differently?
6. **Duration format** — "20 mins" or "20 min" or "20"?
7. **Module naming style** — Does the Topic Cluster include `{Lecture, Lab}` or `{Lecture}` in the cell?

Only after learning these patterns, apply them consistently when inserting new content.

**This ensures the new content is indistinguishable in style from existing content — only the yellow highlight reveals it is new.**

---

## Workflow

1. **Read the base DDD** — extract template style (version format, bullet numId, column structure, content description style)
2. **Read the 2026.1 DDD** (if provided) — understand what version entry exists and what module content was planned
3. **Search AMD TIP** (docs.amd.com) for 2026.1 What's New content relevant to each module in the DDD
4. **Write new bullet points** matching the exact template style — meaningful sentences, no UG references
5. **Insert bullets** into the correct Related Objectives cell of each module row
6. **Add new version row** at end of version history table — matching the exact version numbering and date format
7. **Update the footer** — replace old version string (e.g. `v2025.2`) with new version (e.g. `v2026.1`) in all footer XML files
8. **Verify XML is valid** before saving
9. **Save as updated file**
