# Lab Config Rules — MANDATORY

Read this file AND `lab_development_best_practices.md` before writing ANY lab_config.json.

---

## File Server — Lab Templates and Reference Documents

All lab templates, reference documents, and published lab Word files are stored on the AMD file server:

```
\\atlvauthorapp02
```

This server is accessed via a mapped drive. The drive letter varies per user machine — on this machine it is mapped as `Y:\`. Always use the UNC path `\\atlvauthorapp02` when referring to server locations so the instructions work for all users regardless of their drive letter mapping.

**Key server paths:**

| Path | Contents |
|------|----------|
| `\\atlvauthorapp02\Data\Publishing\` | All published lab Word documents — organized by author name, then lab title |
| `\\atlvauthorapp02\Data\Publishing\[Author]\Lab (Word)\[Lab Title]\English (United States)\` | Individual lab `.docm` files and associated images |

**How to find a reference lab:**

```
\\atlvauthorapp02\Data\Publishing\Harshavardhan\Lab (Word)\
\\atlvauthorapp02\Data\Publishing\Shashank\Lab (Word)\
\\atlvauthorapp02\Data\Publishing\Allen\Lab (Word)\
\\atlvauthorapp02\Data\Publishing\Bindhu\Lab (Word)\
... (one folder per author)
```

**Board-based SCU35 reference lab (primary):**
```
\\atlvauthorapp02\Data\Publishing\Shashank\Lab (Word)\Designing with the Spartan UltraScale+ FPGA Architecture Lab Workbook [2025.2]\English (United States)\Designing with the Spartan UltraScale+ FPGA Architecture Lab Workbook [2025.2].docm
```

**When reading reference labs:** First check what drive letter the server is mapped to on the current machine (`net use` or PowerShell `Get-PSDrive`), then construct the full path. Never hard-code `Y:\` — always verify the mapping first.

---

## XAPP1410 MultiBoot and Fallback — Completed Lab Reference

A fully built lab exists at:
```
C:\Users\hnandebo\OneDrive - Advanced Micro Devices Inc\Desktop\Lab_creation\XAPP1410_MultiBoot_Fallback_FINAL_v7.docm
```
Config saved at: `C:\Users\hnandebo\.psas-ai\shared\lab_config.json`

This lab was built over multiple sessions and is the validated reference for:
- SCU35 board-based labs
- Hardware Manager flash programming flow
- GTKTerm + board setup merged into one step
- CloudShare note (2026.1 format)
- 5-step structure with separate "Setting Up the Lab Files" first step

---

---

## Rule 0: ALWAYS select the correct CloudShare note FIRST

Before choosing a template or writing any config, determine which CloudShare version applies:

| Condition | CloudShare version to use |
|---|---|
| No board at all — AIE sim, HLS, Makefile, Vivado, QEMU only | **Version 1** — single paragraph, no hardware mention |
| Lab has any step on a physical board — SCU35, ZCU, VCK, VEK | **Version 2** — two paragraphs, "hardware-based" wording |
| Lab has board steps AND user targets Board-on-Demand (BoD) | **Version 3** — two paragraphs, "Board-on-Demand" wording |

Full wording for all three versions is in `lab_development_best_practices.md` under "CloudShare Users Only — THREE versions".

---

## Rule 1: ALWAYS start from the correct template — choose based on lab type

There are TWO templates. Pick the right one BEFORE writing the config:

---

### Template A — Non-board lab (software only, no physical hardware required)

```
C:\Users\hnandebo\.claude\skills\custtr-lab-doc\references\lab_config_template.json
```

**Use when:** Lab runs entirely in software — Vivado, Vitis, AIE simulation, HLS, QEMU, Makefile flows. No physical board is connected. CloudShare users can complete 100% of the lab.

**CloudShare note — single paragraph ONLY (verified from Versal AI Engine Tool Flow [SHARED] [2025.2] and [2026.1], AIE Makefile Flow [2025.2]):**

```json
"cloudshare_note": [
  "You are provided with three attempts to finish a lab, where the time allotted to complete each lab is twice the expected completion time. Once the timer starts, you cannot pause the timer. Each lab attempt resets the previous attempt — your work from previous attempts is not saved."
]
```

Do NOT add the hardware paragraph. Non-board labs have only this one paragraph.

**Step structure:** Steps start directly with the tool (e.g. "Launching the Vitis Unified IDE", "Creating a Vivado Project").

---

### Template B — Board-based lab (requires physical evaluation board)

```
C:\Users\hnandebo\.claude\skills\custtr-lab-doc\references\lab_config_template_board.json
```

**Use when:** Lab requires a physical board for any step — JTAG programming, QSPI flash programming, hardware boot validation, running application on board, hardware debug. CloudShare users must have the board locally or use Board-on-Demand.

**CloudShare note — TWO paragraphs, hardware-based wording (verified from MicroBlaze V [2026.1], Spartan UltraScale+ [2025.2]):**
Use for standard board-based labs. For 2026.1 BoD-enabled courses, use Version 3 from `lab_development_best_practices.md`.

```json
"cloudshare_note": [
  "You are provided with three attempts to finish a lab, where the time allotted to complete each lab is twice the expected completion time. Once the timer starts, you cannot pause the timer. Each lab attempt resets the previous attempt — your work from previous attempts is not saved.",
  "Some labs are hardware-based — that is, requiring a board to perform some or all of the lab. Typically, labs requiring hardware only need the target board for the last step. The CloudShare environment does not support these parts of the hardware-based labs as there is no direct way to connect the target board with the cloud-based environment. Hence, these steps need to be performed locally. In order to complete these sections of the hardware-based labs, you need the specified evaluation board and the AMD tools installed locally on your machine. If you do not have the evaluation board, then you can only review that particular step and/or lab. For more details, review the \"Can I run the labs on my local machine?\" question available under the On-Demand Labs section of the FAQs in the On-Demand Portal: https://www.amd.com/en/training/customer/adaptive-computing/faq.html."
]
```

**Step structure:** Always starts with:
1. **"Setting Up the Lab Files"** — host-only file copy step (no board needed)
2. **"Connect and Power Up the [Board] Board"** — board bring-up + GTKTerm merged into one step
3. Remaining lab-specific steps

**Pre-filled blocks in Template B (do not rewrite — use as-is):**
- CloudShare Users Only (both paragraphs, exact wording from reference labs)
- Understanding the Lab Environment (TRAINING_PATH, clean Tcl note)
- Board bring-up substeps (power off → USB cable → boot mode jumper → power on)
- Boot mode table (JTAG/QSPI settings)
- Determine COM port substep
- GTKTerm full setup (sudo gtkterm → port → baud → CR LF auto)
- GTKTerm images: `Opening GtkTerm and Selecting the Port Configuration.png` and `Enabling CR LF Auto in GTKTerm.png`

**Images available in the local images folder for board labs:**

| File | Caption | Step |
|------|---------|------|
| `SCU35 Overview.png` | SCU35 Overview | Inside "Bring up the SCU35 board" action |
| `Selecting the Hardware Target.png` | Selecting the Hardware Target | After COM port substep |
| `Opening GtkTerm and Selecting the Port Configuration.png` | Opening GtkTerm and Selecting the Port Configuration | After GTKTerm port setup |
| `Enabling CR LF Auto in GTKTerm.png` | Enabling CR/LF Auto in GTKTerm | After CR LF auto substep |

Source for these images: `C:\Harsha\Course Updates 2026.1\MicroBlaze V Soft Processor Implementation [2026.1].docm` (images 34, 35, 38, 39)

**Dialog box settings — use table format:**

When a step sets multiple fields in a dialog box, use a table, not individual substeps:

```json
{"substep": "Set the following in the [Dialog Name] dialog:"},
{"table": {
  "rows": [
    ["Setting", "Value"],
    ["Configuration file", "$TRAINING_PATH/lab/pdi/filename.pdi"],
    ["Offset", "0x00000000"],
    ["Address range", "Configuration File Only"],
    ["Actions", "Erase, Blank Check, Program, Verify"]
  ],
  "widths": [3000, 6360]
}},
{"substep": "Click OK and wait for the success message before continuing."}
```

**Training path structure for board labs:**
- Lab files: `$TRAINING_PATH/[lab_folder]/lab/`
- Support files: `$TRAINING_PATH/[lab_folder]/support/`
- TRAINING_PATH = `/home/amd/training` in CustEd_VM and CloudShare

**Vivado launch — always include both methods:**

```json
{"substep": "Click the Vivado icon ( ) from the taskbar."},
{"note": "Note: It takes a few moments to launch. The order of the icons in your environment may be different."},
{"substep": "Alternatively, open the Linux terminal window (<Ctrl+Alt+T>) and enter the following:"},
{"command": "source /opt/amd/2025.2/Vivado/settings64.sh; vivado"},
{"note": "Note: This installation path is valid for the CustEd VM and CloudShare environments. Use the proper path for your environment."}
```

**Reference labs for board-based content (SCU35):**
- `C:\Harsha\Course Updates 2026.1\MicroBlaze V Soft Processor Implementation [2026.1].docm` — PRIMARY reference for board bring-up and GTKTerm steps
- `Y:\Publishing\Shashank\Lab (Word)\Designing with the Spartan UltraScale+ FPGA Architecture Lab Workbook [2025.2]` — Secondary reference

Never rewrite board bring-up or GTKTerm steps from scratch — copy from Template B or the reference labs above.

---

## Rule 2: Elements that MUST appear in every lab

These are non-negotiable — every lab config must include ALL of them:

| Element | Where | Why |
|---|---|---|
| `"toc": true` | Top level | Generates Table of Contents |
| `"cloudshare_note"` | Top level | Required for CloudShare labs |
| `"shared": true` | Top level | Standard for all labs |
| Nomenclature table | Introduction | Always last item in introduction |
| Design Parameters table | Introduction | After background paragraphs |
| `"general_flow"` + `"general_flow_per_row"` | Top level | Flow diagram on page 2 |
| `{"body_heading": "..."}` | First instruction in each step | Informational context before steps |
| `{"question": "..."}` | At end of relevant steps | At least 1–2 questions per lab |
| `"answers"` array | After `"summary"` | One entry per inline question |

---

## Rule 3: Image database

Before writing the config, run:

```bash
python "C:/Users/hnandebo/.claude/skills/custtr-lab-doc/scripts/fetch_github_images.py" <github_url> --clear
```

Then read `C:/Users/hnandebo/.claude/skills/custtr-lab-doc/images/_last_fetch.json`
to see which images were downloaded.

Place images in the config using:
```json
{"image": "filename.png", "caption": "Descriptive caption"}
```

Image placement guide:
- Block diagram / architecture image → Introduction (after background paragraphs)
- Hardware/system diagram → Introduction (last in intro, before nomenclature)
- Step-specific screenshot → Inside the relevant step's instructions
- Analysis / results screenshot → Step 5 or final analysis step

---

## Rule 4: Question placement

- Add 1–2 questions per lab — not every step needs one
- Place at the END of the relevant step's instructions
- Format: `{"question": "Question text? Hint: Hint text."}`
- The `Hint:` word renders bold automatically
- Always add the answer to the `"answers"` array after `"summary"`

---

## Rule 5: Step structure pattern

Every step must follow this pattern:

```json
{
  "title": "Step N Title",
  "intro": "One sentence goal.",
  "instructions": [
    {"body_heading": "Understand [Topic]"},
    {"continue": "Explanatory text with no step number."},

    {"stepxx": "N-1", "text": "Bold main step."},
    {"stepxxx": "N-1-1", "text": "Plain sub-step."},
    {"host_cmd": "exact-command"},
    {"continue": "Note: Expected output."},

    {"stepxx": "N-2", "text": "Next main step."},
    ...
    {"question": "Optional question at the END only."}
  ],
  "outcome": "What the user sees when complete."
}
```

Never skip `body_heading` on the first instruction of a step.
Never put a question in the middle of instructions — always at the end.

---

## Rule 6: Build commands (always the same)

```bash
python "C:/Users/hnandebo/.claude/skills/custtr-lab-doc/scripts/build_lab.py" \
  --config "C:/Users/hnandebo/.psas-ai/shared/lab_config.json" \
  --template "C:/Users/hnandebo/.claude/skills/custtr-lab-doc/references/amd_lab_template.docm" \
  --output "C:/Users/hnandebo/.psas-ai/shared/lab_output.docm"
```

Copy to Desktop:
```bash
python -c "import shutil; shutil.copy2('C:/Users/hnandebo/.psas-ai/shared/lab_output.docm', 'C:/Users/hnandebo/OneDrive - Advanced Micro Devices Inc/Desktop/<LabTitle>.docm')"
```
