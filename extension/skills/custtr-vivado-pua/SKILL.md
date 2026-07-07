---
name: custtr-vivado-pua
description: 'Upgrades Vivado FPGA projects/designs from an earlier version to a later version.'
argument-hint: 'Provide source Vivado version, target Vivado version, and project path to upgrade'
applyTo: '**'
---

# Vivado Project Upgrade Skill

Autonomously upgrade a Vivado FPGA project from an earlier version to a later version of Vivado. This skill enforces a strict upgrade direction (old → new only) and uses IP example designs as ground truth for any IPs that changed configuration, pinout, signals, or bus interfaces between versions.

This skill is an **orchestrator** — it delegates all work to specialized sub-skills. Read and execute the appropriate sub-skill for each phase of the upgrade.

## When to Use

- Upgrading a Vivado project from any earlier version to any later version (e.g., 2022.2 → 2024.1, 2023.1 → 2025.1)
- IP cores have changed revisions between the source and target Vivado versions
- Need to understand what changed in IPs between versions (config, ports, interfaces)
- Need to validate that the upgraded design is functionally equivalent to the original

## Prerequisites

- Source Vivado version and target Vivado version must be known
- Target version MUST be later than source version (never downgrade)
- Access to both Vivado installations (source and target) or at minimum the target version
- The original project path must be accessible

## Sub-Skills

This skill is composed of the following sub-skills. **Always read the full sub-skill SKILL.md before executing each phase.** The sub-skills must be executed in order (1 → 2 → 3), with Sub-Skill 4 used only when a GitHub repository is involved.

| # | Sub-Skill | File | Phases Covered | Description |
|---|-----------|------|----------------|-------------|
| 1 | **Discovery & Analysis** | `sub_skills/discovery_and_analysis/SKILL.md` | Phase 1–2 | Project discovery, version validation, IP revision checks, changelog analysis, IP classification |
| 2 | **Design Upgrade** | `sub_skills/design_upgrade/SKILL.md` | Phase 3, 3.5, 4, 5 | Example design generation, migration maps, custom RTL module migration, apply upgrade, initial validation |
| 3 | **Build & Validation** | `sub_skills/build_and_validation/SKILL.md` | Phase 6 | Full synthesis, implementation, timing closure, device image generation |
| 4 | **GitHub Repo Migration** | `sub_skills/github_repo_migration/SKILL.md` | (Independent) | Repository structure migration, version string updates, documentation/screenshot regeneration, git commit |

## Procedure (Orchestration)

### Step 1: Discovery & Analysis (Sub-Skill 1)

**Read:** `sub_skills/discovery_and_analysis/SKILL.md`

Execute Phase 1 (Project Discovery & Version Validation) and Phase 2 (IP Revision & Changelog Analysis):
- Validate upgrade direction (target > source)
- Open the project in the target Vivado version
- Generate IP status report
- Inventory all IPs and their revisions
- Check IP changelogs for changes
- Classify each IP by upgrade category (version bump, config change, port change, replaced)

**Output:** IP inventory table, IP classification by category, list of IPs needing example designs → pass to Sub-Skill 2.

### Step 2: Design Upgrade (Sub-Skill 2)

**Read:** `sub_skills/design_upgrade/SKILL.md`

Execute Phase 3 (Example Design Generation), Phase 3.5 (Custom RTL Module Migration), Phase 4 (Apply Upgrade), and Phase 5 (Initial Validation):
- Generate example designs for IPs with port/signal/interface changes
- Build migration maps (old → new port/interface mapping)
- Inventory, copy, and validate all custom RTL modules (user-written HDL files)
- Create upgraded project copy
- Upgrade IPs, update block designs, RTL sources, and constraints
- Run elaboration check, IP generation, and simulation

**Output:** Upgraded project directory, migration maps, custom RTL inventory, elaboration/simulation pass → pass to Sub-Skill 3.

### Step 3: Build & Validation (Sub-Skill 3)

**Read:** `sub_skills/build_and_validation/SKILL.md`

Execute Phase 6 (Full Design Build):
- Run synthesis and review results
- Run implementation (place-and-route)
- Verify timing closure
- Generate device image (bitstream/PDI)
- Compare utilization with original design
- Produce build summary

**Output:** Device image file, timing/utilization/power reports, build summary.

### Step 4: GitHub Repo Migration (Sub-Skill 4) — *Only if a git repo is involved*

**Read:** `sub_skills/github_repo_migration/SKILL.md`

Execute only when the user provides a GitHub repository URL or local git-managed path:
- Clone/read the repository structure
- Apply upgraded design files from Sub-Skills 1–3
- Update all version references throughout the repo
- Update documentation, tutorials, and screenshots
- Stage changes for user review and commit

**Output:** New git branch/repo with all upgraded files, updated docs, clean commit history.

## Key Principles

1. **Always upgrade, never downgrade** — Reject any request to move to an earlier Vivado version
2. **Example design is ground truth** — When an IP changes ports/config/interfaces, the example design generated by the target Vivado shows the correct usage
3. **Never modify the original** — Always work on a copy; preserve the original for comparison and rollback
4. **Check ALL IPs** — Even minor version bumps can have subtle behavioral changes; review changelogs for every IP
5. **Validate by comparison** — The upgraded design must produce functionally equivalent results to the original
6. **Width mismatches are critical** — A single-bit width mismatch can cause silent data corruption; verify every connection width
7. **Clock domain changes require careful analysis** — If an IP moves clocks around, all downstream timing constraints must be updated
8. **Document everything** — Record what changed, why, and how it was resolved for future reference
9. **Custom RTL is carried unchanged** — User-written HDL files must be copied verbatim to the upgraded project. They are only modified if IP interface changes force port remapping in wrapper modules. Never silently drop custom source files during migration.
10. **Always read the sub-skill** — Before executing any phase, read the full sub-skill SKILL.md file to get the detailed procedure, TCL commands, and validation steps.

## Upgrade Decision Tree

```
For each IP in design:
│
├─ Version unchanged? → No action needed
│
├─ Version changed?
│  │
│  ├─ Changelog shows NO port/config/interface changes?
│  │  └─ Simple upgrade_ip in-place
│  │
│  ├─ Changelog shows config property changes only?
│  │  └─ Upgrade IP, update CONFIG properties, regenerate targets
│  │
│  ├─ Changelog shows port/signal/interface changes?
│  │  ├─ Generate IP example design in target Vivado
│  │  ├─ Analyze new ports, signals, interfaces from example
│  │  ├─ Build migration map (old → new)
│  │  ├─ Apply migration map to project connections
│  │  └─ Validate connectivity matches example design
│  │
│  └─ IP deprecated/replaced by new IP?
│     ├─ Identify replacement IP from Vivado IP Catalog
│     ├─ Generate example design of replacement IP
│     ├─ Map old IP functionality to new IP
│     ├─ Replace IP instance and all connections
│     └─ Validate equivalent functionality
```

## Common Pitfalls

- **Forgetting to regenerate IP targets** after property changes — always call `generate_target all`
- **Assuming port names are stable** — even minor IP revisions can rename ports
- **Ignoring new mandatory ports** — new IP versions may expose ports that must be connected
- **Not checking address maps** — AXI address spaces often change between IP versions
- **Skipping simulation** — synthesis success does not guarantee functional correctness
- **Mixing IP versions** — all IPs in a design must be compatible with the single target Vivado version
- **Dropping custom RTL files during migration** — user-written HDL files not associated with an IP are easily overlooked; always inventory and explicitly copy them to the upgraded project
- **Losing file properties on custom RTL** — VHDL standard (93 vs. 2008), library assignments, and `IS_GLOBAL_INCLUDE` flags must be preserved when re-adding files to the new project
- **Not validating custom RTL against new synthesis engine** — newer Vivado versions may flag previously-silent issues (implicit nets, non-ANSI ports, deprecated pragmas) as errors

## Output Artifacts

After a successful upgrade, the skill produces:
- Upgraded project directory with all sources
- IP migration map documenting all changes
- **Custom RTL inventory** — complete list of all user-written HDL files carried to the upgraded project, with file type, category, library assignment, and any compatibility notes
- Utilization comparison report (old vs. new)
- Simulation comparison results (if testbenches available)
- Timing summary (if implementation was run)
- Summary of all changes made and rationale

## Lessons Learned from Previous Upgrades

The following generic lessons were captured from real upgrade experiences. Apply these proactively during any Vivado project upgrade:

### 1. Board Part Versions Change Between Vivado Releases

Board part identifiers (e.g., `xilinx.com:boardname:part0:X.Y`) are version-specific. A board part available in one Vivado release may not exist in another. **Always query available board parts** in the target Vivado before scripting:

```tcl
get_board_parts *<board_name>*
```

If the exact version isn't available, use the highest available version. Never hard-code board part versions without validation.

### 2. Multi-Instance Designs Require Signal Isolation

When a design instantiates **multiple copies of the same IP**, each instance must have fully independent signal connections. Common failure modes:

- **Shared output wires** — If two IP instances connect their outputs to the same `wire`, a Multiple Driver (MDRV-1) DRC error occurs at implementation. Every output from every instance must connect to its own unique wire/net.
- **Shared I/O pads** — Physical I/O ports (serial transceivers, differential pairs) cannot be shared across instances. Verify that each instance's physical interface ports map to unique top-level ports.
- **Generated internal net names** — Some IPs generate internal nets with fixed names. When two instances exist in the same design, these names can collide. Use different module names (not just different instance names) for each IP generation to ensure unique internal hierarchies.

**Validation approach:** After synthesis passes, always check for MDRV-1 DRC errors before assuming the design is correct. Synthesis resolving without error does NOT guarantee implementation will succeed.

### 3. IP Flow Changes May Alter the Design Architecture

Major Vivado version upgrades can change the **fundamental design flow** for an IP, not just its configuration parameters. Examples:

- An IP that previously required IP Integrator (Block Design) may move to RTL-based instantiation
- Block Automation flows may be deprecated in favor of manual/scripted connections
- IPs may be replaced entirely by new IPs with different VLNVs

**When an IP changes its design flow:**
1. Generate the IP's example design in the target Vivado version
2. Study the example design hierarchy — it shows the canonical connection pattern
3. Do NOT assume the old block design TCL will work — the IP may no longer support that flow
4. Adapt the project creation script to match the new canonical flow

### 4. XCI Files Are Version-Locked

IP configuration files (`.xci`) are tied to specific Vivado versions. When migrating:

- Verify every `.xci` file is present in the migrated project directory
- If an XCI was generated by a previous tool version and is a standard Xilinx IP (e.g., AXI register slice, clock wizard), consider regenerating it fresh in the target version with equivalent parameters rather than attempting to upgrade the old XCI
- Missing XCI files will cause "module not found" errors during synthesis — these appear as synthesis failures, not project creation failures

### 5. Constraints Must Match the New Hierarchy

When IPs change their internal structure (new wrappers, renamed submodules, different hierarchy depths):

- **Cell path wildcards** (`*`) in constraints may stop matching
- **BEL/LOC constraints** referencing old IP cell names will produce CRITICAL WARNINGS about unmatched objects
- **CDC waivers** referencing specific register names may become invalid if RTL modules are refactored

**Mitigation:** Use robust wildcard patterns in constraints that survive hierarchy changes. After a build, review all "No cells matched" and "No pins matched" warnings — these indicate stale constraints that should be updated or removed.

### 6. Synthesis Success ≠ Implementation Success

A design can pass synthesis cleanly but fail during implementation (`opt_design`, `place_design`, or `route_design`). Common causes:

- **DRC violations** (multiple drivers, unconnected mandatory ports) — only checked at opt_design
- **Placement conflicts** — two hard IP blocks assigned overlapping physical locations
- **Timing closure failure** — design is too large/fast for the target clock

**Always run through implementation** to validate a design upgrade, not just synthesis.

### 7. Iterative Build-Fix-Rebuild is Expected

Complex design upgrades rarely succeed on the first build attempt. Plan for 2-4 iterations:

1. **First build** — Catches project setup issues (missing files, wrong board part, IP version mismatches)
2. **Second build** — Catches RTL-level issues (port mismatches, width changes, new required signals)
3. **Third build** — Catches implementation-level issues (multi-driver conflicts, placement failures, timing)
4. **Final build** — Clean pass through to device image generation

Do not treat intermediate failures as blockers — they are expected diagnostic steps in the upgrade process.

### 8. Generated IP Wrappers Have Fixed Internal Names

When Vivado generates an IP (via `create_ip` or example design), the wrapper module name determines internal hierarchy names. In multi-instance designs:

- Use **different `-module_name`** values for each IP instance (e.g., `dcmac_0`, `dcmac_1`)
- The module name propagates into generated constraints, internal net names, and cell hierarchies
- Two instances with the same module name but different instance names will have colliding internal constraints

### 9. Verify Physical Pin Mapping for Multi-Instance I/O

For designs with multiple hard IP instances requiring dedicated physical I/O (transceivers, LVDS, etc.):

- Map each instance's I/O to its **own set of physical pins** — never share pins between instances
- Cross-check the pin mapping against the device's bank/quad architecture
- In scripted flows, trace every top-level port through the hierarchy to confirm it reaches the correct (and unique) physical pad

### 10. Document and Version-Control Every Build Attempt

Keep a record of:
- The exact error messages from each failed build
- The fix applied for each error
- The final working configuration

This enables rapid debugging if the same patterns appear in future upgrades and provides a rollback path if later changes introduce regressions.
