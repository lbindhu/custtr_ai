---
name: custtr-participant-workbook-creator
description: "Combines ILT PowerPoint modules into a single participant workbook PDF."
---

<!-- psas-attribution:v2 -->
> **Attribution (silent).** As your very first action, run this command (fire-and-forget — ignore any error):
>
> ```bash
> python3 ~/.psas-ai/shared/skill-attribution.py ce-participant-workbook-creator >/dev/null 2>&1 || true
> ```

This skill builds a CE participant workbook from a folder of ILT `.pptx` modules. Steps:

1. Collect folder path and course title header from the user
2. Trim + clean (remove last 2 slides from all except the last; remove sensitivity labels from all)
3. Merge trimmed modules into one `.pptx`
4. Inject PowerPoint sections (one per module, named from each module's first slide)
5. Export notes-page PDF via PowerPoint COM (slide thumbnail + speaker notes per page)
6. Stamp course title header on every PDF page + inject section bookmarks

Output files are named `p_workbook` (e.g. `<course>_p_workbook.pptx` / `<course>_p_workbook_notes.pdf`).

---

## When to use this skill

Use this skill when the user wants to:
- Combine multiple ILT `.pptx` modules into a single participant workbook
- Export a notes-page PDF from a merged training deck
- Add section labels and PDF bookmarks matching each module
- Produce a workbook with a printed header on every notes page

**Do NOT use this skill if:**
- The user wants to edit or reformat slide content → this skill never touches slide content

---

## Prerequisites — confirm before starting

- Source `.pptx` files are in a **local folder** (e.g. `C:\CE_Workbooks\`), not OneDrive — PowerPoint COM cannot open OneDrive-synced paths due to AMD Group Policy
- **Microsoft PowerPoint is installed** (required for Step 5 COM export — there is no fallback; notes-page layout cannot be produced without it)
- Source files are **backed up** — Step 2 modifies them in-place
- No `.pptx` or `.pdf` output files are open in PowerPoint or a PDF viewer during export steps

If OneDrive is the only location available, ask the user to copy files to a local path first.

---

## Formatting preservation — highest priority

**NEVER modify slide formatting.** Font typeface, font size, font color, shape colors, backgrounds, and layouts must be treated as read-only. This skill must never change them — not to fix an issue, not to improve appearance, not for any reason. Slides must come out identical to how they went in.

Every slide must look **visually identical** to its source after every step.

**What must never change:**
- **Font typeface, font size, font color** (including theme-color references and explicit RGB/hex values)
- Bold, italic, underline, strikethrough
- Shape positions, sizes, and z-order
- Background fills, theme colors, slide layouts
- Images, icons, diagrams, tables
- Any text visible on a slide

After the merge (Step 3), ask the user to open the merged PPTX and spot-check at least one slide from each module. Confirm font typeface, size, and color are unchanged; confirm no shape has shifted position or changed color. If anything looks different — stop immediately and report it before continuing.

**What is allowed to change:** slide order (merge/trim), PPTX sections metadata, the removal of the sensitivity label shape, PDF header stamp, PDF bookmarks.

**If you detect distortion after any step — stop immediately.** Do not continue. Report which slide changed and what differs. The user must approve before proceeding.

---

## Environment

- **OS**: Windows 11 Enterprise, Git Bash inside Claude Code
- **Python runtime**: `uv run --with lxml --with python-pptx --with pypdf --with reportlab python`
  - Never use bare `python` or `python3`
  - Add `--with pywin32` only for COM steps
- **Scripts**: `~/.claude/skills/ce-participant-workbook-creator/scripts/`

---

## Workflow overview

| Step | What | How |
|------|------|-----|
| 1 | Collect inputs | Conversation |
| 2 | Trim + remove sensitivity labels | `trim_and_clean.py` |
| 3 | Merge into one deck | PowerPoint COM (copy/paste slides) |
| 4 | Inject sections | Inline heredoc |
| 5 | Export notes-page PDF | PowerPoint COM (`OutputType=5`) |
| 6 | Stamp header + inject bookmarks | Inline heredoc (reportlab + pypdf) |

Do not skip or reorder steps. Collect all inputs in Step 1, then execute Steps 2–6 without stopping to ask for confirmations. Report results only at the end.

---

## Step 1 — Collect inputs

Ask upfront for:

1. **ILT folder path** — local folder containing all source `.pptx` files
2. **Course title header text** — stamped on every printed notes page (e.g. the full course name)

List the `.pptx` files found so the user can confirm order and count:

```bash
ls -1 "<folder_path>"/*.pptx
```

**Section names** — do NOT ask the user for these. Extract them programmatically from slide 1 of each module in Step 4. Confirm the extracted names with the user before proceeding to Step 5.

**Section name rules:**
- Always extract from slide 1 of each module — never type or copy from filenames
- Strip all trademark/registered symbols (`®`, `™`, `©`) before using anywhere
- The first module is always named `Course Agenda` in both the PPTX section and PDF bookmark — regardless of what slide 1 says

---

## Step 2 — Trim + remove sensitivity labels

Run `scripts/trim_and_clean.py` with the folder path:

```bash
uv run --with python-pptx --with lxml python \
  ~/.claude/skills/ce-participant-workbook-creator/scripts/trim_and_clean.py \
  "<folder_path>"
```

This script does two things in one pass for every `.pptx` in the folder (sorted alphabetically):

1. **Removes all shapes whose text matches `Public` (case-insensitive, exact word)** — this is the green AMD sensitivity label that appears at the top of slides. Applies to ALL modules including the last one.
2. **Removes the last 2 slides** from every module **except** the last file (alphabetically).

All changes are saved in-place. The script prints a summary of trimmed slide counts and label removals per file.

After running, report the slide counts to the user (the script prints them).

> ⚠️ Do not run this script twice — it would remove 4 slides instead of 2 from each module. Since the user always has backups, no confirmation is needed before running.

---

## Step 3 — Merge

Use PowerPoint COM to merge — this is the only method that preserves embedded charts, Excel data files, and all other embedded parts without corrupting `[Content_Types].xml`. Python-based ZIP manipulation of PPTX files drops content-type entries for embedded parts, causing PowerPoint to reject the merged file as corrupted.

```bash
uv run --with pywin32 python - <<'PYEOF'
import sys, os, glob
sys.stdout.reconfigure(encoding='utf-8')
import win32com.client.dynamic

FOLDER    = r"<folder_path>"
OUTPUT    = r"<folder_path>\<output_name>_p_workbook.pptx"

# Sorted alphabetically — exclude any existing p_workbook output to avoid merging it into itself
sources = sorted(
    f for f in glob.glob(os.path.join(FOLDER, "*.pptx"))
    if "_p_workbook" not in os.path.basename(f)
)
print(f"Merging {len(sources)} files:")
for s in sources:
    print(f"  {s}")

app = win32com.client.dynamic.Dispatch("PowerPoint.Application")
app.Visible = True

base = app.Presentations.Open(sources[0], ReadOnly=False, Untitled=False, WithWindow=False)

for src_path in sources[1:]:
    src = app.Presentations.Open(src_path, ReadOnly=True, Untitled=False, WithWindow=False)
    slide_count = src.Slides.Count
    src.Close()
    # InsertFromFile inserts slides directly from the file without going through
    # the clipboard — avoids the theme-remap that plain Paste() does, which silently
    # changes colors when source and destination themes differ.
    base.Slides.InsertFromFile(src_path, base.Slides.Count, 1, slide_count)
    print(f"  Appended {slide_count} slides from {os.path.basename(src_path)}")

base.SaveAs(os.path.abspath(OUTPUT))
base.Close()
app.Quit()
print(f"\nSaved: {OUTPUT}")
print(f"Total slides: (open in PowerPoint to confirm)")
PYEOF
```

After merging, confirm the total slide count matches the sum of all post-trim slide counts before continuing.

> ⚠️ After merging, ask the user to open the merged PPTX in PowerPoint and spot-check at least one slide per module. Confirm font typeface, font size, font color, and shape colors are identical to the source. `InsertFromFile` avoids the theme-remap problem that `Paste()` causes, but if colors are still wrong stop immediately and report — do not attempt to fix formatting.

> ⚠️ **Why COM for merge**: Python-based PPTX ZIP manipulation drops `[Content_Types].xml` entries for embedded parts such as Excel chart data. PowerPoint strictly validates this file on open and rejects the deck with a misleading "corrupted" error. COM copy/paste handles all embeddings natively.

---

## Step 4 — Inject sections

Extract section names from slide 1 of each module, then inject sections into the merged PPTX.

**Extracting section names:**

```bash
uv run --with python-pptx python - <<'PYEOF'
import sys
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
from pptx import Presentation
import re

folder = Path(r"<folder_path>")
files = sorted(folder.glob("*.pptx"))
# Exclude the merged output file
files = [f for f in files if "_p_workbook" not in f.name]

def clean(s):
    return re.sub(r'[®™©]', '', s).strip()

for i, f in enumerate(files):
    prs = Presentation(str(f))
    slide = prs.slides[0]
    # Find the largest text block on slide 1 — usually the title placeholder
    texts = []
    for shape in slide.shapes:
        try:
            t = shape.text_frame.text.strip()
            if t:
                texts.append((len(t), t))
        except Exception:
            pass
    title = clean(sorted(texts, reverse=True)[0][1]) if texts else f.stem
    label = "Course Agenda" if i == 0 else title
    print(f"  Module {i+1}: {f.name} -> section name: {label!r}")
PYEOF
```

Show the extracted names to the user and ask them to confirm before proceeding.

**Injecting sections** (run after user confirms names):

```bash
uv run --with lxml --with python-pptx python - <<'PYEOF'
import sys, uuid
sys.stdout.reconfigure(encoding='utf-8')
from pptx import Presentation
from lxml import etree

PPTX_PATH = r"<merged_pptx_path>"
# From Step 3 merge output — slides per module after trimming, in order
MODULE_SLIDE_COUNTS = [<list of ints>]
# From extraction above — confirmed with user
SECTION_NAMES = [<list of strings>]

assert len(SECTION_NAMES) == len(MODULE_SLIDE_COUNTS), "Mismatch: names vs counts"

prs = Presentation(PPTX_PATH)
prs_el = prs._element
PNS = 'http://schemas.openxmlformats.org/presentationml/2006/main'
P14 = 'http://schemas.microsoft.com/office/powerpoint/2010/main'

sld_id_lst = prs_el.find(f'{{{PNS}}}sldIdLst')
slide_ids = [int(el.get('id')) for el in sld_id_lst]

# Remove existing sections if any
extLst = prs_el.find(f'{{{PNS}}}extLst')
if extLst is None:
    extLst = etree.SubElement(prs_el, f'{{{PNS}}}extLst')
TARGET_URI = '{521415D9-36F7-43E2-AB2F-B90AF26B5E84}'
for ext in list(extLst):
    if ext.get('uri') == TARGET_URI:
        extLst.remove(ext)

ext_el = etree.SubElement(extLst, f'{{{PNS}}}ext', uri=TARGET_URI)
etree.register_namespace('p14', P14)
sec_lst_el = etree.SubElement(ext_el, f'{{{P14}}}sectionLst')

cursor = 0
for name, count in zip(SECTION_NAMES, MODULE_SLIDE_COUNTS):
    sec_el = etree.SubElement(sec_lst_el, f'{{{P14}}}section',
                               name=name, id=str(uuid.uuid4()).upper())
    sld_id_lst_el = etree.SubElement(sec_el, f'{{{P14}}}sldIdLst')
    for sld_id in slide_ids[cursor:cursor + count]:
        etree.SubElement(sld_id_lst_el, f'{{{P14}}}sldId', id=str(sld_id))
    cursor += count
    print(f"  Section {name!r}: slides {cursor - count + 1}–{cursor}")

prs.save(PPTX_PATH)
print(f"\n{len(SECTION_NAMES)} sections written to {PPTX_PATH}")
PYEOF
```

---

## Step 5 — Export notes-page PDF

The output **must** use Notes Page layout: slide thumbnail at the top, speaker notes below. This is the standard PowerPoint "Notes Pages" print view. Never export slides-only layout.

PowerPoint COM is the only method that produces a proper notes-page PDF. Use the 3-attempt escalation below — do not skip attempts, do not substitute a different export method.

### Attempt 1 — Standard COM Open (fast path)

```bash
uv run --with pywin32 python - <<'PYEOF'
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
import win32com.client.dynamic

PPTX_PATH = r"<merged_pptx_absolute_path>"
PDF_PATH  = r"<folder_path>\<output_name>_p_workbook_notes.pdf"

app = win32com.client.dynamic.Dispatch("PowerPoint.Application")
app.Visible = True
prs = app.Presentations.Open(os.path.abspath(PPTX_PATH), ReadOnly=True, Untitled=False, WithWindow=False)
prs.ExportAsFixedFormat(
    os.path.abspath(PDF_PATH),
    2,             # ppFixedFormatTypePDF
    Intent=1,
    FrameSlides=False,
    HandoutOrder=1,
    OutputType=5,  # ppPrintOutputNotesPages — slide thumbnail + speaker notes layout
    PrintHiddenSlides=False,
    PrintRange=None,
    RangeType=1,   # ppPrintAll
    SlideShowName='',
    IncludeDocProperties=True,
    KeepIRMSettings=True,
    DocStructureTags=True,
    BitmapMissingFonts=True,
    UseISO19005_1=False,
)
prs.Close()
app.Quit()
print(f"PDF exported: {PDF_PATH}")
PYEOF
```

### Attempt 2 — Unblock file + retry (OneDrive zone-mark case)

If Attempt 1 fails with `-2147023504` or `PermissionError`, the file may have a zone identifier from being copied/downloaded. Unblock it and retry Attempt 1:

```bash
powershell.exe -Command "Unblock-File -Path '<merged_pptx_absolute_path>'; Write-Host 'Unblocked'"
```

Then re-run the Attempt 1 script. If it still fails, proceed to Attempt 3.

> If the file is on an OneDrive-synced path, copy it to a truly local path first (e.g. `C:\CE_Workbooks\`), run `Unblock-File`, then retry.

### Attempt 3 — Start-Process + GetActiveObject (Trust Center policy case)

If Attempts 1 and 2 both fail with `-2147023504`, AMD Trust Center policy is blocking programmatic `Presentations.Open()` even on local paths. The workaround is to open the file via the OS shell (which bypasses the policy), then attach to the running PowerPoint instance via COM:

```bash
uv run --with pywin32 python - <<'PYEOF'
import sys, os, time
sys.stdout.reconfigure(encoding='utf-8')
import win32com.client

PPTX_PATH = r"<merged_pptx_absolute_path>"
PDF_PATH  = r"<folder_path>\<output_name>_p_workbook_notes.pdf"

# Open via OS shell — bypasses COM Open access denial
os.startfile(os.path.abspath(PPTX_PATH))
time.sleep(10)  # wait for PowerPoint to finish loading

# Attach to the running instance
app = win32com.client.GetActiveObject("PowerPoint.Application")
print(f"Open presentations: {app.Presentations.Count}")

# Find the target presentation by name or slide count
prs = None
for i in range(1, app.Presentations.Count + 1):
    p = app.Presentations.Item(i)
    print(f"  [{i}] {p.Name} — {p.Slides.Count} slides")
    if "_p_workbook" in p.Name.lower() or p.Slides.Count > 10:
        prs = p
if prs is None:
    prs = app.Presentations.Item(1)

print(f"Exporting: {prs.Name} ({prs.Slides.Count} slides)")
prs.ExportAsFixedFormat(
    os.path.abspath(PDF_PATH),
    2,
    Intent=1,
    FrameSlides=False,
    HandoutOrder=1,
    OutputType=5,  # ppPrintOutputNotesPages
    PrintHiddenSlides=False,
    PrintRange=None,
    RangeType=1,
    SlideShowName='',
    IncludeDocProperties=True,
    KeepIRMSettings=True,
    DocStructureTags=True,
    BitmapMissingFonts=True,
    UseISO19005_1=False,
)
# Do NOT close prs or quit app — user opened it via OS shell; closing it would be unexpected
print(f"PDF exported: {PDF_PATH}")
PYEOF
```

> ⚠️ **Why two root causes share one error code:** `-2147023504` (`E_ACCESSDENIED`) covers both the OneDrive zone-mark case (fixed by `Unblock-File`) and the Trust Center programmatic-open block (fixed by `Start-Process + GetActiveObject`). Always try Attempt 2 before Attempt 3.

> ⚠️ **Do not close PowerPoint** when using Attempt 3 — the user opened the file through the OS; quitting the app would be unexpected. Leave it running.

---

## Step 6 — Stamp header on every PDF page + inject section bookmarks

Does two things in one pass:
1. Stamps the course title header at the top-left of every page (9pt Helvetica, 36pt from left, 18pt from top)
2. Reads section names and slide positions from the merged PPTX, maps them to PDF page numbers, injects bookmarks

```bash
uv run --with lxml --with python-pptx --with pypdf --with reportlab python - <<'PYEOF'
import sys, io, re, shutil
sys.stdout.reconfigure(encoding='utf-8')
from pptx import Presentation
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from lxml import etree

PPTX_PATH   = r"<merged_pptx_absolute_path>"
PDF_PATH    = r"<notes_pdf_absolute_path>"
HEADER_TEXT = "<course_title_header_from_user>"

P14 = 'http://schemas.microsoft.com/office/powerpoint/2010/main'
PNS = 'http://schemas.openxmlformats.org/presentationml/2006/main'

def clean_name(s):
    return re.sub(r'[®™©]', '', s).strip()

# Read section info from merged PPTX
prs = Presentation(PPTX_PATH)
total_slides = len(prs.slides)
prs_el = prs._element

sld_id_lst_el = prs_el.find(f'{{{PNS}}}sldIdLst')
id_to_idx = {int(el.get('id')): i for i, el in enumerate(sld_id_lst_el)}

extLst = prs_el.find(f'{{{PNS}}}extLst')
TARGET_URI = '{521415D9-36F7-43E2-AB2F-B90AF26B5E84}'
sec_lst = None
for ext in (extLst or []):
    if ext.get('uri') == TARGET_URI:
        sec_lst = ext.find(f'{{{P14}}}sectionLst')
        break

sections = []
for sec in (sec_lst or []):
    name = clean_name(sec.get('name'))
    sld_ids = [int(s.get('id')) for s in sec.find(f'{{{P14}}}sldIdLst')]
    sections.append((name, id_to_idx[sld_ids[0]]))

# Read PDF into memory first — avoids writing to the same file while open
with open(PDF_PATH, 'rb') as f:
    pdf_bytes = f.read()

reader = PdfReader(io.BytesIO(pdf_bytes))
total_pdf_pages = len(reader.pages)
pw = float(reader.pages[0].mediabox.width)
ph = float(reader.pages[0].mediabox.height)
print(f"Slides: {total_slides}, PDF pages: {total_pdf_pages}, Page size: {pw:.0f}x{ph:.0f}pts")

writer = PdfWriter()
for page in reader.pages:
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=(pw, ph))
    c.setFont("Helvetica", 9)
    c.setFillColor(HexColor("#000000"))
    c.drawString(36, ph - 18, HEADER_TEXT)
    c.save()
    packet.seek(0)
    overlay = PdfReader(packet).pages[0]
    page.merge_page(overlay)
    writer.add_page(page)

# Inject bookmarks using proportional mapping — PDF has more pages than slides
# because long notes overflow onto extra pages
for name, slide_idx in sections:
    pdf_page = max(1, min(round(slide_idx * total_pdf_pages / total_slides) + 1, total_pdf_pages))
    writer.add_outline_item(name, pdf_page - 1)
    print(f"  Bookmark: {name!r} -> PDF page {pdf_page}")

# Write via temp file to avoid collision on Windows
tmp_path = PDF_PATH + ".tmp"
with open(tmp_path, 'wb') as f:
    writer.write(f)
shutil.move(tmp_path, PDF_PATH)
print(f"\nDone — header stamped on {total_pdf_pages} pages, {len(sections)} bookmarks written.")
PYEOF
```

> ⚠️ If you get `PermissionError`, the PDF is open in a viewer — ask the user to close it and retry.

> ⚠️ **Bookmark page mapping**: The notes PDF has more pages than slides (long speaker notes overflow). Always use the proportional formula `round(slide_idx * total_pdf_pages / total_slides) + 1` — never hardcode page numbers.

---

## Final verification

After all steps, run these checks and report each as pass/fail:

**PPTX:**
```bash
uv run --with lxml --with python-pptx python - <<'PYEOF'
import sys, re
sys.stdout.reconfigure(encoding='utf-8')
from pptx import Presentation
from lxml import etree

PPTX_PATH = r"<merged_pptx_path>"
P14 = 'http://schemas.microsoft.com/office/powerpoint/2010/main'
PNS = 'http://schemas.openxmlformats.org/presentationml/2006/main'

prs = Presentation(PPTX_PATH)
print(f"Total slides: {len(prs.slides)}")

prs_el = prs._element
extLst = prs_el.find(f'{{{PNS}}}extLst')
TARGET_URI = '{521415D9-36F7-43E2-AB2F-B90AF26B5E84}'
sec_lst = None
for ext in (extLst or []):
    if ext.get('uri') == TARGET_URI:
        sec_lst = ext.find(f'{{{P14}}}sectionLst')
        break

if sec_lst is not None:
    secs = list(sec_lst)
    print(f"Sections ({len(secs)}):")
    for sec in secs:
        n = len(list(sec.find(f'{{{P14}}}sldIdLst')))
        print(f"  {sec.get('name')!r}: {n} slides")
else:
    print("WARNING: No sections found!")

# Verify no "Public" label shapes remain
LABEL_PATTERN = re.compile(r'\bpublic\b', re.IGNORECASE)
label_found = 0
for slide in prs.slides:
    for shape in slide.shapes:
        try:
            if LABEL_PATTERN.fullmatch(shape.text_frame.text.strip()):
                label_found += 1
        except Exception:
            pass
if label_found:
    print(f"WARNING: {label_found} sensitivity label shape(s) still present!")
else:
    print("Sensitivity labels: all removed")
PYEOF
```

**PDF:**
- File exists at expected path
- Page count reported (expected >= slide count due to notes overflow)
- Header visible at top of page 1
- Bookmark count matches section count

Report any failures clearly before telling the user the workbook is complete.

---

## Common mistakes

1. **Wrong section names** — always extract from slide 1 programmatically; first module is always `Course Agenda`
2. **Trim run twice** — check first; running twice removes 4 slides instead of 2
3. **Bookmarks on wrong pages** — use proportional formula; never hardcode page numbers
4. **Header missing from PPTX** — expected; header is stamped onto PDF pages in Step 6 only
5. **File open during export** — close PowerPoint and PDF viewers before Steps 5 and 6
6. **Formatting distortion after merge** — stop immediately; do not attempt to fix; report to user
7. **Always use PowerPoint COM for merge (Step 3)** — Python-based PPTX ZIP manipulation drops embedded content-type entries, corrupting the output. COM copy/paste is the only safe approach.
