---
name: upgrade-discovery-and-analysis
description: 'Sub-skill for project discovery, version validation, IP revision checks, and changelog analysis during Vivado project upgrades.'
argument-hint: 'Provide source Vivado version, target Vivado version, and project path'
applyTo: '**'
---

# Sub-Skill 1: Project Discovery, Version Validation, IP Revision Checks & Changelog Analysis

Handles the initial phase of a Vivado project upgrade: validating the upgrade direction, opening the project in the target version, inventorying all IPs, checking revision changes, and analyzing changelogs to classify each IP's required upgrade action.

## When to Use

- Starting a new project upgrade — this sub-skill runs first
- Need to determine which IPs changed between source and target Vivado versions
- Need to classify IPs by upgrade complexity (version bump only, config changes, port changes, replacement)
- Need to validate that the upgrade direction is correct (old → new only)

## Prerequisites

- Source Vivado version and target Vivado version must be known
- Target version MUST be later than source version (never downgrade)
- Access to the target Vivado installation
- The original project path must be accessible

## Procedure

### Phase 1: Project Discovery and Version Validation

1. **Validate upgrade direction** — Confirm target version > source version. Reject any downgrade request immediately.

2. **Open the project in the TARGET Vivado version** — Use the target Vivado to open or migrate the project:
   ```tcl
   open_project <path_to_project>.xpr
   ```
   Vivado will report IP status and any IPs requiring upgrade.

3. **Generate IP Status Report** — Get the full list of IPs and their upgrade status:
   ```tcl
   report_ip_status -name ip_status_report
   ```
   This identifies which IPs have new revisions available in the target version.

### Phase 2: IP Revision and Changelog Analysis

4. **Inventory all IPs and their revisions** — For each IP in the design, record:
   - IP name and current VLNV (vendor:library:name:version)
   - New VLNV available in target Vivado
   - Whether the IP is locked, deprecated, or requires upgrade

5. **Check IP changelogs** — For each IP that has a version change, review the changelog:
   ```tcl
   # Get IP definition details
   get_ipdefs -filter {NAME == <ip_name>}
   # Check IP catalog for revision history
   get_property CORE_REVISION [get_ipdefs <vlnv>]
   ```
   Also check AMD/Xilinx product guides, release notes, and IP changelogs for:
   - Configuration property changes (added/removed/renamed CONFIG.* keys)
   - Port/pin changes (added/removed/renamed/resized ports)
   - Signal changes (new required signals, removed signals)
   - Bus interface changes (protocol upgrades, interface renaming, width changes)
   - Behavioral changes (new operating modes, deprecated features)

6. **Classify each IP into one of these categories:**

   | Category | Action Required |
   |----------|----------------|
   | **Version bump only** (no functional changes) | Simple in-place upgrade, no design changes |
   | **Config changes** (new/removed properties) | Update IP configuration, may need example design |
   | **Port/signal changes** (added/removed/renamed pins) | Must generate example design, remap connections |
   | **Bus interface changes** (protocol/width change) | Must generate example design, redesign connectivity |
   | **IP replaced entirely** (new IP replaces old) | Must generate example design of replacement IP |

## Output Artifacts

- IP inventory table with current and target VLNVs
- Classification of each IP by upgrade category
- Changelog summary for each changed IP
- List of IPs requiring example design generation (handed off to Sub-Skill 2)

## Upgrade Decision Tree (Discovery Phase)

```
For each IP in design:
│
├─ Version unchanged? → No action needed
│
├─ Version changed?
│  ├─ Changelog shows NO port/config/interface changes? → "Version bump only"
│  ├─ Changelog shows config property changes only? → "Config changes"
│  ├─ Changelog shows port/signal/interface changes? → "Port/signal changes"
│  └─ IP deprecated/replaced by new IP? → "IP replaced"
```

## Key Principles

- **Always upgrade, never downgrade** — Reject any request to move to an earlier Vivado version
- **Check ALL IPs** — Even minor version bumps can have subtle behavioral changes
- **Document everything** — Record what changed for each IP and why it matters
- **Never modify the original** — This phase is read-only analysis; no changes to the project yet
