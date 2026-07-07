# custtr-storyboard

**Customer Training Storyboard — 4-Phase Engine**

Transforms raw AMD Content Development (CD) PowerPoint decks into instructionally sound, brand-compliant storyboards ready for eLearning development.

---

## Invoke

```
/custtr-storyboard
```

Attach a `.pptx` file to process an existing deck (Mode A), or run without a file to build from a topic outline or context (Mode B).

---

## Modes

| Mode | When | Description |
|---|---|---|
| **Mode A — Enrich/Transform** | `.pptx` attached | Reads source deck, runs full 4-phase pipeline |
| **Mode B — Build from Context** | No file attached | Collects course info via intake, sources content, then runs same pipeline |

---

## Pipeline

### Phase 0 — Classification Gate
Scans the file for an AMD `[Public]` label before any content is read. Hard-stops on Internal, Confidential, NDA, or Restricted content. Prompts for user confirmation if no label is found.

### Phase 1 — Analyze
Produces a diagnostic report across 7 groups:

- **Deck Overview** — slide count, content classification, orphan detection
- **Learning Design** — LO coverage, Bloom's Taxonomy, constructive alignment, sequencing
- **Knowledge Checks** — quality audit of existing KCs
- **Content Quality** — internal consistency, redundancy
- **Presentation Quality** — OST/VO state, brand violations
- **Structural Completeness** — mandatory slide presence check
- **Learner Experience** — cognitive load / concept density

Outputs:
- `[filename]_Phase1_Review.pptx` — working copy with findings annotated in slide notes
- `[filename]_Phase1_Report.docx` — full diagnostic report with scorecard

### Phase 2 — Transform
Builds a Transformation Table (one row per slide) with actions: Keep, Rewrite, Split, Merge, Re-sequence, Insert, Flag for Removal. Auto-resolves all Phase 1 Critical findings using ID principles. Sources content for identified gaps via Confluence, Vivado Doc Search, and Web Search.

### Phase 3 — Build + Design
Generates the final storyboard PPTX:

- `[filename]_Phase3_SB.pptx` — content blueprint with full notes pane
- `[filename]_Phase3_SB_DESIGNED.pptx` — fully designed output with visible OST

Built using the AMD Corporate Template (`layout[27]` blank) with all rectangles drawn before textboxes to ensure correct z-order rendering.

---

## Output Files

| File | Phase | Contents |
|---|---|---|
| `[name]_Phase1_Review.pptx` | 1 | Source copy with findings in slide notes |
| `[name]_Phase1_Report.docx` | 1 | Full diagnostic report |
| `[name]_Phase3_SB.pptx` | 3 | Storyboard blueprint |
| `[name]_Phase3_SB_DESIGNED.pptx` | 3 | Designed storyboard ready for developer handoff |

All files are saved to the same folder as the source input.

---

## Requirements

- Source file must be classified **AMD Public**
- Python 3.12 with `python-pptx` installed at `C:\Users\mvlbnimi\AppData\Local\Programs\Python\Python312\`
- AMD Corporate Template at `C:\Users\mvlbnimi\.psas-ai\slai-installs\.claude\skills\amd-pptx-template\assets\AMD_Corp_Template_2_13_2026.pptx`
- Reference SB library at `C:\Users\mvlbnimi\.psas-ai\shared\sb_analysis\`
- Phase 3 builder at `C:\Users\mvlbnimi\.psas-ai\shared\build_designed_CONFIRMED.py`

---

## Version

`1.0` — see [version.txt](version.txt)
