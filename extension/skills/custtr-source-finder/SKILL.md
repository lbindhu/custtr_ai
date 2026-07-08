---
name: custtr-source-finder
description: >
  Analyzes a PowerPoint (.pptx), Word (.docx), or PDF (.pdf) file and finds the original
  source URLs for the content — both text and images/diagrams. Searches only within
  approved AMD/Xilinx documentation domains. Produces a reference table mapping each
  slide/section/page to its most likely source URL(s), flags content that may be outdated,
  and scores each match with a confidence level. Use this skill whenever the user wants to:
  trace where document content came from, build a reference list for a presentation or
  document, verify if content matches current official documentation, check source
  attribution for AMD/Xilinx files, or audit a deck or doc for content provenance.
  Trigger on: "find sources for my slides", "find sources for this document", "where does
  this content come from", "source URLs for PPT", "source URLs for PDF", "source URLs for
  Word doc", "reference list for presentation", "check if slides are up to date",
  "attribution for deck", "audit slide content", "audit document content".
---

# Document Source Finder

You analyze a PowerPoint, Word, or PDF file and find the original source URLs for its
content. You only search within the three approved AMD/Xilinx domains — never guess or
fabricate URLs.

## Approved Search Domains (priority order)

1. **`docs.amd.com`** — official AMD documentation, always preferred
2. **`xilinx-wiki.atlassian.net`** — curated internal wiki, use if docs.amd.com has no match
3. **`github.com/Xilinx`** — code/examples, lowest priority unless the only match

All URLs you return MUST be from one of these domains. If you cannot find a matching
page, say so explicitly — do not invent URLs.

---

## Workflow

### Step 1: Extract content

Run the single entry-point script — it auto-detects file type (.pptx, .docx, .pdf):

```bash
python "$SKILL_DIR/scripts/extract.py" "<path_to_file>"
```

Each JSON element includes:
- `type` — "slide", "section", or "page"
- `searchable` — false = skip this item (reason in `skip_reason`)
- `skip_reason` — `"non-content slide"` or `"image-only or blank"`
- `text` — cleaned strings (noise + strikethrough already removed)
- `images` — list of image descriptions (empty string = no metadata)
- `has_images` / `is_blank` — additional flags

**Skip rules (automatic):**
- `non-content slide` — title matches training scaffolding: Objectives, Summary,
  Disclaimer, Quiz, Apply Your Knowledge, Lab N, Q&A, Thank You, etc.
- `image-only or blank` — no meaningful text (< 3 words per line) and no images

> ⚠️ **PDF note:** `pdftotext` cannot detect strikethrough. If `may_have_strikethrough`
> is true (filename contains "draft"/"review"), treat text with extra caution.

Do NOT use `pptx_read`, `docx_read`, or `pdf_extract_text` MCP tools.

---

### Step 2: Determine the target release version (once, before searching)

Do this ONCE at the start — not per slide:

1. Search `docs.amd.com` for the product name from the document title:
   ```
   query="<product name> documentation" allowed_domains=["docs.amd.com"]
   ```
2. Parse version strings from returned URLs using pattern `\d{4}\.\d+`
   (e.g. `2026.1` from `docs.amd.com/r/2026.1-English/...`).
3. **Prefer `en-US` URLs** — AMD serves the latest release there. If the search
   returns `docs.amd.com/r/en-US/...`, those are always current.
4. Pick the highest numbered version as your **target version** fallback.
5. Tell the user: `"Targeting: en-US (always latest). Versioned fallback: 2026.1"`

---

### Step 3: Build a search library (one search per unique topic, not per slide)

**This is the key speed optimization.** Many slides cover the same topic — searching
once and reusing saves 60–80% of search calls for typical decks.

**Before searching any slide:**
1. Scan all `searchable` items and group them by topic cluster. Items with the same
   title or significant text overlap belong to the same cluster.
2. For each cluster, formulate ONE representative search query.
3. Run the search once per cluster (3 searches — one per domain).
4. Cache the results keyed by cluster.

**For each slide, look up cached results** — only run a fresh search if the slide's
topic has no cache entry.

**Query construction rules:**
- Extract 3–5 of the most distinctive *technical nouns* from the slide text.
  Prefer product names, architecture names, and feature names over generic terms.
- Avoid: "overview", "introduction", "features", "architecture" (alone),
  "description", "example", "note", "important".
- For multi-word technical phrases, wrap in quotes: `"block RAM"`, `"look-up table"`,
  `"carry logic"`.
- For image-heavy slides, append the inferred diagram type: `"block diagram"`,
  `"architecture diagram"`, `"flowchart"`.
- Sanitize special characters: wrap terms containing `.`, `-`, `/` in quotes
  (e.g., `"PCIe 5.0"`, `"Zynq-7000"`, `"ARM Cortex-A9"`).

**Example query for a LUT slide:**
```
"look-up table" "six-input LUT" Versal CLB cascade multiplexer
```
Not: `LUT features overview Versal architecture`

---

### Step 4: Search per domain using the search library

For each unique topic query, run three searches — one per domain:

```
Search 1: query="<terms>" allowed_domains=["docs.amd.com"]
Search 2: query="<terms>" allowed_domains=["xilinx-wiki.atlassian.net"]
Search 3: query="<terms>" allowed_domains=["github.com"]
```

**Version filtering for `docs.amd.com` results:**
- **Always prefer `en-US` URLs** — these serve the latest release.
- If only versioned URLs appear, pick the one matching the target version (e.g. `2026.1`).
- If target version not found, use the next older version and mark as `⚠️ Older version`.
- Never use an older versioned URL when a `en-US` URL exists for the same page.

**Domain priority tiebreaker** (when multiple domains match):
1. `docs.amd.com` — always wins if High or Medium confidence
2. `xilinx-wiki.atlassian.net` — use if docs.amd.com returns Low confidence or no match
3. `github.com` — use only if no match in the above two

---

### Step 5: Verify candidates

For each domain's top result:
1. Fetch with `WebFetch` to confirm content is actually present on the page
2. Never include a URL based on the search snippet alone
3. Pick the domain with the best-matching content per the priority order above

**Batch verification:** Collect all top candidate URLs from the search phase first,
then fetch them together rather than one-at-a-time per slide. This runs in parallel
and cuts verification time significantly.

---

### Step 6: Assess freshness and confidence

Compare the slide/section content against the live fetched page:
- Do key facts, version numbers, feature names match?
- Flag **⚠️ Possibly Outdated** if there are discrepancies

**Confidence thresholds (quantified):**

| Confidence | Criteria |
|------------|---------|
| `High` | ≥3 distinctive phrases found verbatim on the page, OR ≥2 phrases + page title is an exact/near-exact match |
| `Medium` | ≥2 distinctive phrases match, OR ≥1 phrase + page topic clearly covers the slide content |
| `Low` | ≥1 phrase matches but page is tangentially related, OR topic area matches with no phrase overlap |
| `—` | Not searchable or no source found |

---

### Step 7: Produce the output

#### Header summary

Before the table, output:

```
**Doc:** 04. AMD Versal Adaptive SoC - Programmable Logic (PL)_SB_V1.pptx
**Targeting:** docs.amd.com en-US (latest) | Versioned fallback: 2026.1
**Slides:** 31 total | 25 searchable | 6 skipped (non-content/blank)
**Primary source:** AM005 – Versal CLB Architecture Manual (18 slides)
**Also referenced:** AM007 (5 slides) | xilinx-wiki.atlassian.net (2 slides)
```

Extract the doc short name (AM005, AM007, UG1273, etc.) from the URL pattern
`docs.amd.com/r/en-US/<doc-id>/...`. For wiki/GitHub, use the domain name.

#### Reference table

| # | Title / Topic | Source URL | Match Type | Confidence | Status |
|---|--------------|-----------|------------|------------|--------|
| Slide 1 | Title slide | — | — | — | — |
| Slide 2 | Objectives | — | Non-content | — | — |
| Slide 3 | CLB Architecture | https://docs.amd.com/r/en-US/am005-versal-clb/CLB-Architecture | Text + Image | High | ✅ Current |
| Slide 4 | LUT features | https://docs.amd.com/r/en-US/am005-versal-clb/Look-Up-Table | Text | Medium | ⚠️ Possibly Outdated |
| Slide 5 | (diagram only) | — | Image-only or blank | — | — |
| Slide 6 | Some topic | https://docs.amd.com/r/2025.2-English/am005-versal-clb/... | Text | Medium | ⚠️ Older version |
| Slide 7 | PS-PL Interface | No source found | — | — | ❓ Unknown |

**Match Type:**
- `Text` / `Image` / `Text + Image` — what was matched
- `Non-content` — training scaffold slide, skipped by design
- `Image-only or blank` — no text to search
- `No source found` — searched all domains, no confirmed match

**Status:**
- `✅ Current` — content matches latest (`en-US`) page
- `⚠️ Possibly Outdated` — content found but discrepancies with live page
- `⚠️ Older version` — only found in a prior release (e.g. 2025.2), not latest
- `❓ Unknown` — searched but no source found
- `—` — not applicable

#### Notes section

After the table:
- **Outdated slides** — explain what changed on each flagged slide
- **Low-confidence matches** — flag for manual review with brief reason
- **Secondary sources** — if multiple domains matched, list alternates here

---

## Anti-hallucination rules

1. **Never construct or guess URLs** — only URLs returned by `WebSearch` and confirmed by `WebFetch`
2. **Always verify** — fetch the page before including it
3. **Prefer "No source found"** over a low-confidence guess
4. **No URL pattern extrapolation** — don't substitute product names into existing URL patterns
5. **Quote your evidence** — in Notes, state which phrase led you to the source URL

---

## Handling large files

Process in batches of 5 and report progress after each batch. Build the full search
library upfront before processing individual slides — this avoids redundant searches
across batches.

---

## Example invocations

User: "Here's my Versal AI Core deck — `versal_overview.pptx`. Find where each slide came from."
→ `extract.py` → build search library → search per domain → verify → produce table.

User: "Find sources for this Word doc — `versal_design_guide.docx`."
→ `extract.py` → section-by-section → same flow.

User: "Where did the content in `am005_clb.pdf` come from?"
→ `extract.py` → page-by-page → same flow.
