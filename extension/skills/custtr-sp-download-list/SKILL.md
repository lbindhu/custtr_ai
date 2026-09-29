---
name: custtr-sp-download-list
description: >
  Creates a SharePoint download-links list for a course's training materials. Creates an
  AMD Course Materials SharePoint Links list of course download URLs from a course title,
  part number, and version. Use when the user asks to create a course download list,
  materials list, or SharePoint list of training files on the Course Materials & Software
  site, or mentions part numbers like ver-dm and versioned download.amd.com cust-training
  links.
license: Copyright © Advanced Micro Devices, Inc., or its affiliates. All rights reserved.
  Portions of this content consists of AI generated content.
metadata:
  author: allent
  version: 1.0.0
  category: sharepoint
  tags:
  - sharepoint
  - course-materials
  - downloads
compatibility:
  universal: true
---

# Create course download SharePoint list

Create a **Links** list on the AMD Course Materials & Software site with the seven standard download items for one course. Do not add the list to site navigation.

Site: `https://amdcloud.sharepoint.com/sites/arc/materials`

## Prompt the user

If any of the three values is missing from the current message, ask these questions (verbatim) and wait for answers before creating anything:

1. What is the course title?
2. What is the part number?
3. What is the version number?

Do not invent a part number or version. If the user already supplied all three, do not re-ask.

## How values map

Example from `Designing with the Versal Adaptive SoC: Design Methodology 2026.1`:

- Course title: `Designing with the Versal Adaptive SoC: Design Methodology`
- Part number: `ver-dm` (the `{part}` segment in download URLs)
- Version number: `2026.1`

**List title:** `{course title} {version}`. If the course title already ends with the version number, do not append it again.

**Download URL pattern** (`{part}` and `{version}` substituted as given):

```
https://download.amd.com/opendownload/cust-training/{version}/{part}-{version}-all-rev1.7z
https://download.amd.com/opendownload/cust-training/{version}/{part}-{version}-rev1-lab_files.7z
https://download.amd.com/opendownload/cust-training/{version}/{part}-{version}-wkbp-rev1.7z
https://download.amd.com/opendownload/cust-training/{version}/{part}-{version}-wkb-lab-rev1.7z
https://download.amd.com/opendownload/cust-training/{version}/{part}-{version}-wkb-rev1_VILT.7z
https://amdcloud.sharepoint.com/sites/arc/materials/Lab%20Setup%20Guides/Common/Common%20Lab%20Setup%20Guide%20{version}.pdf
https://amdcloud.sharepoint.com/sites/arc/materials/Virtual%20Machines/Virtual%20Machines.aspx
```

Items and alternative text (in this order):

| Alternative text | File suffix / target | Notes |
|---|---|---|
| Course materials file | `{part}-{version}-all-rev1.7z` | |
| Lab files only | `{part}-{version}-rev1-lab_files.7z` | |
| Participant book | `{part}-{version}-wkbp-rev1.7z` | |
| Lab book | `{part}-{version}-wkb-lab-rev1.7z` | |
| VILT workbooks | `{part}-{version}-wkb-rev1_VILT.7z` | |
| Lab setup guide | Common Lab Setup Guide PDF | |
| Virtual machine | Virtual Machines.aspx | `The same virtual machine is used across all {version} courses so you will only need to download the VM once.` |

List type: SharePoint **Links** list (`BaseTemplate` 103), same as `_VirtualBox Virtual Machine 2018.3`. Fields: `URL` (link + alternative text) and `Comments` (Notes). `OnQuickLaunch` must stay false.

## Run the script

Resolve `scripts/create_course_download_list.py` relative to the folder containing this `SKILL.md` (for example `~/.cursor/skills/custtr-sp-download-list/` or `~/.claude/skills/custtr-sp-download-list/`). Use `python` on Windows; write args as a file invocation — do not use `python -c`.

```bash
python scripts/create_course_download_list.py --title "COURSE TITLE" --part "ver-dm" --version "2026.1"
```

`--title` is the course title **without** requiring the version; the script appends `{version}` when needed.

On PowerShell, pass a quoted title. If the title contains double quotes, wrap the argument in single quotes.

## Auth

Uses the shared Microsoft Graph token at `~/.config/microsoft-graph/token.json` (same as other m365 skills). Graph `Sites.ReadWrite.All` cannot create lists; the script requests a SharePoint `.default` token and creates the list via REST.

If auth fails, tell the user to authenticate with the m365 SharePoint skill (`auth.py`) and stop.

## After create

Report:

- List title
- List URL
- That it is **not** in site navigation
- The seven items (alternative text + URL); include the Virtual machine note

If the list already exists, the script is idempotent: it keeps the list and only adds missing items by alternative text. Tell the user it already existed when that happens.

Do not create a second list with a slightly different title. Do not add the list to left navigation. Do not copy items from `_VirtualBox Virtual Machine 2018.3` (template only).
