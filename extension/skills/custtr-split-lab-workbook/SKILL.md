---
name: split-lab-workbook
description: >
  Splits a combined AMD lab workbook .docx into separate lab files by lab number while preserving
  Word formatting, then post-processes outputs: removes last-page AMD header images, exports PDFs,
  trims trailing blank pages, sets PDF metadata, and exports a combined workbook PDF with lab
  bookmarks and document properties. Prompt the user for missing inputs (workbook path, output
  folder, pipeline scope) and confirm lab count before running. Use when the user asks to break,
  split, or cut a lab workbook into individual lab documents, remove Lab N prefixes from headings,
  or name outputs like "01 Versal AI Engine Tool Flow.docx". Do not rebuild documents with
  python-docx or Word save — trim OOXML only.
---

# Split Lab Workbook

Split a combined AMD training **lab workbook** (`.docx`) into standalone lab files — one per lab — without changing formatting. Optionally run post-processing to clean last-page headers, export PDFs, trim trailing blank pages, set document metadata, and export a combined workbook PDF with lab bookmarks.

**Visual workflow:** [workflow-slides.md](workflow-slides.md) (AMD MARP deck — open with Marp extension)

## When to use

- User has one `.docx` containing Lab 1, Lab 2, … Lab N
- User wants separate files named `NN Lab Title.docx`
- Each lab should start on its own first page (no cover, TOC, or Lab FAQ from the combined workbook)
- First-page heading should show **title only** — no `Lab 1:` prefix or SEQ field codes
- User wants matching PDFs with no trailing blank pages and populated Document Properties
- User wants a combined workbook PDF (`{part-number}.pdf`) with lab bookmarks, metadata, and correct blank pages before the back cover

## Hard rules

| Do | Don't |
|----|-------|
| Copy the full `.docx` zip and trim `word/document.xml` body elements only | Re-save through Word, `python-docx`, or text extraction |
| Preserve styles, tables, images, bookmarks, and `sectPr` | Rewrite paragraph content or restyle headings |
| Split at `Heading1` paragraphs containing lab numbers | Split on TOC lines (`TOC1`) or plain-text grep alone |
| Name outputs `{NN} {title}.docx` (two-digit lab number + space + title) | Include workbook part number or `- Lab NN -` in filename |
| Remove AMD images from **final-section** header/footer parts only | Strip images from regular page headers/footers |
| Trim up to 3 trailing blank PDF pages (zero extracted text) | Remove pages with visible lab content |

## Quick start (full pipeline)

```bash
python ~/.cursor/skills/split-lab-workbook/scripts/run_split_pipeline.py "path/to/workbook.docx"
```

Optional output folder:

```bash
python ~/.cursor/skills/split-lab-workbook/scripts/run_split_pipeline.py "workbook.docx" -o "output/folder"
```

**Split only** (no post-processing):

```bash
python ~/.cursor/skills/split-lab-workbook/scripts/run_split_pipeline.py "workbook.docx" --split-only
```

**Split + DOCX post-process** (no PDF):

```bash
python ~/.cursor/skills/split-lab-workbook/scripts/run_split_pipeline.py "workbook.docx" --no-pdf
```

**Inspect only** (pre-flight; no files written):

```bash
python ~/.cursor/skills/split-lab-workbook/scripts/run_split_pipeline.py "workbook.docx" --inspect
```

Individual scripts (when running steps manually):

```bash
python ~/.cursor/skills/split-lab-workbook/scripts/split_lab_workbook.py "workbook.docx"
python ~/.cursor/skills/split-lab-workbook/scripts/postprocess_lab_outputs.py "output/folder" --docx-only
powershell.exe -ExecutionPolicy Bypass -File ~/.cursor/skills/split-lab-workbook/scripts/export_lab_pdfs.ps1 -Folder "output/folder"
python ~/.cursor/skills/split-lab-workbook/scripts/postprocess_lab_outputs.py "output/folder" --pdf-only
python ~/.cursor/skills/split-lab-workbook/scripts/export_workbook_pdf.py "workbook.docx" -o "output/folder/workbook.pdf"
```

**Dependencies:** `lxml`, `pypdf` (`pip install lxml pypdf`)

**PDF export:** Requires Microsoft Word on Windows (uses Word COM via PowerShell).

**Locked file?** The split script copies the source to `%TEMP%\lab-workbook-split-source.docx` when the original is open in Word.

## User prompting

**Always follow this prompting workflow before running scripts.** Use the **AskQuestion** tool for structured choices. Do not start the pipeline until required inputs are known and the user confirms the pre-flight summary.

### Step 0 — Gather inputs

| Input | When to prompt | Default |
|-------|----------------|---------|
| Source workbook `.docx` | User did not provide a path | — (required) |
| Output folder | User did not specify | Same folder as source |
| Pipeline scope | User did not say split-only / no-pdf / full | Full pipeline |

**Do not prompt** for values the user already gave in their message (e.g. a path, `-o` folder, or "split only").

**Source path missing** — if the user named a folder but not a file, list `*-wkb-lab*.docx` candidates in that folder and ask which workbook to split.

**Multiple candidates** — use AskQuestion to pick one file; do not guess.

### Step 0b — Pipeline scope (AskQuestion)

Ask only when scope is unclear:

| Option | Runs |
|--------|------|
| **Full pipeline (Recommended)** | Split → DOCX cleanup → split-lab PDF export → split-lab PDF cleanup/metadata → combined workbook PDF |
| **Split + DOCX cleanup only** | Split → remove last-page header images; no PDF |
| **Split DOCX only** | Steps 1–6 only; no post-processing |

Map user phrases: "split only" → Split DOCX only; "no pdf" / "docx only" → Split + DOCX cleanup only.

### Step 0c — Output folder (AskQuestion)

Ask only when the user might want a different destination:

| Option | Behavior |
|--------|----------|
| **Same folder as source (Recommended)** | Write outputs next to the combined workbook |
| **Custom folder** | Ask for path in follow-up chat |

### Step 0d — Pre-flight inspect and confirm

Before writing any files, run inspect:

```bash
python ~/.cursor/skills/split-lab-workbook/scripts/run_split_pipeline.py "workbook.docx" --inspect
```

Present a short summary in chat:

```
Source: conn-rfsoc-2026.1-wkb-lab-rev1.docx
Output:  C:\...\RFSoC
Labs:    8
Scope:   Full pipeline

  01  RF-ADC: IP Configuration
  02  RF-DAC: IP Configuration
  ...
```

Then use **AskQuestion** to confirm:

| Option | Action |
|--------|--------|
| **Run pipeline (Recommended)** | Execute with chosen scope and output folder |
| **Change output folder** | Ask for new path, re-run `--inspect`, confirm again |
| **Change pipeline scope** | Re-ask scope question, confirm again |
| **Cancel** | Stop; do not run scripts |

**Do not skip confirmation** unless the user explicitly says to proceed without prompting (e.g. "run it", "no prompts", "just do it").

### Prompting checklist

```
- [ ] Source workbook path resolved
- [ ] Output folder resolved (default or custom)
- [ ] Pipeline scope resolved (default: full)
- [ ] --inspect run; lab list shown to user
- [ ] User confirmed Run pipeline (or explicit skip)
- [ ] Then run run_split_pipeline.py with appropriate flags
```

## Workflow checklist

```
- [ ] Step 1: Confirm source is a combined lab workbook (.docx)
- [ ] Step 2: Locate lab split points (Heading1 + lab number)
- [ ] Step 3: Define ranges — each lab from its Heading1 to the next
- [ ] Step 4: For each lab, copy docx and trim document.xml body children
- [ ] Step 5: Clean first Heading1 — remove Lab N prefix and field codes
- [ ] Step 6: Save as NN Title.docx and validate first page
- [ ] Step 7: Remove AMD images from final-section header/footer (last page)
- [ ] Step 8: Export PDF via Word; trim trailing blank pages (1–3)
- [ ] Step 9: Set PDF metadata (Title, Author, Subject) on split-lab PDFs
- [ ] Step 10: Export combined workbook PDF from source `.docx` with metadata, bookmarks, and blank pages
```

### Step 1 — Inspect source

Read `word/document.xml` inside the `.docx` zip. AMD lab workbooks use:

- `Heading1` — `Lab N: Title` (often Word SEQ/QUOTE field codes in XML)
- Front matter before Lab 1 — cover, Lab FAQ, Table of Contents (`TOC1` lines listing all labs)

**Do not include front matter** in any output file. Lab 1 starts at the first `Heading1` lab heading (same as Lab 2–N).

### Step 2 — Find split points

Scan body children for paragraphs where:

1. Style is `Heading1`
2. Text matches `Lab\s*(\d+)\s*:` **or** SEQ pattern `\\n\s*(\d+)\s*:` (field-code headings)

Example indices from a typical workbook:

| Lab | Start element | End element |
|-----|---------------|-------------|
| 1 | first Heading1 | next lab Heading1 |
| 2 | Lab 2 Heading1 | Lab 3 Heading1 |
| … | … | … |
| N | Lab N Heading1 | last content before `sectPr` |

### Step 3 — Trim body XML (format-safe cut)

For each range:

1. Deep-copy body children from `start_idx` to `end_idx` (exclusive)
2. Re-append original `w:sectPr` at end
3. Replace only `word/document.xml` inside a full copy of the source zip
4. Leave all other zip parts unchanged (styles, media, rels, settings)

### Step 4 — Clean first-page heading

On the first `Heading1` in each output file:

- **Remove** QUOTE/SEQ field runs and `Lab N:` prefix
- **Keep** `w:pPr`, `bookmarkStart`, `bookmarkEnd`
- **Replace** visible text with title only, e.g. `Versal AI Engine Tool Flow`

Target XML pattern:

```xml
<w:p>
  <w:pPr><w:pStyle w:val="Heading1"/></w:pPr>
  <w:bookmarkStart w:id="0" w:name="_Toc..."/>
  <w:r><w:t>Versal AI Engine Tool Flow</w:t></w:r>
  <w:bookmarkEnd w:id="0"/>
</w:p>
```

### Step 5 — Output naming

```
{lab_num:02d} {sanitized_title}.docx
```

Examples:

- `01 Versal AI Engine Tool Flow.docx`
- `02 Versal AI Engine Tool Flow – Makefile.docx`
- `06 AI Engine-ML Programming Model.docx`

Write to the **same folder as the source** unless the user specifies otherwise.

### Step 6 — Validate split

For each output file, confirm:

- First paragraph is `Heading1` with **title only** (no `Lab 1:`, no `fldChar`)
- No `TOC1` paragraphs (no multi-lab table of contents)
- First visible section is Abstract / Objectives (lab content), not cover or Lab FAQ
- File opens in Word with formatting intact

### Step 7 — Remove last-page AMD header/footer images

AMD workbooks add a **final section** (`sectPr` at end of `document.xml`) whose header/footer parts are used on trailing blank page(s). These parts contain an embedded AMD logo image.

For each split DOCX:

1. Resolve header/footer parts referenced by the **final** `sectPr`
2. Remove `w:r` runs containing embedded images (`a:blip` or `v:imagedata`)
3. Remove orphaned image relationships from those header/footer `.rels` files
4. Do **not** modify regular page headers/footers (lab content pages keep AMD branding)

Script: `postprocess_lab_outputs.py --docx-only`

### Step 8 — Export PDF and trim trailing blank pages

1. Export each `NN Title.docx` to PDF via Word (`ExportAsFixedFormat`, format 17)
2. Walk backward from the last page; remove up to **3** consecutive pages with zero extracted text

Trailing blank pages are caused by the final section break in the workbook template.

Script: `export_lab_pdfs.ps1`, then `postprocess_lab_outputs.py --pdf-only`

### Step 9 — Set PDF document metadata

For each split PDF, set Document Properties:

| Field | Value |
|-------|-------|
| Title | Lab title (from filename, e.g. `Design Tool Flow`) |
| Author | `AMD, Inc.` |
| Subject | Same as Title |

Script: `postprocess_lab_outputs.py --pdf-only` (runs after blank-page trim)

### Step 10 — Export combined workbook PDF

After all split-lab PDFs are complete, export the **original combined workbook** (the pipeline input `.docx`) to a single PDF in the user-specified output folder. This is the last step of the full pipeline.

Script: `export_workbook_pdf.py` (also invoked automatically by `run_split_pipeline.py`)

**Input:** the combined workbook `.docx` passed to the pipeline (not the split lab files)

**Output:** `{part-number}.pdf` in the output folder (e.g. `conn-rfsoc-2026.1-wkb-lab-rev1.pdf`)

#### Document properties

| Field | Value |
|-------|-------|
| Title | `<workbook title> Lab Workbook <version>` (e.g. `Designing with the Zynq UltraScale+ RFSoC Lab Workbook 2026.1`) |
| Author | `AMD, Inc.` |
| Subject | Same as Title |

**Title source logic:**

1. Read Word Info metadata (`docProps/core.xml`) if present
2. If Info metadata does not match the cover page title (below `AMD ADAPTIVE COMPUTING CUSTOMER TRAINING`), use the cover page title from `CoverTitle` + `Lab Workbook`
3. Append version from the cover part number (`CoverPartNumber`, e.g. `conn-rfsoc-2026.1-wkb-lab-rev1` → `2026.1`)

#### Initial view

Set `/PageMode` to `/UseOutlines` so the PDF opens with the **Bookmarks Panel and Page** visible.

#### Lab bookmarks

Create one bookmark per lab at the PDF page where that lab's content begins (the page with **Abstract**, not the Table of Contents page number). Bookmark text matches the combined workbook heading, e.g. `Lab 1: RF-ADC: IP Configuration`.

**Do not** create bookmarks for blank pages or the back cover.

#### Blank pages before back cover

After export, check the **printed page number** in the footer of the last content page (before blank pages and back cover):

| Last content page (printed) | Action |
|-----------------------------|--------|
| **Odd** (e.g. 181) | Insert **2 blank pages** before the back cover |
| **Even** (e.g. 230) | No change |

If Word already exported some blank pages before the back cover, insert only enough additional blanks to reach 2 total. Never add bookmarks for inserted blank pages.

## Example reference

Golden sample output:

```
01 Versal AI Engine Tool Flow.docx
01 Versal AI Engine Tool Flow.pdf
aie-arch-2026.1-wkb-lab-rev1.pdf
```

First page heading text: `Versal AI Engine Tool Flow` (not `Lab 1: Versal AI Engine Tool Flow`)

PDF metadata: Title = `Versal AI Engine Tool Flow`, Author = `AMD, Inc.`, Subject = `Versal AI Engine Tool Flow`

Combined workbook PDF metadata: Title = `Designing with Versal AI Engine: Architecture and Design Flow - 1 Lab Workbook 2026.1`, Author = `AMD, Inc.`, Subject = same as Title; opens with Bookmarks panel; lab bookmarks at each lab start page.

## Script location

```
~/.cursor/skills/split-lab-workbook/scripts/
  split_lab_workbook.py      # Steps 1–6: split combined workbook
  postprocess_lab_outputs.py # Steps 7, 8–9: DOCX images + split-lab PDF cleanup/metadata
  export_lab_pdfs.ps1        # Step 8: Word COM PDF export for split labs (Windows)
  export_workbook_pdf.py     # Step 10: combined workbook PDF export + post-processing
  run_split_pipeline.py      # Full pipeline orchestrator
```

Use the bundled scripts instead of regenerating logic. Extend only for new edge cases (e.g. alternate heading styles).

## Known limitations

- Output files retain all embedded media from the combined workbook (~10 MB each). This preserves formatting; pruning unused media is a separate optional step.
- Lab numbers inside SEQ field codes require the `\\n\s*(\d+)\s*:` fallback regex — plain `^Lab\s*\d+` is not sufficient.
- PDF export requires Microsoft Word installed on Windows.
- Blank-page detection for split-lab PDFs uses zero extracted text; unusual PDFs with invisible-only trailing content may need manual review.
- Combined workbook PDF blank-page rule uses the **printed footer page number** on the last content page, not the PDF page index.
- Combined workbook PDF export runs only in the **full pipeline** (skipped with `--split-only` or `--no-pdf`).

## Additional resources

- Step-by-step MARP deck: [workflow-slides.md](workflow-slides.md)
- Implementation: [scripts/](scripts/)
