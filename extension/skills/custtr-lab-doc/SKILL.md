---
name: custtr-lab-doc
description: >
  Generates AMD-style hands-on lab documents(.docm) that match the AMD training lab template structure and Word styles

---

# AMD Lab Document Generator

This skill produces `.docm` lab files that exactly match the AMD training lab
template — the same paragraph styles, document structure, and layout. It works
for **any AMD product or tool**: Vivado, Vitis, PetaLinux, ROCm, XDMA, Versal,
Zynq, and more.

**All technical content must come from AMD's knowledge base first** — not from
training data. The retrieval step is mandatory and runs before any content is
drafted.

## References folder — bundled knowledge base

All reference files are in:
```
%USERPROFILE%\.claude\skills\custtr-lab-doc\references\
```

| File | Purpose |
|---|---|
| `amd_lab_template.docm` | Real AMD Word template — source of styles and layout |
| `amd_github_repos.md` | AMD/Xilinx GitHub repos mapped to topics and lab content |
| `amd_vitis_tutorials.md` | Vitis tutorial knowledge base (commands, flows, boards) |
| `amd_technical_portals.md` | AMD docs portal URLs and search patterns |
| `snagit_best_practices.md` | Snagit annotation standards, arrow colors, blur rules |
| `lab_development_best_practices.md` | Lab writing standards, hierarchy rules, naming conventions |

**Read `snagit_best_practices.md` and `lab_development_best_practices.md` for every lab** — they define mandatory rules for screenshot quality, annotation colors, step writing style, question placement, and file naming.

## Base directory

```
%USERPROFILE%\.claude\skills\custtr-lab-doc\
```

## References folder

The skill is self-contained. The AMD lab template is bundled in:

```
%USERPROFILE%\.claude\skills\custtr-lab-doc\references\amd_lab_template.docm
```

**Always use this bundled template** — do not reference any external path. This
ensures the skill works for the customer training team regardless of what files
are installed on their machine.

This file is used **only** to extract Word namespace declarations and page
layout (sectPr) from its `document.xml`. All content is replaced — nothing
from the original lab carries over into the output.

## Word styles used (do not invent new ones)

Verified against real AMD lab reference files in C:\SET2\F3\Lab Docs\.

| Style name | Purpose |
|---|---|
| `SuperTitle` | Invisible cover block above title (empty paragraph) |
| `Title` | Large cover title, Arial bold 18pt, centered |
| `Version` | Empty placeholder on cover (version appears in Sub-title, not here) |
| `Byline` | 3× empty paragraphs on cover page |
| `TOCTitle` | "Table of Contents" |
| `TOC1` | TOC entry with right-tab page number |
| `Heading1` | "Lab N:  Title" — Arial 22pt, centered |
| `Sub-title` | Version string (e.g. "2026.1") — Arial bold 12pt, immediately after Heading1 |
| `AllowPageBreak` | Invisible 1pt spacer between major sections (NOT a page break) |
| `Heading2` | Section headers: Abstract, Objectives, Introduction, etc. — Arial 16pt |
| `BodyText` | Standard body paragraphs — Arial 11pt |
| `General` | Context text within step sections — Arial 13pt |
| `ListBullet` | Objectives bullet list |
| `ListContinue` | Plain continuation after a step (no indent change) |
| `ListContinue2` | Code/path/image continuation after sub-steps — monospace or plain |
| `LabListNumber1` | Primary numbered steps — SEQ field prefix Segoe UI Bold 12pt, body text plain (not bold) |
| `LabListNumber1Continue` | Continuation paragraph of an L1 step (bold, no number) |
| `LabListNumber2` | Sub-steps — SEQ field prefix Segoe UI Bold 10pt, body text plain (not bold) |
| `LabListNumber2Bullet` | Bulleted sub-items inside a step — body text plain (not bold) |
| `Warning` | Note/Warning bordered box — use for Note: Important: Caution: |
| `TableBodyText` | Table cell body text |
| `TableBodyTextCenter` | Table header cells (centered) |
| `TableGrid` | Table border style (set on `<w:tblStyle>`) |
| `Caption` | Figure caption — auto-numbered as Figure N-M |
| `GeneralFlowSpacer` | Spacer after General Flow diagram |
| `QuestionHeading` | "Question N" — SEQ QNum field, Arial bold 12pt |
| `QuestionBody` | Question text body — Arial 11pt |
| `QuestionLine` | Underlined answer line (contains only `<w:tab/>`) |
| `QuestioninAnswerSection` | Question repeated in Answers section |
| `AnswerBody` | Answer text in Answers section |

**Critical implementation notes (verified from real docs):**
- `LabListNumber1` and `LabListNumber2` use **SEQ field codes**, NOT `w:numPr` list numbering
- Number prefix font is **Segoe UI Bold** (not Arial) — `w:rFonts w:ascii="Segoe UI Bold"`
- `LabListNumber2` prefix runs have `w:sz w:val="20"` (10pt); `LabListNumber1` prefix is 12pt (sz=24 from style)
- **Body text in `LabListNumber1`, `LabListNumber2`, and `LabListNumber2Bullet` must explicitly cancel bold** using `<w:b w:val="0"/>` in the run properties — the Word style definition is bold by default; without the override the body text renders bold
- Images use **VML format** (`<w:pict><v:shape><v:imagedata>`) — NOT DrawingML `<w:drawing>`
- `QuestionLine` has only `<w:tab/>` inside — underline is defined in the style itself
- `AllowPageBreak` is a 1pt invisible spacer, not a `<w:br w:type="page"/>`
- The version string is in `Sub-title` style, not `Version` style (Version is always empty)
- Both `LabListNumber1Continue` (bold) and `LabListNumber1ContinueNotBold` (plain) exist — use `lab1_continue_nb` key for plain cross-references/hints
- `TableandQuestionSpacer` style exists for spacing after questions near tables

---

## Question and Answer Rules (MANDATORY — verified from C:\SET2\F3\Lab Docs)

### Rule 1: Every step MUST have at least one question
Every lab step must include at least one `question` instruction. Questions are placed **inline within the step flow** — immediately after the numbered step instruction they relate to, before the next step continues. Do NOT group all questions at the end of a step.

### Rule 2: Exact question placement pattern
```
LabListNumber1 — 1-3. Open the uart_rx.xpr project.
  QuestionHeading — Question 1         ← immediately after the relevant step
  QuestionBody    — What files are in the project? Are these sufficient?
  QuestionLine    — (empty underlined line)
  QuestionLine    — (empty underlined line)
  QuestionLine    — (empty underlined line)
LabListNumber1 — 1-4. Implement the design.  ← next step continues normally
```

### Rule 3: Always 3 QuestionLine paragraphs per question
Each question always has exactly **3 QuestionLine** paragraphs after it — these are the student's answer lines. Use `"answer_lines": 3` (default, so can be omitted).

### Rule 4: Questions must be thought-provoking and relevant
Questions should ask the student to observe, analyse, or predict something based on the step they just completed:
- After opening a project: "What files are in the project?"
- After running synthesis: "What resources are used? Is this expected?"
- After marking nets: "How many nets are marked for debug? What do they represent?"
- After capturing waveform: "What does the waveform show? What does it tell you about the design?"
- After a trigger fires: "What should be the next step to diagnose the problem?"

### Rule 5: All answers collected in the Answers section
At the end of the lab (after Summary), add a `Heading2 "Answers"` section. Every question must have a corresponding answer entry using `QuestioninAnswerSection` + `AnswerBody`. Use the `answers` array in the config — one entry per question, in the same order.

### Config pattern for questions and answers
```json
{
  "steps": [
    {
      "title": "Open the Synthesized Design",
      "instructions": [
        {"action": "Open the uart_led.xpr project."},
        {
          "question": "What files are in the project? Are these sufficient to build a project? Why or why not?",
          "answer_lines": 3
        },
        {"action": "Click Run Implementation in the Flow Navigator."}
      ]
    }
  ],
  "answers": [
    {
      "question": "What files are in the project? Are these sufficient to build a project? Why or why not?",
      "answer": "You can view the source files by selecting the Sources window. The project contains an EDF netlist and an XDC constraints file. These are sufficient — the EDF provides the synthesized netlist and the XDC provides pin assignments and timing constraints needed for implementation."
    }
  ]
}
```

---

## Workflow

### Step 1 — Read best practices files + Query the AMD knowledge base (MANDATORY, always first)

Before drafting any content, read these two reference files:
```
%USERPROFILE%\.claude\skills\custtr-lab-doc\references\snagit_best_practices.md
%USERPROFILE%\.claude\skills\custtr-lab-doc\references\lab_development_best_practices.md
```
These define mandatory rules for screenshot quality, annotation standards, step writing style, hierarchy, question placement, and file naming. Apply them throughout the lab.

Before drafting any content, query AMD's knowledge base to retrieve accurate
technical information for the lab topic. This ensures every command, version
number, prerequisite, expected output, and troubleshooting tip is grounded in
real AMD documentation — not guessed from training data.

#### Knowledge source priority order

Query ALL sources before drafting content. Use results in this strict priority:

1. **GitHub Xilinx (https://github.com/Xilinx)** — FIRST. Fetch the actual tutorial/lab page for the topic. Exact commands, file paths, board names, and flows come verbatim from here.
2. **Vivado AI Assistant RAG** — for Vivado, Vitis, and all AMD FPGA/tool topics (TCL syntax, design flow steps, known issues)
3. **AMD Technical Information Portal (docs.amd.com)** — official UG/PG documents for all products
4. **Nabu** — AMD internal docs, product specs, topics not covered above
5. **WebSearch on AMD docs** — to fetch full page content from portal URLs

Read the portal reference file at the start of every lab to know which URL to target:

```
%USERPROFILE%\.claude\skills\custtr-lab-doc\references\amd_technical_portals.md
```

---

#### Source 0: GitHub Xilinx Repositories — PRIMARY TECHNICAL SOURCE

**https://github.com/Xilinx** is the FIRST source to query for every lab. Before querying any other source, fetch the content of the relevant repository for the lab topic. This ensures all commands, file paths, prerequisites, board names, and lab flows are grounded in the actual AMD/Xilinx source material.

**How to use:**

1. Identify the correct repository from `references/amd_github_repos.md` based on the lab topic.
2. Fetch the README and relevant lab/tutorial page from GitHub:
   ```
   WebFetch("https://raw.githubusercontent.com/Xilinx/<repo>/main/README.md")
   WebFetch("https://xilinx.github.io/<repo>/<lab-page>.html")
   ```
3. Extract **verbatim**: exact commands, file paths, board names, tool versions, prerequisites, expected outputs.
4. For images: check the repository's `docs/` or `images/` folder for screenshots embedded in the tutorial pages. Use these as the reference for what the UI should look like, then find the matching image in `T:\Graphics_Repository\` using `find_images.py`.

**Key repositories (full details in `references/amd_github_repos.md`):**

| Lab Topic | Repository URL |
|---|---|
| Vivado FPGA flow, synthesis, ILA debug | https://github.com/Xilinx/xup_fpga_vivado_flow |
| Advanced Vivado, Versal NoC, DFX | https://github.com/Xilinx/Vivado-Design-Tutorials |
| Embedded Zynq PS/PL, Vitis, custom IP | https://github.com/Xilinx/xup_embedded_system_design_flow |
| HLS C-to-RTL, optimization | https://github.com/Xilinx/xup_high_level_synthesis_design_flow |
| Formal embedded tutorials (Zynq-7000, ZynqMP, Versal) | https://github.com/Xilinx/Embedded-Design-Tutorials |
| AI Engine, acceleration, platform creation | https://github.com/Xilinx/Vitis-Tutorials |
| All Xilinx/AMD repos | https://github.com/Xilinx |

**Image sourcing from GitHub:**
- When a lab is built from a GitHub tutorial, the images in that tutorial's documentation pages show the exact UI steps the student will see.
- Identify the screenshots shown in the GitHub tutorial page (via WebFetch of the docs site).
- Then search `T:\Graphics_Repository\` using `find_images.py` to find the matching AMD-approved screenshot.
- The GitHub tutorial image tells you WHAT to show; the Graphics Repository provides the APPROVED version to embed.
- Reference: `references/amd_github_repos.md` → GitHub → Graphics Repository image mapping table.

---

#### Source 1: Image Database (ALWAYS check before fetching from internet)

The AMD Graphics Repository is the primary image source for all labs. It contains **15,052 images** across all AMD training topics:

```
T:\Graphics_Repository\
```

The builder accesses this directly — no copying needed. Reference images in the config using the path **relative to `T:\Graphics_Repository\`**:

```json
{"image": "F4/ILA Dashboard.png", "caption": "ILA Default Dashboard"}
{"image": "Tool-Specific Graphics/VivadoDS/Opening the Hardware Manager from an Open Project [2017.1].png", "caption": "Opening the Hardware Manager"}
{"image": "Boards/KCU105.png", "caption": "KCU105 Evaluation Board"}
```

**Repository structure — 15,052 images total:**

| Sub-folder | Image count | Contents |
|---|---|---|
| `F1\` | 10,301 | Basic design analysis, IP, timing, power — all Vivado DS course screenshots |
| `x86Topics\` | 944 | x86 / software topics |
| `Japanese_Graphics\` | 1,958 | Japanese-language versions of all graphics |
| `Tool-Specific Graphics\` | 1,215 | Vivado, Vitis, HLS, PetaLinux, SDK, XSCT tool screenshots |
| `Boards\` | 213 | Board photos — KCU105, ZCU102, VCK190, KV260, etc. |
| `3D-2D Graphics\` | 278 | Architecture diagrams and block diagrams |
| `Logos\` | 69 | AMD, Xilinx, product logos |
| `Devices\` | (in F1) | Device die photos and architecture diagrams |
| `F3\` | 1 | Debug flow — Summary of Debug Nets |
| `F4\` | 7 | ILA Dashboard, debug nets, JTAG, schematic, connectivity |
| `ROCm\` | 11 | ROCm software stack screenshots |

**How to find images before writing the config (MANDATORY before each step):**

Use the `find_images.py` search helper — it queries the pre-built index of all 15,052 images instantly:

```bash
python "%USERPROFILE%/.claude/skills/custtr-lab-doc/scripts/find_images.py" hardware manager
python "%USERPROFILE%/.claude/skills/custtr-lab-doc/scripts/find_images.py" ILA dashboard
python "%USERPROFILE%/.claude/skills/custtr-lab-doc/scripts/find_images.py" synthesis complete
python "%USERPROFILE%/.claude/skills/custtr-lab-doc/scripts/find_images.py" netlist debug
python "%USERPROFILE%/.claude/skills/custtr-lab-doc/scripts/find_images.py" mark debug nets
python "%USERPROFILE%/.claude/skills/custtr-lab-doc/scripts/find_images.py" KCU105 board
```

Run a search for **every step** before writing the config. If results are returned, use the best match. Only leave a step image-free if the search returns nothing relevant.

**Image resolution order in the builder:**
1. `%USERPROFILE%\.claude\skills\custtr-lab-doc\images\<filename>` — flat images folder (hand-picked)
2. `T:\Graphics_Repository\<path>` — live access to the full repository
3. Absolute path — fallback

**Rule: Every step that shows a UI action MUST have an image. Never leave a step image-free if a matching screenshot exists in the repository.**

---

### GitHub → Graphics Repository Image Mapping (MANDATORY)

When generating a lab from a GitHub repository, images MUST be sourced from the corresponding topic folder in the Graphics Repository — not from unrelated folders. Search within the mapped folder first before broadening the search.

| GitHub Repository / Topic | Primary image folder in `T:\Graphics_Repository\` |
|---|---|
| `xup_fpga_vivado_flow` — Lab 1–3 (design flow, synthesis, implementation) | `F1/Topic Clusters/F1/` and `F1/Topic Clusters/F2/` |
| `xup_fpga_vivado_flow` — Lab 4 (IP Catalog, IP Integrator) | `F1/Topic Clusters/Driving_IPI/` and `F1/Topic Clusters/Vivado-IPI/` |
| `xup_fpga_vivado_flow` — Lab 5 (XDC, I/O Planning) | `Tool-Specific Graphics/VivadoDS/` |
| `xup_fpga_vivado_flow` — Lab 6 (ILA hardware debug) | `F1/Topic Clusters/F3/` and `F1/Topic Clusters/Debugging/` |
| `Vivado-Design-Tutorials` — Versal NoC / DDRMC | `F1/Topic Clusters/NoCddr/` and `F1/Topic Clusters/Versal NoC/` |
| `Vivado-Design-Tutorials` — DFX | `F1/Topic Clusters/DFX/` and `F1/Topic Clusters/DFX IP Integrator/` |
| `Vivado-Design-Tutorials` — Versal architecture | `F1/Topic Clusters/Versal_ACAP/` and `F1/Topic Clusters/Versal-Arch/` |
| `xup_embedded_system_design_flow` — Zynq PS/PL, AXI IP | `F1/Topic Clusters/AXI/` and `F1/Topic Clusters/AXI_bldgPeriph/` |
| `xup_embedded_system_design_flow` — Custom IP, IP Packager | `F1/Topic Clusters/Building Custom AXI IP/` |
| `xup_embedded_system_design_flow` — Vitis software dev | `Tool-Specific Graphics/VUIDE/` and `Tool-Specific Graphics/Vitis/` |
| `xup_embedded_system_design_flow` — Booting | `F1/Topic Clusters/Booting/` and `F1/Topic Clusters/basicBooting/` |
| `xup_high_level_synthesis_design_flow` — HLS design flow | `Tool-Specific Graphics/VitisHLS/` and `F1/Topic Clusters/HLS/` |
| `Embedded-Design-Tutorials` — Zynq-7000 EDT | `F1/Topic Clusters/F1/` and `F1/Topic Clusters/Zynq [advanced]/` |
| `Embedded-Design-Tutorials` — ZynqMP EDT | `F1/Topic Clusters/MPSoC_Overview/` and `F1/Topic Clusters/MPSoC_Ecosystem/` |
| `Embedded-Design-Tutorials` — Versal ACAP EDT | `F1/Topic Clusters/Versal_ACAP/` |
| `Embedded-Design-Tutorials` — MicroBlaze | `F1/Topic Clusters/ArchMicroBlazeV/` and `MicroBlaze RISC-V Graphics/` |
| `Embedded-Design-Tutorials` — Software debug | `F1/Topic Clusters/Debugging/` and `F1/Topic Clusters/SystemDebugger/` |
| `Embedded-Design-Tutorials` — FSBL | `F1/Topic Clusters/FSBL Debugging/` |
| `Vitis-Tutorials` — AI Engine | `F1/Topic Clusters/Versal_AIE/` |
| `Vitis-Tutorials` — HLS / acceleration | `Tool-Specific Graphics/VitisHLS/` and `F1/Topic Clusters/Vitis Accelerator/` |
| `Vitis-Tutorials` — Vitis Model Composer | `F1/Topic Clusters/Vitis_Model_Composer/` |
| Any Vivado debug lab (ILA, netlist insertion, IPI debug) | `F1/Topic Clusters/F3/`, `F1/Topic Clusters/F4/`, `F1/Topic Clusters/Debugging/` |
| Any board-related step | `Boards/<board-name>/` (e.g., `Boards/KCU105/`, `Boards/ZCU102/`) |
| ROCm / HIP labs | `ROCm/` and `F1/Topic Clusters/ROCm HIP Migration/` |

**How to search within a mapped folder:**
```bash
# Search only within the topic-specific folder
python "%USERPROFILE%/.claude/skills/custtr-lab-doc/scripts/find_images.py" <keyword>
# Then manually confirm the result is from the correct folder
# If the top result is from an unrelated folder, use the next result that IS in the mapped folder
```

**Priority within a topic folder:**
1. Use `find_images.py` to get results sorted newest-first
2. Pick the **first result that is inside the mapped folder** for the GitHub topic
3. Only use images from other folders if the mapped folder has no relevant image

---

#### Source 1: Vivado AI Assistant RAG (primary for AMD tool topics)

The Vivado MCP server exposes a hybrid BM25 + vector RAG model indexed over
Xilinx/AMD documentation — user guides, application notes, web docs, wikis, and
GitHub. This is the most accurate source for tool-specific commands, TCL syntax,
design flow steps, and known issues.

Use the `mcp__vivado-mcp-server__vivado_doc_search` tool. Run multiple queries
with different phrasings to get broad coverage:

```
mcp__vivado-mcp-server__vivado_doc_search({
  query: "how to run synthesis in Vivado step by step",
  top_k: 10,
  alpha: 0.80
})
```

| Parameter | Guidance |
|---|---|
| `query` | Natural language question — be specific ("Vivado synthesis run TCL commands") |
| `top_k` | Use 10–15 for lab content; 25 for troubleshooting and edge cases |
| `alpha` | 0.80 default (favors semantic); lower to 0.4–0.6 for exact keyword matches |

Run at least **4–6 queries** covering:
- The main flow/topic of each lab step
- Exact CLI or TCL commands needed
- Prerequisites and system requirements
- Expected outputs at each stage
- Known errors and fixes
- Verification commands

Extract from results: exact commands, flag names, file paths, expected console output,
version numbers, and any doc page URLs returned.

---

#### Source 1b: Vivado MCP Server (active Vivado session — use when available)

If a Vivado session is running, use `vivado_execute` to query the live tool for exact TCL command syntax, property names, and expected outputs. This is more accurate than documentation for commands that vary by version.

```tcl
# Example: get exact TCL syntax verified in the running tool
vivado_execute("help get_nets")
vivado_execute("help set_property mark_debug")
vivado_execute("help write_debug_probes")
```

Also use `vivado_doc_search` for hybrid RAG search over Xilinx/AMD docs:

```
mcp__vivado-mcp-server__vivado_doc_search({
  query: "netlist insertion debug probing flow Set Up Debug wizard ILA",
  top_k: 12,
  alpha: 0.80
})
```

Run 4–6 queries covering the main flow, exact TCL commands, prerequisites, expected outputs, known errors.

---

#### Source 2: AMD Technical Information Portal (TIP)

The TIP at https://docs.amd.com/ is AMD's official centralized documentation hub
covering all products — Vivado, Vitis, Versal, Zynq, Kria, ROCm, Instinct, and more.
It is the authoritative source for User Guides (UG), Product Guides (PG), Application
Notes (AN), and Datasheets (DS). **Always prefer UG documents for lab step content**
— they contain numbered procedures and expected outputs.

Search it using `WebSearch` scoped to `docs.amd.com`, then fetch the full page with
`WebFetch` before extracting content:

```
WebSearch({
  query: "Vivado synthesis user guide UG901 launch_runs TCL command",
  allowed_domains: ["docs.amd.com"]
})
```

Specialized sub-portals to use depending on the lab topic:

| Topic | Portal URL |
|---|---|
| ROCm, HIP, GPU programming | https://rocm.docs.amd.com/ |
| AMD Instinct / HPC cluster | https://instinct.docs.amd.com/ |
| Enterprise AI (AIM, workbench) | https://enterprise-ai.docs.amd.com/ |
| Vivado / Vitis / Zynq / Versal | https://www.xilinx.com/support/documentation-navigation/design-hubs.html |
| Troubleshooting (community fixes) | https://adaptivesupport.amd.com/s/ |

Full search patterns and document naming conventions (UG/PG/AN/DS prefixes) are in:

```
%USERPROFILE%\.claude\skills\custtr-lab-doc\references\amd_technical_portals.md
```

---

#### Source 3: Nabu (AMD internal knowledge base)

Use the `mcp__nabu__nabu_chat` tool with `amd_search_toggle: true` for topics
not covered by the Vivado RAG — ROCm, software tools, product specs, or internal
AMD processes.

```
mcp__nabu__nabu_chat({
  user_prompt: "How do I install AMD ROCm on Ubuntu 22.04 step by step?",
  amd_search_toggle: true,
  amd_legacy_search: false,
  max_tokens: 2000,
  k: 5
})
```

Run at least **3–5 queries** covering different aspects of the lab topic.
Collect the responses and extract:

- Exact commands (copy verbatim — do not paraphrase commands)
- Correct version numbers and package names
- Supported operating systems and hardware
- Real expected output strings
- Known errors and their official fixes
- Any URLs to AMD documentation pages returned in the results

#### Source 4: AMD Vitis GitHub tutorials (embedded knowledge base)

If the lab topic is Vitis-related (HLS, AI, acceleration, AI Engine, embedded,
Versal, Alveo), **read this file as part of the knowledge base before drafting
any content**:

```
%USERPROFILE%\.claude\skills\custtr-lab-doc\references\amd_vitis_tutorials.md
```

This file contains embedded knowledge sourced directly from AMD's official Vitis
GitHub repositories — exact commands, prerequisites, tool versions, supported boards,
lab sequences, and CLI syntax for all major Vitis flows. It is not a pointer to
go look something up later; treat it as structured reference content to draw from
immediately, the same way you would use retrieved Nabu results.

Priority when drafting content:
1. Commands and flows in `amd_vitis_tutorials.md` — use verbatim
2. Nabu results that add detail beyond what the file contains
3. WebSearch on AMD/Xilinx docs as a last resort

Never invent a command or expected output if the knowledge base already has it.

#### Source 5: Fallback WebSearch (AMD public documentation)

If Nabu returns no results or insufficient detail for a query, fall back to
`WebSearch` scoped to AMD's public documentation domains:

```
WebSearch({
  query: "[product] installation guide site:docs.amd.com OR site:xilinx.com OR site:rocm.docs.amd.com",
  allowed_domains: ["docs.amd.com", "xilinx.com", "rocm.docs.amd.com", "amd.com"]
})
```

Use `WebFetch` to retrieve the full content of any relevant pages found.

#### Knowledge retrieval rules

- **Query all available sources** (Vivado RAG → Nabu → Vitis tutorials file → WebSearch) before
  drafting any content. Do not skip sources because one returned results.
- **Commands must be copied verbatim** from the retrieved documentation. Never
  paraphrase or reconstruct a command from memory.
- **Version numbers must match** what the documentation states. Do not substitute
  your own defaults.
- **Expected outputs must reflect** what the docs say the user will see. Do not
  invent output strings.
- **If no source has information** on a specific detail, state that explicitly to
  the user and ask them to provide it — do not fill the gap with training data.
- **Cite the source** in a `reference` field or note whenever a specific doc page
  informed the content. Name which source it came from (RAG, Nabu, GitHub, or WebSearch).

---

### Step 1b — MANDATORY TUTORIAL CONFIRMATION (do this before writing anything)

After completing the GitHub search in Step 1, you may find **multiple tutorials** that partially match the lab name the user gave. Before writing any config or content, you MUST stop and present all matches to the user for confirmation.

**When to trigger this step:**
- Any time more than one tutorial directory matches the lab name or topic
- Any time the best match is not an exact name match
- Always — even if you are confident — when the topic is AI Engine, Vitis, or has multiple tutorial variants (AIE vs AIE-ML vs AIE-MLv2, numbered variants like 02- vs 04-)

**What to present to the user:**

List every matching tutorial found, with:
- Full GitHub path (repo + branch + directory path)
- Tutorial number and exact directory name
- One-line description of what it covers
- Target board/device
- Which tool version / branch it belongs to

**Example format:**

```
I found multiple tutorials matching "Channelizer-Using-Vitis-Libraries".
Please confirm which one to use:

1. AI_Engine_Development/AIE-MLv2/Design_Tutorials/02-Channelizer-Using-Vitis-Libraries
   Branch: 2025.2 | Board: VEK280 | Uses Vitis DSP Libraries on AIE-MLv2 architecture

2. AI_Engine_Development/AIE/Design_Tutorials/04-Polyphase-Channelizer
   Branch: 2025.1 | Board: VCK190 | Hand-written AIE kernels, no Vitis Libraries

Which tutorial should I use for the lab?
```

**Rules:**
- NEVER pick one silently based on which had richer documentation — always ask
- NEVER proceed to writing the config until the user explicitly confirms a tutorial
- If only one tutorial is found, still confirm: "I found [name] at [path] — is this correct?"
- The user's lab name is the primary anchor — match it exactly first, then by description

---

### Step 1c — Fetch images from the confirmed tutorial (MANDATORY, runs immediately after Step 1b)

Once the user confirms the exact tutorial, run the image fetch script against that tutorial's GitHub URL **before writing the config**. This downloads all images from that specific tutorial into the local `images/` folder so they can be referenced by filename in the config.

```bash
python "%USERPROFILE%/.claude/skills/custtr-lab-doc/scripts/fetch_github_images.py" \
  "<confirmed-github-tree-url>" --clear
```

Example for the Channelizer AIE-MLv2 tutorial:
```bash
python "%USERPROFILE%/.claude/skills/custtr-lab-doc/scripts/fetch_github_images.py" \
  "https://github.com/Xilinx/Vitis-Tutorials/tree/2025.2/AI_Engine_Development/AIE-MLv2/Design_Tutorials/02-Channelizer-Using-Vitis-Libraries" --clear
```

After the script runs:
- Read `%USERPROFILE%/.claude/skills/custtr-lab-doc/images/_last_fetch.json` to see exactly which images were downloaded and their filenames
- Use **only those filenames** in the config `image` fields — no other image sources
- Reference images by filename only (e.g. `"image": "Figure1.png"`) — the builder resolves them from the `images/` folder automatically

**Rules:**
- Always use `--clear` to remove images from any previous lab before downloading the new set
- Only use images that actually exist in `_last_fetch.json` — never guess filenames
- If the tutorial has no images folder, note that to the user and leave image fields out of the config

---

### Step 2 — Collect any remaining details from the user

After the knowledge retrieval AND after the user confirms the tutorial in Step 1b AND images are fetched in Step 1c, you will have most of the technical content. Confirm with the user and fill any gaps the knowledge base did not cover:

1. **Title** — the lab title
2. **Lab number** — default 1
3. **Version** — always use the current calendar year as the version (e.g. "2026.1" in 2026). Do NOT copy older version numbers from retrieved documentation. The version shown under the lab title must match the current year.
4. **Target audience / context** — who is running this lab and in what environment
5. **Any steps or requirements the user wants to add** beyond what the docs cover

If the user already provided content in their message, extract it directly —
don't ask again for things already given.

---

### Step 3 — Write the config JSON

Combine the knowledge base content and any user-supplied details into the config
file:

```
%USERPROFILE%\.psas-ai\shared\lab_config.json
```

Every field must contain real, verified content from Step 1. Never leave a field
with placeholder text, invented commands, or assumed version numbers.

Use this schema:

```json
{
  "title": "Lab Title Here",
  "lab_number": 1,
  "version": "2026.1",
  "abstract": "One paragraph describing the lab and estimated time.",
  "objectives": [
    "Do X",
    "Configure Y",
    "Validate Z"
  ],
  "prerequisites_intro": "Confirm every item below before starting.",
  "prerequisites": [
    ["Requirement", "Minimum Specification", "How to Verify"],
    ["<Requirement name>", "<Minimum version or spec>", "<verification command from docs>"]
  ],
  "introduction": [
    "Background paragraph 1 — sourced from AMD documentation.",
    "Background paragraph 2."
  ],
  "steps": [
    {
      "title": "Step Section Title",
      "intro": "One sentence describing this step's goal (rendered as General style — 13pt).",
      "instructions": [
        {"action": "Open a terminal window."},
        {"action": "Enter the following command in the Tcl Console:", "command": "exact-command --from-docs"},
        {"substep": "Click Run Implementation in the Flow Navigator."},
        {"substep": "Select the bitstream file and click Program.", "command": "optional-command-here"},
        {"note": "Note: This is a note or continuation paragraph (smart-bolded prefix)."},
        {"warning": "Note: Using Window > IP Catalog will add IP to the top level, not the block design."},
        {"lab1_continue": "There are different ways to add IPs to the design."},
        {"bullet2": "Click the Add IP icon on the horizontal bar of the workspace."},
        {"image": "screenshot.png", "caption": "Opening the Block Design"},
        {"question": "What files are in the project? Are these sufficient to build a project?", "answer_lines": 3}
      ],
      "outcome": "What the user should see when this step succeeds — rendered as ListContinue2."
    }
  ],
  "validation": {
    "intro": "Complete all checks below before considering the lab finished.",
    "rows": [
      ["Check / Command", "Expected Result", "What It Confirms"],
      ["<exact command from docs>", "<expected output from docs>", "<what passing this means>"]
    ],
    "pass_statement": "If all checks pass, the lab objective has been met."
  },
  "troubleshooting": {
    "problem": "Short description of the symptom (from known issues in docs)",
    "cause": "Explanation from AMD documentation of why this happens.",
    "steps": [
      {"action": "Check X:", "command": "check-command-from-docs"},
      {"action": "If X is missing, run:", "command": "fix-command-from-docs"},
      {"action": "If the issue persists, refer to:", "note": "<AMD doc URL>"}
    ],
    "reference": "URL to the relevant AMD documentation page"
  },
  "summary": "One paragraph summarizing what was accomplished in the lab.",
  "answers": [
    {
      "question": "What files are in the project?",
      "answer": "You can view the source files in this project by selecting the Sources window."
    }
  ]
}
```

---

### Step 4 — Run the builder script

```bash
python "%USERPROFILE%/.claude/skills/custtr-lab-doc/scripts/build_lab.py" \
  --config "%USERPROFILE%/.psas-ai/shared/lab_config.json" \
  --template "%USERPROFILE%/.claude/skills/custtr-lab-doc/references/amd_lab_template.docm" \
  --output "%USERPROFILE%/.psas-ai/shared/lab_output.docm"
```

---

### Step 5 — Copy to Desktop

```bash
python3 -c "
import shutil, os
shutil.copy2(
    '%USERPROFILE%/.psas-ai/shared/lab_output.docm',
    '%USERPROFILE%/Desktop/<LabTitle>.docm'
)
print('Done')
"
```

Replace `<LabTitle>` with a short filename derived from the lab title (no spaces,
use underscores).

---

### Step 6 — Confirm to the user

Tell the user:
- The file is on their Desktop
- The title, number of steps, and whether validation and troubleshooting were included
- Which AMD documentation sources were used to produce the content

---

## Tone and content guidelines

- **Action-oriented**: every step instruction starts with a verb ("Run", "Open", "Enter", "Confirm")
- **Expected Outcome always present**: every step must end with an Expected Outcome sentence
- **Commands in monospace**: any shell command goes in a `command` field, never inline in action text
- **One troubleshooting tip only**: do not add more than one troubleshooting section
- **Tables for structured data**: prerequisites and validation always use tables, not bullet lists
- **No placeholder text**: fill every field with real content — never leave "TBD" or "TODO"
- **Knowledge base first**: if content was not retrieved from Nabu or AMD docs, do not include it without flagging it to the user

---

## Common mistakes to avoid

- **NEVER pick a tutorial silently** — if multiple tutorials match the lab name or topic, always stop after Step 1 and present ALL matches to the user for confirmation before writing any content. Do not pick based on which had richer documentation.
- **Do not skip GitHub** — always fetch the relevant Xilinx GitHub repo page FIRST before any other source. Commands, file paths, and board names must come from GitHub verbatim, not from training data.
- Do not skip Step 1 — the knowledge retrieval is mandatory, even if the topic seems familiar
- Do not use `docx_create` MCP tool — it does not know these AMD styles
- Do not use `pptx_create` or any PPTX tool — the output is always `.docm`
- Do not invent new paragraph styles — only use the styles listed in the table above
- Do not use `~` in paths — always use full Windows paths like `C:/Users/<username>/...`
- Do not paraphrase commands from memory — copy them verbatim from the retrieved documentation
- **`action` must be a short bold summary** — the `action` text renders as LabListNumber1 (bold). It must be a short, punchy summary sentence that captures the entire meaning of the step. Follow every `action` with 2–4 `substep` entries that give the detailed, plain-text instructions. Never write a long sentence as the `action` text.
- **`substep` entries provide the detail** — each `substep` renders as LabListNumber2 (plain, not bold). Break the detailed explanation of the parent `action` into 2–4 individual substeps, one clickable action per substep. Example pattern:
  ```json
  {"action": "Open the Vitis Unified IDE and select a workspace."},
  {"substep": "Launch the Vitis Unified IDE from the desktop shortcut or taskbar."},
  {"substep": "When prompted, select or create a folder for the workspace and click Launch."}
  ```
- **Do NOT use `action` for sub-steps** — use `action` for LabListNumber1 (primary) and `substep` for LabListNumber2 (secondary)
- **Do NOT use `LabListNumber1ContinueNotBold`** — the correct style is `LabListNumber1Continue`; use `lab1_continue` key in the instruction dict
- **Do NOT use `w:numPr` for step numbering** — the builder uses SEQ fields automatically; just provide `action`/`substep` strings
- **Always check `T:\Graphics_Repository\` first for images** — reference directly by repo-relative path in the config
- **Every step that shows a UI action MUST have an image** — use `find_images.py` to search; results are sorted newest version first — always use the top result
- **Always use the most recent version image** — `find_images.py` sorts by full version descending (`2025.2 > 2025.1 > 2024.2 > 2024.1 > 2023.2 > 2023.1 > ...`); always pick the **first result**. Prefer `2025.2` wherever available, then `2025.1`, then `2024.2`, etc. Never use `[2017.1]` if a newer version exists
- **Do NOT render `outcome` as "Expected Outcome:" text** — the `outcome` field in the config is for author notes only; real AMD labs never print this text in the student document
- **Always include `general_flow` in the config** — every lab must have a General Flow section. Add a `general_flow` array with one entry per lab step using `<gerund> <noun>` format (e.g. "Building Platform", "Simulating Design"). Set `general_flow_per_row` to match the number of steps (max 5 per row). Never omit this field.
- **Every step MUST have at least one question** — placed inline after the relevant step instruction, not at the end of the step
- **Version must be current year** — always `"2026.1"` in 2026; do not copy older version numbers from retrieved documentation
- **Images must use VML** — the builder handles this automatically; never write DrawingML image XML manually
- **QuestionLine is just a tab** — the underline comes from the style definition; do not add underline formatting manually
- If the template `.docm` is open in Word, the script will still work — it reads only, never writes to the template
