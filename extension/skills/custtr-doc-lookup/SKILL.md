---
name: custtr-doc-lookup
description: Finds AMD documentation links for a given topic or device family. Searches the AMD Technical Information Portal (docs.amd.com) to find relevant user guide, architecture manual, product guide, and data sheet links for any AMD topic or device family. Use this skill whenever the user provides a topic related to AMD products and wants documentation links — such as Versal, AI Engine, SelectIO, NoC, DDR, GT Transceivers, Vivado, Vitis, PetaLinux, Zynq, UltraScale, FPGA, or any specific module like Processing System, Platform Management Controller, SelectIO Resources, etc. Trigger on: "find docs for", "user guide for", "AMD documentation", "TIP link", "docs.amd.com link", or any request to look up AMD technical documentation. Always use this skill when the user gives a numbered topic (e.g. "06. AMD Versal AI Edge...") or pastes a course/module title and wants reference links. Also triggers when the user provides a list of course names and asks to load or register them, or when the user provides a module name and asks to find matching documentation.
owner: akanapur
---

# AMD Technical Information Portal — Documentation Lookup

**Owner:** akanapur

This skill operates in two modes depending on what the user provides.

---

## Mode 1: Load Course List

When the user provides a **list of course names** (numbered or bulleted), store them as the active course list for this session. Confirm receipt with a numbered list of the courses registered, and tell the user they can now give any module name to find its documentation.

---

## Mode 2: Look Up Documentation for a Topic or Module

When the user provides a **module name or topic**, find the most relevant AMD documentation links from **docs.amd.com** and return them in a clean, structured format.

### Matching logic

If a course list was previously loaded in this session:
- Match the user's input to the closest course/module name (fuzzy match — ignore numbering, capitalization, abbreviations)
- Confirm the match before searching

If no course list is loaded, treat the input as a direct topic and search immediately.

### How to search

Run **3 web searches in parallel** using different query strategies:

1. **Exact device + topic**: `site:docs.amd.com "<device family>" "<topic keyword>"`
2. **Document number hunting**: `docs.amd.com <device family> <topic> UG OR AM OR PG OR DS`
3. **Subsystem section deep-links**: `docs.amd.com "<subsystem name>" "<device family>" site:docs.amd.com`

If the topic names a **specific subsystem** (e.g., PMC, AI Engine, NoC, SelectIO, DDR, GT), also run a 4th targeted search for section-level deep-links within the primary TRM.

If the topic is **broad/non-device-specific**, run wider variations including tools-focused and version-agnostic queries.

Always scope results to **docs.amd.com** only. Use WebFetch to read actual page content when a specific URL is provided.

### Document type priority

| Prefix | Type | When relevant |
|--------|------|---------------|
| AM | Architecture Manual | Primary architectural reference |
| UG | User Guide | Implementation and usage guidance |
| PG | Product Guide | Vivado IP blocks |
| DS | Data Sheet | DC/AC specs, device characteristics |
| EN | Embedded Navi | AMD training/course content |

### Handling Gen 1 vs Gen 2

If the topic specifies Gen 2 (e.g., "Versal AI Edge Series Gen 2"), **prioritize Gen 2-specific documents** (e.g., AM026 over AM011). Still include relevant Gen 1/general documents as secondary references if no Gen 2-specific document exists yet. Label Gen 1 fallbacks clearly.

### Deduplication

Deduplicate by document number before presenting. If the same UG or AM appears from multiple searches pointing to different sections, consolidate into one row with section deep-links listed below.

### Output format

Always output:
1. A **matched module line** (if course list is active)
2. A **markdown table** with columns: Document | Description | Link
3. **Section deep-links** as sub-rows or bullets beneath the relevant parent row
4. A **Sources:** section listing all URLs as markdown links

### If results are sparse

If fewer than 3 documents are found, run one more broader search (drop the device family constraint, or try the topic alone). If still sparse, say so and direct the user to [docs.amd.com](https://docs.amd.com) directly.

### Tone

Be concise. The user is a technical trainer — they want actionable links, not explanations. One-line descriptions in the table are enough.
