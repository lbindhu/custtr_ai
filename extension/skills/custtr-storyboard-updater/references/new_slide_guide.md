# New Slide Guide

## Authoring New Slides

This is the most important part of the skill. New slides must look like professional AMD training material â€” with real PowerPoint shapes, tables, and diagrams that an instructor can edit.

### Design Philosophy

Training material teaches through structure and visuals. A learner absorbs a concept when they see its architecture, understand where it fits, and connect it to prior knowledge. Text-only slides are outline notes formatted as slides, not training content.

Every new slide should answer: **"What will the learner see on screen that helps them understand this concept?"**

### Theme Color Extraction (MANDATORY â€” read before authoring any new slide)

**Never hardcode AMD brand colors in a new slide.** Every deck ships its own
`ppt/theme/theme1.xml`, and the palette varies â€” the AMD red used by the PCIE
storyboard deck is `#E20000`, while older training decks use `#ED1C24`, and
some newer decks use `#E4002B`. If you paint the new slide with a hardcoded
red (or worse, with python-pptx defaults like black and teal), the addition
will look like a foreign object dropped into the deck and the user will reject
it.

#### The rule

Before authoring any new-slide builder, extract the palette from the
**base deck** you are about to extend, then use those exact RGB values
in every shape fill, text color, and accent stripe.

#### How to extract

```python
import zipfile, re
with zipfile.ZipFile(base_deck_path) as z:
    theme = z.read('ppt/theme/theme1.xml').decode('utf-8', 'replace')
palette = dict(re.findall(
    r'<a:(\w+)>\s*<a:srgbClr val="([0-9A-Fa-f]{6})"/>',
    theme,
))
# palette now maps scheme-color names -> hex strings, e.g.
#   {'dk1':'0C0C0C','lt1':'FFFFFF','dk2':'161C2E','lt2':'5F5F5F',
#    'accent1':'E20000','accent2':'282D3F','accent3':'8D919A',
#    'accent4':'055C99','accent5':'0D9079','accent6':'00B2BA',
#    'hlink':'055C99','folHlink':'5F5F5F'}
```

`create_additions_deck.py` already does this via `_theme_palette.py` â€” but
that helper only gets used if the builder reads from it. **Any custom
slide-build script you write inside Phase 5B must do the same extraction.**

#### Standard color roles

Once you have the palette, map roles to scheme entries (do NOT invent
new colors):

| Role                           | Scheme key | Example for this deck |
|--------------------------------|------------|-----------------------|
| Brand accent / primary highlight | accent1  | `#E20000` (AMD red)   |
| Dark background / title bar      | dk2      | `#161C2E` (deep navy) |
| Secondary dark / card body       | accent2  | `#282D3F` (slate)     |
| Sub-accent / data lines          | accent4  | `#055C99` (blue)      |
| Tertiary accent / coherency      | accent5  | `#0D9079` (teal-green)|
| Neutral text / disabled          | accent3 / lt2 | `#8D919A`         |
| Body text                        | dk1      | `#0C0C0C`             |
| Inverted text (on dark fills)    | lt1      | `#FFFFFF`             |

Use the **brand accent sparingly** â€” title accent strip, bullet glyphs,
single-card stripe. The majority of card real estate is dark2/slate with
white text. Teal-green is reserved for one role (e.g. coherency / safety)
so the slide does not turn into a swatch chart.

#### Failure mode this prevents

A previous CPM6 PCIE addition was generated with python-pptx defaults:
black title bar, default teal table headers, white body. It read as a
generic stock PowerPoint slide and the user rejected the whole merge. The
fix was to re-extract the palette from `updated_base.pptx`, re-author the
slide with `#E20000` / `#161C2E` / `#055C99` / `#0D9079`, and re-merge â€”
producing a slide that matched the other 38 in the deck. The lesson:
**theme extraction is not optional, even for one-off custom builders.**

---

### Instructional Pattern Match (companion to the theme rule)

When adding a slide that parallels an existing teaching surface (e.g. a
new CPMn slide alongside slides for CPM4 and CPM5), match the existing
**pedagogical pattern**, not just the visual palette:

1. **Anchor the new content against what learners already saw.** A new
   CPM6 slide should open with a one-line sub-headline that names CPM5
   and CPM4 so learners place the new module on the timeline immediately.
2. **Mirror the depth.** If CPM4 has a block diagram and CPM5 has a block
   diagram, do not ship CPM6 as a four-bullet text slide. Either build a
   parallel diagram, or use a `cards` layout that delivers comparable
   teaching density (4 cards Ã— kicker + headline + lead + 3 bullets is
   a reasonable substitute when a published block diagram is not yet
   available for the new generation).
3. **Close with a cross-reference footer.** A short footer band ("CPM4
   on slides 15â€“16  Â·  CPM5 on slide 17  Â·  CPM6 here") tells the learner
   the new slide is the third beat in a sequence, not a one-off addition.

The yellow `New Slide` badge is still required and is applied
automatically â€” these rules govern the content underneath it.

### Available Slide Layouts

Six layouts are available, split across two rendering pipelines. MARP-eligible layouts (`comparison_table`, `cards`, `two_column`, `key_takeaway`) produce visually superior slides via the MARP + AMD theme pipeline. Diagram layouts (`ascii_diagram`, `block_diagram`) produce native PPT shapes via `create_additions_deck.py`. The plan JSON schema is identical for both â€” routing is automatic by `slide_layout` value. There is no generic `body` field â€” every layout has its own required data field. Unknown layout names and missing data fields are hard errors at every validation gate.

#### `comparison_table` â€” Side-by-side feature/spec comparison

Best for: APU vs RPU, version-over-version changes, protocol comparisons.

Produces a native PPTX table with a dark teal header row, alternating row shading, and white text. The table is fully editable in PowerPoint.

**Plan action data:**
```json
{
  "type": "add_new_slide",
  "slide_layout": "comparison_table",
  "title": "APU vs RPU: When to Use Each Processor",
  "table": {
    "headers": ["Criteria", "APU (Cortex-A72)", "RPU (Cortex-R5F)"],
    "rows": [
      ["Primary use case", "Linux, networking, AI inference", "Real-time control, safety"],
      ["Architecture", "Armv8-A (64-bit)", "Armv7-R (32-bit)"],
      ["Clock speed", "Up to 1.7 GHz", "Up to 600 MHz"],
      ["Memory", "32K L1 + 1MB L2 shared", "32K L1 + 256KB TCM"],
      ["OS support", "Linux, bare-metal", "FreeRTOS, bare-metal"],
      ["Determinism", "Best-effort (cache)", "Hard real-time (TCM)"],
      ["Safety", "N/A", "ASIL B/D (lockstep)"],
      ["Power domain", "Full Power Domain", "Low Power Domain"]
    ]
  },
  "learning_goal": "...",
  "why_this_slide_exists": "...",
  "what_customer_should_understand": "...",
  "speaker_notes": "... (150-300 words) ..."
}
```

#### `ascii_diagram` â€” Architecture diagram from ASCII art (preferred for diagrams)

Best for: system block diagrams, data flow, component relationships, protection architectures.

Design the diagram as ASCII box-drawing art. The `ascii_to_diagram.py` script automatically parses it into native PowerPoint shapes â€” rounded rectangles with connector lines, fully editable by the instructor. This is the natural way for you to design a spatial layout: draw the diagram with box-drawing characters, and the script handles coordinate mapping and rendering.

Use Unicode box-drawing characters (`â”Œ â” â”” â”˜ â”‚ â”€`) or ASCII equivalents (`+ - |`). Connect boxes with `â”‚` or `|` (vertical) and `â”€` or `-` (horizontal). Add arrowheads with `â–¼ â–² â–º â—„` or `v ^ > <`.

You can set box colors with a trailing comment on the top edge: `# color=gold`. Available colors: `teal` (default), `gold`, `red`, `dark`, `mid`, `black`.

**Plan action data:**
```json
{
  "type": "add_new_slide",
  "slide_layout": "ascii_diagram",
  "title": "PS Isolation Architecture",
  "ascii_art": "â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”     â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”\nâ”‚       APU       â”‚â”€â”€â”€â”€â–ºâ”‚  Interconnect   â”‚\nâ”‚   Cortex-A72    â”‚     â”‚     (CCI)       â”‚\nâ””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜     â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜\n                               â”‚\n                               â–¼\nâ”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”     â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”\nâ”‚       RPU       â”‚â”€â”€â”€â”€â–ºâ”‚       DDR       â”‚  # color=gold\nâ”‚   Cortex-R5F    â”‚     â”‚     Memory      â”‚\nâ””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜     â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜",
  "learning_goal": "...",
  "why_this_slide_exists": "...",
  "what_customer_should_understand": "...",
  "speaker_notes": "... (150-300 words) ...",
  "key_points": {
    "heading": "Key Specs",
    "bullets": [
      "APU: Cortex-A72 running Linux",
      "RPU: Cortex-R5F running RTOS",
      "CCI Interconnect: cache-coherent bridge",
      "DDR: shared memory subsystem"
    ]
  }
}
```

The `key_points` field renders a right-side dark panel with 4-6 visible bullet points. This is required for narrated storyboards — the instructor needs on-screen text to reference during delivery. **Key points and speaker notes must stay in sync**: every bullet must be elaborated in the notes, and the notes must not teach concepts absent from both the key_points and the diagram labels (Rule 34).

**Tips for good ASCII diagrams:**
- Keep boxes the same width within a tier for visual consistency
- Use 2+ character gaps between boxes so connectors are visible
- Put the primary component at top-left; data/control flows downward or rightward
- Add a sublabel on the second line inside each box (e.g., "Cortex-A72" under "APU")
- Use `# color=gold` hints to distinguish secondary or protection components
- Nested boxes (a large box containing smaller ones) are detected automatically as containers

**Advanced features (all optional, backward-compatible):**
- **`[[id]]` emphasis** â€” wrap a box label in double brackets to make it visually emphasized (heavier border + accent fill). Example: `[[CPM6]]`.
- **Line styles** â€” use `â•` (or `=`) for bold/wide connectors, `â•Œ` (or `.`) for dashed connectors, `â”€`/`-` for the default thin style.
- **Edge labels** â€” free text within 2 cells of a connector path becomes the connector's label. Example: `APU â”€â”€PCIeâ”€â”€â–º NoC`.
- **Bent routes** â€” drop a `+` corner on a connector to introduce a 90-degree bend. Example: `A â”€â”€+`<br>`     â”‚`<br>`     â–¼`<br>`     B`.
- **Bidirectional connectors** â€” arrowheads on both ends (`â—„â”€â”€â”€â–º`) render as a single bidirectional arrow.
- **Column-drift tolerance** â€” body-row arrows like `â”€â”€â”€â–ºâ”‚` that shift downstream chars by 1-2 columns are handled automatically; you no longer need pixel-perfect alignment.
- **Soft-fail** â€” if the parser can't make sense of the art, it logs to stderr and the slide falls back to the `block_diagram` layout instead of crashing.

See `references/ascii_diagram_guideline.md` for the full syntax reference and `references/ascii_examples/` for working fixtures (chain, group, bidirectional+labeled, emphasized).

#### `block_diagram` â€” Architecture boxes with JSON coordinates (fallback)

Use this only when you need pixel-precise control over box positioning. For most diagrams, prefer `ascii_diagram` â€” it's faster and more natural.

Produces native PowerPoint rounded-rectangle shapes with connector lines. Each box has a label and optional sublabel. Boxes are positioned using inch coordinates (0,0 is top-left).

Available box colors: `teal`, `gold`, `red`, `dark`, `mid`, `black`.

**Plan action data:**
```json
{
  "type": "add_new_slide",
  "slide_layout": "block_diagram",
  "title": "PS Isolation Architecture",
  "diagram": {
    "boxes": [
      {"id": "apu", "label": "APU", "sublabel": "Cortex-A72 (Linux)", "x": 1.0, "y": 1.5, "w": 3.0, "h": 1.2, "color": "teal"},
      {"id": "rpu", "label": "RPU", "sublabel": "Cortex-R5F (RTOS)", "x": 5.5, "y": 1.5, "w": 3.0, "h": 1.2, "color": "gold"}
    ],
    "connectors": [
      {"from": "apu", "to": "rpu"}
    ]
  },
  "learning_goal": "...",
  "why_this_slide_exists": "...",
  "what_customer_should_understand": "...",
  "speaker_notes": "... (150-300 words) ...",
  "key_points": {
    "heading": "Key Specs",
    "bullets": [
      "APU: Cortex-A72 (Linux domain)",
      "RPU: Cortex-R5F (RTOS domain)",
      "AXI interconnect between domains",
      "Isolation via XMPU/XPPU"
    ]
  }
}
```

The `key_points` field renders a right-side dark panel with 4-6 visible bullet points. This is required for narrated storyboards — the instructor needs on-screen text to reference during delivery. **Key points and speaker notes must stay in sync**: every bullet must be elaborated in the notes, and the notes must not teach concepts absent from both the key_points and the diagram labels (Rule 34).

#### `two_column` â€” Left/right content areas

Best for: before/after comparisons, concept vs detail, old vs new architecture.

**Plan action data:**
```json
{
  "type": "add_new_slide",
  "slide_layout": "two_column",
  "title": "APU vs RPU: Design Considerations",
  "columns": [
    {
      "heading": "APU (Application Processing)",
      "bullets": [
        "Arm Cortex-A72/A78AE cores",
        "Runs Linux, hypervisors",
        "Cache-based memory (L1/L2)",
        "Best-effort scheduling",
        "Full Power Domain (FPD)"
      ]
    },
    {
      "heading": "RPU (Real-Time Processing)",
      "bullets": [
        "Arm Cortex-R5F/R52 cores",
        "Runs FreeRTOS, bare-metal",
        "TCM-based memory (deterministic)",
        "Hard real-time guarantees",
        "Low Power Domain (LPD)"
      ]
    }
  ],
  "learning_goal": "...",
  "why_this_slide_exists": "...",
  "what_customer_should_understand": "...",
  "speaker_notes": "... (150-300 words) ..."
}
```

#### `key_takeaway` â€” Bold centered statement

Best for: critical learning points, section transitions, key design principles.

**Plan action data:**
```json
{
  "type": "add_new_slide",
  "slide_layout": "key_takeaway",
  "title": "Key Design Principle",
  "statement": "Use the APU for application workloads and the RPU for real-time control â€” most Versal designs use both.",
  "subtext": "The cache-coherent interconnect enables efficient data sharing between the two processor clusters.",
  "learning_goal": "...",
  "why_this_slide_exists": "...",
  "what_customer_should_understand": "...",
  "speaker_notes": "... (150-300 words) ..."
}
```

---

## New-Slide Quality Bar â€” "Slide-18 Standard"

Every `add_new_slide` action of type `block_diagram` / `ascii_diagram` / `comparison_table` is held to the visual quality bar defined below. This is non-negotiable: a new slide that doesn't meet this bar fails plan review.

### Required elements â€” block / architecture diagrams

1. **Grouped colored regions** with semi-transparent backgrounds delineating logical zones (e.g. CPM6 / PS / Fabric / Off-chip). Each region carries a label.
2. **Component boxes** for each functional block, each with:
   - A title (e.g. "PCIe Gen 6 Controller")
   - A one-line role descriptor (e.g. "x8 @ 64 GT/s, root/endpoint")
   - Optional small icon or count badge
3. **Annotated connectivity arrows** between blocks. Every arrow labelled with the protocol carried (AXI4-MM, AXI-ST, CXL.io / .cache / .mem, PCIe, AXI-Lite). Bidirectional arrows where applicable.
4. **Side panel** (right column) â€” populated via the `key_points` field on the plan action. 4-6-bullet “Key Specs” or “What's New” list. Concise, scannable. Must stay in sync with speaker notes (Rule 34).
5. **Source / scope footer** in 8-pt grey â€” source attribution (e.g. "Source: CPM6 Webinar Slides S3; AMD docs.amd.com PG346 v3.x"). Required.
6. **AMD palette only** â€” primary AMD red `#ED1C24` for highlight regions, slate `#3F4451` for neutral fills, light grey `#F2F2F2` for backgrounds, white text on red, dark text on light.
7. **Typography** â€” title 24-28 pt bold; block titles 12-14 pt semibold; body 10-11 pt regular; footer 8 pt.
8. **Layout discipline** â€” 16:9, ~0.5" margins, grid-aligned blocks, no overlapping shapes, orthogonal arrows where possible.

### Required elements â€” comparison tables

- 3 columns minimum (Aspect / Option A / Option B â€” e.g. CPM5 vs CPM6), zebra striping.
- Header row in AMD red, white bold text.
- Concrete values per row (rates, lane counts, protocol versions, channel counts). No marketing fluff.
- Footnote row citing source.
- Same palette and typography as diagrams.

### Linter

`create_additions_deck.py` (or a companion linter) must verify each new slide has at minimum:
- A title shape.
- A source-attribution footer.
- >=1 grouped region (for block diagrams) or >=1 table (for comparison slides).
- The yellow "New Slide" badge in the top-right corner.

A new slide missing any of these fails the quality check and blocks merge.

#### `cards` â€” Info cards (default fallback)

Best for: introducing multiple related concepts, feature overviews. This is the default if `slide_layout` is omitted.

**Plan action data:**
```json
{
  "type": "add_new_slide",
  "slide_layout": "cards",
  "title": "PS Isolation Mechanisms",
  "cards": [
    {"heading": "XMPU", "bullets": ["Memory protection unit", "Controls DDR and OCM access per master"]},
    {"heading": "XPPU", "bullets": ["Peripheral protection unit", "Gate access to PS/PL peripherals"]},
    {"heading": "SMMU", "bullets": ["System MMU for DMA", "Translates and isolates DMA transactions"]}
  ],
  "learning_goal": "...",
  "why_this_slide_exists": "...",
  "what_customer_should_understand": "...",
  "speaker_notes": "... (150-300 words) ..."
}
```

> **Cards require a non-empty `cards` array with domain-specific headings.** There is no auto-generation fallback. If `cards` is missing or empty, the rendering pipeline raises a hard error. Headings like "What it is", "Why it matters", "Customer value", "Overview", or "Benefits" are rejected by `audit_gate.py` â€” use headings specific to the concepts being taught (e.g., "XMPU", "XPPU", "SMMU" as shown above).

### Choosing the Right Layout

| Content type | Layout | Pipeline | Why |
|---|---|---|---|
| Feature/spec comparison (>=3 rows) | `comparison_table` | MARP | Styled table with teal headers, fully editable |
| System architecture, data flow | `ascii_diagram` | Script | Draw the layout naturally; auto-converts to native PPT shapes |
| Precise pixel-positioned diagram | `block_diagram` | Script | JSON coordinates for exact placement (fallback) |
| Two-thing comparison (deep bullets) | `two_column` | MARP | Side-by-side columns with AMD-branded styling |
| Critical learning point | `key_takeaway` | MARP | Centered bold statement with teal accent |
| Multiple related concepts (overview) | `cards` | MARP | Styled card layout with bold headings and bullets |

### What to Avoid

- **Raw MARP for diagrams.** MARP cannot produce draggable native PPT shapes. Use `ascii_diagram` or `block_diagram` layouts (routed to `create_additions_deck.py`) for architecture diagrams and data-flow visuals. MARP is the correct pipeline for tables, cards, two-column, and key-takeaway layouts.
- **Generic "What/Why/Value" cards.** If the plan has `cards` with headings like "What it is" / "Why it matters", stop and choose a better layout. Those headings are a sign that the content needs a table, diagram, or two-column comparison instead.
- **Wall of bullets.** If a slide has 8+ bullets, restructure it as a table or cards.
- **Missing visuals.** Every slide should have a visual structure â€” table, diagram, two-column layout, or cards. Plain title + bullets is not a training slide.
- **Non-existent layout names.** Using `"slide_layout": "title_and_content"` or any name not in the six valid layouts is a hard error. There is no silent fallback.
- **The `body` field.** No layout consumes a `body` field. Every layout has its own data field (`table`, `diagram`, `ascii_art`, `columns`, `statement`, `cards`). Using `body` is a hard error.
- **Glossary-style bullets.** A bullet that reads `"Term: one-line definition"` belongs in a glossary, not a training slide. Training bullets include at least one of: a comparison, a condition, a consequence, or a concrete metric.

### Training Content vs. Datasheet Content

New slides must teach, not inventory. The difference:

| Aspect | Datasheet (don't) | Training (do) |
|---|---|---|
| **Headings** | "What it is" / "Why it matters" / "Customer value" | Domain-specific: "XMPU", "XPPU", "SMMU" or "Protocol Comparison", "Bandwidth Impact" |
| **Bullets** | `AES-GCM: Authenticated encryption with associated data` | `Use AES-GCM when your application needs both confidentiality and integrity in a single pass â€” preferred for network workloads where separate MAC computation would halve throughput` |
| **Structure** | Flat feature inventory â€” every item at the same depth | Contextual hierarchy â€” each point builds on the prior or contrasts with a peer |
| **Learner test** | Sounds like a glossary entry read aloud | Sounds like an instructor explaining to a colleague |

**Self-test before submitting a plan:** Read each bullet aloud. If it sounds like a glossary entry, rewrite it. A training bullet contains at least one of: a comparison, a condition, a consequence, or a concrete metric.

### Hard Schema Constraints

Every validation layer enforces the same constraints. No silent fallback, no auto-generation.

| Layout | Required data field | Notes |
|---|---|---|
| `comparison_table` | `table` | `{headers: [...], rows: [[...]]}` |
| `block_diagram` | `diagram` | `{boxes: [...], arrows: [...]}` |
| `block_diagram` | `key_points` | `{heading?: string, bullets: string[]}` (recommended â€" renders side panel) |
| `ascii_diagram` | `ascii_art` | Multi-line string |
| `ascii_diagram` | `key_points` | `{heading?: string, bullets: string[]}` (recommended â€" renders side panel) |
| `two_column` | `columns` | `[{heading, bullets}, {heading, bullets}]` â€” minimum 2 columns |
| `key_takeaway` | `statement` | Non-empty string |
| `cards` | `cards` | `[{heading, bullets}]` â€” minimum 2 cards, domain-specific headings |

Using any other `slide_layout` value or the `body` field produces a hard error in `validate_plan.py`, `audit_gate.py`, `create_additions_deck.py`, and `create_marp_additions.py`.

---

## Narrative Notes

Speaker notes are not an afterthought â€” they are the instructor's script. Every slide in a training storyboard has narration that an instructor reads or uses as a guide.

### What good narration looks like

Study the existing deck's notes to match its style. Most AMD storyboard narration follows this pattern:

1. **Orient** â€” Tell the learner what they're about to see: "On this slide, we'll look at..."
2. **Walk the slide** â€” Explain each visual element or bullet in order, top-to-bottom or left-to-right
3. **Connect** â€” Explain why this matters: what problem it solves, what it enables, how it relates to the previous slide
4. **Caveats** â€” Note any limitations, version-specific behavior, or "watch out for" items
5. **Transition** â€” Bridge to the next slide: "Now that we understand X, let's see how Y..."

### Minimum requirements

- **New slides:** Full narration (150-300 words) covering orient, walk, connect, and transition
- **Updated slides:** Update narration to reflect the changed content
- **Knowledge checks:** Narrate the correct answer and explain why distractors are wrong
- **Title slides, Objectives slides, and Summary slides:** No speaker notes required. Leave these slides' notes empty or unchanged â€” do not generate or modify narration for them.

### Anti-patterns

- Empty speaker notes on a new slide
- Copy-pasting the slide's visible text into the notes
- One-sentence notes like "This slide covers the processing system"
- Notes that don't reference the visual elements on the slide

---

## How to Express Actions in `update_plan.json`

Use these action types:

- `update_existing`: change text/notes on an existing slide.
- `remove_or_deprecate`: omit obsolete slide(s) from final merge or mark content obsolete.
- `add_new_slide`: create new content in a generated additions deck.
- `knowledge_check_update`: update a quiz/feedback slide after new instructional content.
- `notes_update`: update narration only.

Each action should include:

- `slide_number` or `insert_after_slide`
- `reason`
- `source_basis`
- `visible_text`
- `speaker_notes` (full narration â€” see "Narrative Notes" above)
- `marking`: `existing_edit` or `new_slide_badge`

For `add_new_slide`, the plan must also include:

- `slide_layout`: one of `ascii_diagram`, `comparison_table`, `block_diagram`, `two_column`, `key_takeaway`, `cards`
- Layout-specific data: `ascii_art`, `table`, `diagram`, `columns`, `statement`/`subtext`, or `cards` (see "Authoring New Slides")
- `learning_goal`
- `why_this_slide_exists`
- `what_customer_should_understand`
- `speaker_notes`: full narration (150-300 words)
- `connects_from_slide`
- `connects_to_slide`

For major new concepts, the plan must include dependent actions for objectives, summary, and the nearest relevant knowledge check.

## Instructional Design Bar

New slides must be designed as training content, not placeholders.

### Acceptable slide patterns

| Pattern | Layout | Description |
|---|---|---|
| Architecture diagram | `ascii_diagram` | ASCII art auto-converted to native PPT shapes and connectors |
| Feature comparison | `comparison_table` | Native table comparing specs, options, or versions |
| Before/after comparison | `two_column` | Old approach vs new approach side by side |
| Decision guide | `comparison_table` | When to use each option (table format) |
| Concept overview | `cards` | 2-4 cards introducing related concepts |
| Key takeaway | `key_takeaway` | Single critical learning point |
