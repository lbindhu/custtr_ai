# AMD Technical Information Portal — Knowledge Base

This file documents AMD's official technical documentation portals and how to
use them as knowledge sources when generating lab content. Read this file during
Step 1 (knowledge retrieval) for any lab topic, regardless of product area.

---

## Primary Portal: AMD Technical Information Portal (TIP)

**URL:** https://docs.amd.com/

The AMD TIP is the single authoritative source for all AMD technical documentation
across the full product portfolio. It covers:

- AMD EPYC processors
- AMD Radeon graphics
- AMD Instinct accelerators
- AMD Alveo adaptive accelerators
- Adaptive computing products — Zynq SoCs, Versal ACAPs, FPGAs
- AMD Kria system-on-modules

**How to access a specific document:**
```
https://docs.amd.com/v/u/en-US/<document-code>
```
Example: `https://docs.amd.com/v/u/en-US/ug1676-sdkdoc-platformstudio-documentation`

**How to search:** Use `WebSearch` with `allowed_domains: ["docs.amd.com"]` and
include the document type (UG, PG, AN, DS) in the query if known:

```
WebSearch({
  query: "Vivado synthesis user guide UG901 site:docs.amd.com",
  allowed_domains: ["docs.amd.com"]
})
```

### AMD Document Naming Conventions

| Prefix | Document Type | Example |
|---|---|---|
| UG | User Guide — procedural how-to content | UG901 Vivado Design Suite User Guide |
| PG | Product Guide — IP core documentation | PG252 AXI DMA |
| AN | Application Note — design-specific guidance | AN-1200 |
| DS | Datasheet — part specifications | DS925 Zynq UltraScale+ |
| TP | Technical Paper | TP495 |
| WP | White Paper | WP512 |

Always prefer UG documents for lab content — they contain step-by-step procedures
and expected outputs. PG documents are best for IP configuration steps.

---

## Specialized Documentation Portals

### ROCm Documentation
- **URL:** https://rocm.docs.amd.com/
- **Covers:** AMD open-source software platform for HPC and AI workloads; GPU programming,
  developer APIs, software frameworks, ROCm compatibility matrix
- **Use for labs on:** ROCm installation, HIP programming, MIOpen, PyTorch/TensorFlow on AMD GPU
- **Versioned:** `rocm.docs.amd.com/en/latest/` or `/en/docs-6.2.1/` — always pin the version
- **Radeon/Ryzen variant:** https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/

### AMD Instinct Data Center GPU Documentation
- **URL:** https://instinct.docs.amd.com/latest/index.html
- **Covers:** Enterprise deployment and operations of AMD Instinct GPUs; system administration,
  cluster management, monitoring, HPC/AI operational best practices
- **Note:** From ROCm 6.4 onward, driver documentation and system management content
  moved here from rocm.docs.amd.com

### AMD Enterprise AI Suite Documentation
- **URL:** https://enterprise-ai.docs.amd.com/
- **Covers:** AMD unified AI infrastructure platform including:
  - AMD Inference Microservice (AIM) — model serving
  - AMD Solution Blueprints — validated AI workflows
  - AMD Resource Manager — resource governance
  - AMD AI Workbench — model development

### Xilinx / Adaptive Computing Documentation Portal
- **URL:** https://www.xilinx.com/support/documentation-navigation/documentation-portal.html
- **Keyword search:** https://www.xilinx.com/support/documentation-navigation/documentation-keyword-search.html
- **Design Hubs (by task):** https://www.xilinx.com/support/documentation-navigation/design-hubs.html
- **Use for labs on:** Vivado, Vitis, PetaLinux, IP cores, Zynq, Versal, FPGA design flows
- **DocNav:** Offline doc database integrated into Vivado IDE (Help → Documentation and Tutorials)

### AMD Adaptive Support Community
- **URL:** https://adaptivesupport.amd.com/s/
- **Covers:** Knowledge base articles, community Q&A, FAQs, and support cases for adaptive
  computing products (FPGAs, SoCs, Versal, Kria)
- **Use for:** Troubleshooting tips — real-world error messages and community-verified fixes

### AMD Developer Central
- **URL:** https://www.amd.com/en/developer.html
- **Documentation by type:** https://www.amd.com/en/developer/browse-by-resource-type/documentation.html
- **Use for:** Broad developer-facing content not tied to a specific product portal

---

## Quick Reference: Which Portal to Use by Lab Topic

| Lab Topic | Primary Portal |
|---|---|
| Vivado synthesis, implementation, timing | docs.amd.com (UG901, UG904, UG949) |
| Vitis HLS, acceleration, platform creation | docs.amd.com + Xilinx design hubs |
| Vitis AI, DPU, model quantization | docs.amd.com + rocm.docs.amd.com |
| ROCm installation, HIP, GPU programming | rocm.docs.amd.com |
| AMD Instinct, HPC cluster setup | instinct.docs.amd.com |
| Zynq / MPSoC / Versal embedded design | docs.amd.com + xilinx.com design hubs |
| Kria SOM bring-up | docs.amd.com |
| IP core configuration (AXI, DMA, etc.) | docs.amd.com (PG documents) |
| Troubleshooting FPGA/SoC issues | adaptivesupport.amd.com |
| Enterprise AI inference deployment | enterprise-ai.docs.amd.com |

---

## How to Search These Portals During Knowledge Retrieval

Use `WebSearch` with the portal domain scoped in `allowed_domains`:

```
# AMD TIP — general search
WebSearch({
  query: "Vivado implementation strategies timing closure",
  allowed_domains: ["docs.amd.com"]
})

# ROCm — installation and GPU programming
WebSearch({
  query: "ROCm 6.2 installation Ubuntu 22.04",
  allowed_domains: ["rocm.docs.amd.com"]
})

# Xilinx design hubs — flow-based search
WebSearch({
  query: "Vitis HLS AXI interface synthesis",
  allowed_domains: ["xilinx.com", "docs.xilinx.com"]
})

# Adaptive support — troubleshooting
WebSearch({
  query: "Vivado ERROR Synth 8-439 module not found fix",
  allowed_domains: ["adaptivesupport.amd.com"]
})
```

After a `WebSearch` returns a relevant page URL, use `WebFetch` to retrieve the
full page content before extracting commands and expected outputs.

---

## Rules for Using Portal Content in Labs

1. **Always fetch the actual page** — do not rely on the search snippet alone.
   Use `WebFetch` on the returned URL to read the full procedure.
2. **Cite the document code and URL** — include in the `reference` field
   (e.g., "UG901 — Vivado Design Suite User Guide: https://docs.amd.com/...").
3. **Match the version** — docs.amd.com hosts version-specific content. Confirm
   the page version matches the lab's target tool version before copying content.
4. **Prefer UG documents for steps** — User Guides contain numbered procedures
   and expected outputs; use those as the template for lab steps.
5. **Use adaptivesupport.amd.com for troubleshooting** — community-verified fixes
   are more reliable for the troubleshooting section than generic error descriptions.
