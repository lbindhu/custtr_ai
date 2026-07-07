---
name: upgrade-github-repo-migration
description: 'Independent sub-skill for migrating a GitHub-based Vivado design repository to an upgraded version. Reads the existing repo structure, upgrades the design, and creates a new repo/branch with the upgraded version name.'
argument-hint: 'Provide the GitHub repo URL or local path, source Vivado version, and target Vivado version'
applyTo: '**'
---

# Sub-Skill 4: GitHub Repository Migration for Upgraded Designs

Independently handles the migration of a GitHub-hosted Vivado design repository to a new upgraded version. This sub-skill reads the existing repo directory structure, understands the design hierarchy, applies the upgrade, and produces a new repository (or branch) named after the target Vivado version with all updated files, scripts, documentation, and tutorials.

## When to Use

- **ONLY** when the user provides a GitHub repository (URL or local clone path) to upgrade
- The design source lives in a git-managed repository
- The user wants the upgraded design committed/pushed to a new repo or branch
- Need to migrate the entire repo structure (README, tutorials, build scripts, CI/CD) to reflect the new version
- Do NOT invoke this sub-skill for non-git projects or local-only designs

## When NOT to Use

- No GitHub repo or git directory is provided
- The user only wants to upgrade a local Vivado project without version control
- The design is not managed in a git repository

## Prerequisites

- GitHub repo URL or local path to a cloned repo
- Source and target Vivado versions identified
- Git available in the environment
- Sub-Skills 1–3 available for the actual design upgrade work

## Procedure

### Phase 1: Repository Discovery

1. **Clone or read the repository** — If a URL is provided, clone it; if a local path, read it directly:
   ```bash
   git clone <repo_url> <local_path>
   # OR
   cd <existing_local_path>
   ```

2. **Analyze repository structure** — Map the entire directory tree:
   - Identify Vivado project files (`.xpr`, `.bd`, `.tcl`, `.xdc`, `.xci`)
   - Identify HDL sources (`.v`, `.sv`, `.vhd`, `.vhdl`)
   - Identify documentation (`README.md`, tutorials, guides)
   - Identify build/automation scripts (`Makefile`, `build.tcl`, CI/CD configs)
   - Identify IP configurations and block design TCL scripts
   - Note any version-specific references in file names or paths

3. **Identify version references throughout the repo** — Search for:
   - Vivado version strings in scripts (e.g., `2022.2`, `2023.1`)
   - Version-specific paths (e.g., `/tools/Xilinx/Vivado/2022.2/`)
   - IP VLNV version strings in TCL scripts
   - Version references in README, documentation, and tutorials
   - CI/CD pipeline version references
   - Docker/container image tags with Vivado versions

### Phase 2: Design Upgrade (Delegate to Sub-Skills 1–3)

4. **Run the design upgrade** — Invoke Sub-Skills 1, 2, and 3 as needed:
   - Sub-Skill 1: Discovery, version validation, IP revision checks, changelog analysis
   - Sub-Skill 2: Example design generation, migration maps, apply upgrade
   - Sub-Skill 3: Build and validation (synthesis, implementation, device image)

   Collect all upgrade artifacts and changes produced by these sub-skills.

### Phase 3: Repository Migration

5. **Create the new branch or repository** — Named after the target version:
   ```bash
   # Option A: New branch in same repo
   git checkout -b upgrade/<target_version>
   
   # Option B: New repository (if requested)
   mkdir <project_name>_<target_version>
   cp -r <original_repo>/* <project_name>_<target_version>/
   cd <project_name>_<target_version>
   git init
   ```

6. **Apply upgraded design files** — Replace/update all design files:
   - Updated `.xpr` project file (or regeneration TCL script)
   - Updated block design TCL scripts with new VLNVs and connections
   - Updated IP configurations (`.xci` files or creation scripts)
   - Updated HDL sources (if port/signal changes required RTL modifications)
   - Updated constraint files (`.xdc`) if clock/pin changes occurred
   - Updated wrapper files

7. **Update all version references** — Globally replace version strings:
   ```bash
   # Find and update version references
   grep -rl "<source_version>" . | xargs sed -i 's/<source_version>/<target_version>/g'
   ```
   - Update Vivado version strings in all TCL scripts
   - Update tool path references
   - Update IP version strings in build scripts
   - Update `scripts_vivado_version` in BD TCL scripts

8. **Update documentation and tutorials** — Rewrite version-specific content:
   - Update `README.md` with new version, updated instructions, and any changed steps
   - Update tutorial documents to reflect new IP configurations or workflows
   - Add migration notes explaining what changed from the previous version
   - Update "Tested With" or "Requirements" sections

### Phase 3.5: Screenshot and Image Regeneration

9. **Inventory all existing screenshots/images** — Find all image assets in the repo:
   ```bash
   find . -type f \( -name "*.png" -name "*.jpg" -name "*.jpeg" -name "*.gif" -name "*.svg" \) | sort
   ```
   - Identify images referenced in tutorials and documentation
   - Classify each image by type:
     - IP configuration/customization dialog screenshots
     - IPI block design diagrams
     - Vivado GUI workflow screenshots (project creation, synthesis, etc.)
     - Timing/utilization report screenshots
     - Simulation waveform captures

10. **Regenerate IP configuration screenshots** — For each IP config image:
    - Open the upgraded IP in Vivado GUI customization dialog
    - Capture the new configuration window showing updated parameters
    - Save with the same filename to preserve markdown/doc references
    - If the IP has new tabs or removed options, capture all relevant views
    - **Note:** This step requires manual GUI interaction or Vivado's `export_ip_user_files` for non-visual representations. Flag images that need manual recapture and provide the user with exact steps:
      ```
      Images requiring manual recapture:
      - docs/images/cmac_config.png → Open CMAC IP, Customize IP dialog
      - docs/images/gt_wizard_setup.png → Open GT Wizard, General tab
      ```

11. **Regenerate block design diagrams** — For IPI block design images:
    - After the block design is upgraded and validated, export a new diagram:
      ```tcl
      # Open the upgraded block design
      open_bd_design <path_to_bd>
      
      # Regenerate layout for clean appearance
      regenerate_bd_layout
      
      # Export block design as PDF/SVG (if supported)
      # For PNG export, use write_bd_layout:
      write_bd_layout -format pdf -orientation landscape <output_path>/block_design.pdf
      ```
    - Convert to PNG if the tutorial uses PNG:
      ```bash
      # If ImageMagick/convert available:
      convert block_design.pdf block_design.png
      ```
    - If automated export is not available, flag for manual capture:
      ```
      Block design images requiring manual capture:
      - docs/images/system_bd.png → Open BD in Vivado, File > Export > Block Design as Image
      ```

12. **Regenerate Vivado workflow screenshots** — For GUI step screenshots:
    - Identify which workflow steps changed between versions (new dialogs, renamed options, reorganized menus)
    - Flag each outdated screenshot with instructions for manual recapture:
      ```markdown
      ## Screenshots Requiring Manual Update
      
      | Image Path | Description | Recapture Instructions |
      |---|---|---|
      | `docs/img/create_project.png` | Project creation wizard | File > Project > New, capture Step 1 |
      | `docs/img/run_synth.png` | Synthesis launch | Flow Navigator > Run Synthesis, capture dialog |
      | `docs/img/ip_status.png` | IP Status report | Reports > IP Status, capture window |
      ```

13. **Update image references in documentation** — If any image was renamed or new images added:
    - Update all markdown `![alt](path)` references
    - Update any HTML `<img>` tags
    - Ensure relative paths are correct in the new repo structure
    - Add captions/alt-text reflecting the new version where applicable

14. **Generate text-based alternatives for non-capturable images** — Where screenshots cannot be automatically regenerated, provide equivalent textual documentation:
    - Use Mermaid diagrams for block design topology:
      ```markdown
      ```mermaid
      graph LR
        A[Zynq PS] -->|M_AXI_HPM0| B[AXI SmartConnect]
        B --> C[IP_Core_1]
        B --> D[IP_Core_2]
      ```
      ```
    - Use tables to document IP configuration settings:
      ```markdown
      | Parameter | Value | Notes |
      |---|---|---|
      | CONFIG.DATA_WIDTH | 64 | Increased from 32 in previous version |
      | CONFIG.NUM_LANES | 4 | New parameter in <target_version> |
      ```
    - Use TCL property reports as configuration reference:
      ```tcl
      report_property [get_ips <ip_instance>] -file ip_config_reference.txt
      ```

### Phase 4: Commit and Finalize

15. **Stage and review changes** — Show the user what will be committed:
    ```bash
    git add -A
    git status
    git diff --cached --stat
    ```
    - Present a summary of all changed files
    - Highlight any files that were added or removed
    - **Do NOT commit without user approval**

16. **Commit with descriptive message** (only after user approval):
    ```bash
    git commit -m "Upgrade design from Vivado <source_version> to <target_version>

    - Upgraded all IPs to target version revisions
    - Updated block design scripts with new VLNVs
    - Updated RTL sources for port/signal changes
    - Updated documentation and tutorials
    - Updated build scripts and CI/CD configs
    - Verified synthesis/implementation pass

    IPs upgraded:
    - <ip1>: v<old> -> v<new>
    - <ip2>: v<old> -> v<new>"
    ```

17. **Push or deliver** (if requested by user):
    ```bash
    git push origin upgrade/<target_version>
    ```

## Output Artifacts

- New git branch or repository named with target version
- All design files upgraded and committed
- Updated README and documentation reflecting new version
- Updated build/automation scripts
- Upgrade changelog documenting all changes
- Git log showing clean migration history

## Key Principles

- **Independent execution** — This sub-skill only runs when a GitHub/git repo is explicitly provided
- **Never force-push to main** — Always use a new branch or new repo
- **Never commit without approval** — Stage changes and present to user before committing
- **Update EVERYTHING** — Version strings in scripts, docs, CI/CD, and paths must all be consistent
- **Preserve git history** — Use meaningful commits; don't squash the original repo history
- **Document the migration** — Future developers need to understand what changed and why
- **Reproducibility** — The upgraded repo must be buildable from scratch using only its contents and the target Vivado version
