---
marp: true
theme: amd
paginate: true
---

<!-- _class: title -->

![w:180](C:/Users/Vnelliko/.claude/skills/psas-amd-marp/images/amd-logo-dark.jpg)

# Split Lab Workbook
## Agent Skill Workflow

AMD Customer Training | Lab workbook automation

---

<!-- _class: lead -->

# When to use

---

# When to use this skill

- User has **one combined lab workbook** `.docx` with Lab 1, Lab 2, … Lab N
- User wants **separate files** without reformatting
- Each lab starts on its **own first page** (no cover, TOC, or Lab FAQ)
- First-page heading shows **title only** — no `Lab N:` prefix
- Output naming: **`NN Lab Title.docx`** + matching PDFs

**Trigger phrases:** break workbook, split by lab, cut into separate docx, remove Lab 1 Lab 2 from first page

---

<!-- _class: lead -->

# Hard rules

---

<style scoped>
section h1 { color: #00C2DE; }
</style>

# Do vs Don't

| Do | Don't |
|----|-------|
| Copy full `.docx` zip; trim `document.xml` only | Re-save via Word or `python-docx` |
| Preserve styles, tables, images, `sectPr` | Rewrite or restyle content |
| Split at `Heading1` lab headings | Split on TOC lines alone |
| Name files `01 Title.docx` | Use `- Lab 01 -` prefix in filename |
| Clean final-section headers only | Strip all page headers/footers |

---

<!-- _class: lead -->

# User prompting

---

# Before you run anything

1. **Resolve** source path, output folder, pipeline scope
2. **Inspect** with `--inspect` — show lab count and titles
3. **Confirm** with AskQuestion — user approves or adjusts
4. **Run** `run_split_pipeline.py` only after confirmation

Skip prompts only when the user already supplied all values **and** said to proceed.

---

<!-- _class: lead -->

# Workflow

---

# Nine-step workflow

```
1. Confirm source is a combined lab workbook
2. Find split points (Heading1 + lab number)
3. Define ranges — lab heading to next lab heading
4. Copy docx; trim document.xml body children
5. Clean first Heading1 (remove Lab N + field codes)
6. Save as NN Title.docx and validate
7. Remove AMD images from last-page header/footer
8. Export PDF; trim trailing blank pages (1–3)
9. Set PDF metadata (Title, Author, Subject)
```

Run: `python scripts/run_split_pipeline.py workbook.docx`

---

<!-- _class: cols -->

# Step 1–2: Inspect & locate

<div>

## Inspect source
- Unzip `.docx`; read `word/document.xml`
- Front matter **before Lab 1** = cover, Lab FAQ, TOC
- **Exclude** front matter from all outputs

## Find split points
- Style: `Heading1`
- Match: `Lab N:` or SEQ `\\n N:`
- Lab 1 starts at **first lab Heading1**, not page 0

</div>
<div>

## Typical structure

| Section | Include? |
|---------|----------|
| Cover / TOC | No |
| Lab 1 Heading1 → Lab 2 | Lab 1 file |
| Lab 2 Heading1 → Lab 3 | Lab 2 file |
| … | … |
| Lab N → end | Lab N file |

</div>

---

# Step 3–4: Trim XML safely

**Format-preserving cut:**

1. Deep-copy body elements for the lab range
2. Keep original `w:sectPr` at end
3. Replace **only** `word/document.xml` in a full zip copy
4. Do not touch styles, media, rels, or settings

**Why:** Rebuilding from text loses AMD Word styles, SEQ fields, tables, and images.

---

# Step 5: Clean first-page heading

**Before (field codes):**
`Lab 1: Versal AI Engine Tool Flow`

**After (plain title):**
`Versal AI Engine Tool Flow`

- Remove QUOTE / SEQ field runs
- Keep `w:pPr`, bookmarks
- One plain `w:r` / `w:t` with title text

---

# Step 6: Name & validate

## Output naming

```
{NN} {title}.docx
```

Examples:
- `01 Versal AI Engine Tool Flow.docx`
- `02 Versal AI Engine Tool Flow – Makefile.docx`

## Validation checklist

- [ ] Heading1 = title only (no `fldChar`)
- [ ] No `TOC1` paragraphs
- [ ] Starts with Abstract / Objectives
- [ ] Opens in Word with formatting intact

---

# Step 7: Last-page header cleanup

AMD workbooks use a **final section** whose headers/footers appear on trailing blank page(s).

- Locate final `sectPr` header/footer parts
- Remove embedded AMD logo images (`a:blip`, `v:imagedata`)
- Keep regular page headers/footers unchanged

---

# Step 8–9: PDF export & metadata

## Export & trim
- Export DOCX → PDF via Word COM
- Remove up to **3** trailing blank pages (zero text)

## Document Properties

| Field | Value |
|-------|-------|
| Title | Lab title |
| Author | `AMD, Inc.` |
| Subject | Lab title |

---

<!-- _class: lead -->

# Run the pipeline

---

# Command

```bash
python ~/.cursor/skills/split-lab-workbook/scripts/run_split_pipeline.py "workbook.docx"
```

**Optional output folder:**
```bash
python .../run_split_pipeline.py "workbook.docx" -o "output/folder"
```

**Requires:** `pip install lxml pypdf` + Microsoft Word (Windows)

**Split only:** `--split-only` | **No PDF:** `--no-pdf`

---

<!-- _class: closing -->

![w:700](C:/Users/Vnelliko/.claude/skills/psas-amd-marp/images/amd-text-watermark.png)
