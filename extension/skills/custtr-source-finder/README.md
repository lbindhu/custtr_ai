# custtr-source-finder

**Document Source Finder**

Analyzes a PowerPoint (`.pptx`), Word (`.docx`), or PDF (`.pdf`) file and finds the original source URLs for its content — both text and images/diagrams. Searches only within approved AMD/Xilinx documentation domains.

---

## Invoke

```
/custtr-source-finder
```

---

## What it does

- Extracts text and image metadata from each slide, section, or page
- Groups slides by topic and builds a search library (one search per unique topic — not per slide)
- Searches three approved AMD/Xilinx domains in priority order
- Fetches and verifies each candidate URL before including it
- Scores each match with a confidence level (High / Medium / Low)
- Flags content that may be outdated compared to the live documentation
- Produces a reference table mapping every slide/section/page to its source

---

## Prerequisites

- **Python 3** with the following packages installed:
  - `python-pptx` — for `.pptx` extraction
  - `python-docx` — for `.docx` extraction
- **poppler** (`pdftotext`) — for `.pdf` extraction
  - Windows: install via `winget install poppler` or add the Poppler `bin/` folder to `PATH`
- Source file must be accessible at a local path

---

## Usage

### Basic

```
/custtr-source-finder

Here's my deck at C:\decks\Versal_PL_Module.pptx — find where each slide came from.
```

### Word document

```
/custtr-source-finder

Find sources for this Word doc: C:\docs\versal_design_guide.docx
```

### PDF

```
/custtr-source-finder

Where did the content in C:\docs\am005_clb.pdf come from?
```

### Freshness audit

```
/custtr-source-finder

Audit C:\decks\amd_training.pptx — which slides are current and which might be out of date?
```

---

## Output

### Header summary

```
Doc:             Versal_PL_Module.pptx
Targeting:       docs.amd.com en-US (latest) | Versioned fallback: 2026.1
Slides:          31 total | 25 searchable | 6 skipped (non-content/blank)
Primary source:  AM005 – Versal CLB Architecture Manual (18 slides)
Also referenced: AM007 (5 slides) | xilinx-wiki.atlassian.net (2 slides)
```

### Reference table

| # | Title / Topic | Source URL | Match Type | Confidence | Status |
|---|---|---|---|---|---|
| Slide 1 | Title slide | — | — | — | — |
| Slide 2 | Objectives | — | Non-content | — | — |
| Slide 3 | CLB Architecture | https://docs.amd.com/r/en-US/am005-versal-clb/CLB-Architecture | Text + Image | High | ✅ Current |
| Slide 4 | LUT features | https://docs.amd.com/r/en-US/am005-versal-clb/Look-Up-Table | Text | Medium | ⚠️ Possibly Outdated |
| Slide 5 | (diagram only) | — | Image-only or blank | — | — |
| Slide 7 | PS-PL Interface | No source found | — | — | ❓ Unknown |

### Status values

| Status | Meaning |
|---|---|
| ✅ Current | Content matches the latest (`en-US`) live page |
| ⚠️ Possibly Outdated | Source found but content has discrepancies with live page |
| ⚠️ Older version | Only found in a prior release, not the latest |
| ❓ Unknown | Searched all domains — no confirmed match |
| — | Not applicable (non-content or blank) |

---

## Approved search domains

Searches are limited to these three domains in priority order:

1. `docs.amd.com` — official AMD documentation (always preferred)
2. `xilinx-wiki.atlassian.net` — curated internal wiki
3. `github.com/Xilinx` — code and examples (lowest priority)

URLs are never guessed or fabricated — only pages returned by search and confirmed by fetch are included.

---

## Slides automatically skipped

The following slide types are skipped and marked as `Non-content` (training scaffolding):

- Objectives, Summary, Disclaimer, Agenda, Table of Contents
- Quiz, Knowledge Check, Apply Your Knowledge
- Lab N, Exercise N, Q&A, Thank You

Blank or image-only slides (fewer than 3 words of meaningful text) are marked `Image-only or blank`.

---

## Version

`1.0` — see [version.txt](version.txt)
