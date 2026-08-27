# AMD Lab Development Best Practices
**Sources:** `U:\BestPractices\` — Best Practices - Labs.docx, Best Practices - New Lab Format.docx,
Best Practices - Topic Cluster Guidance.docx, Metrics.pptx, Agreed-On Best Practices.docx,
Lab Validation Checklist.docx, Environment Variable Usage.docx, Script Checklist.docx,
Checklist for 2014.1 Updates.docx, Best Practices - Course Development.docx

---

## Lab Structure (Mandatory Sections — in order)

Every lab must contain these sections in this order:

1. **Abstract** — 1–2 sentences: what the lab covers and why it is relevant to the student.
2. **Objectives** — Concrete, measurable goals the student will accomplish by the end of the lab.
3. **Introduction** — Background information relevant to completing the lab. Explains why the lab is constructed the way it is. Includes design overview (usually with block diagrams).
4. **General Flow** — Graphical flow diagram of the steps. Each box uses `<gerund> <noun>` format (e.g., "Opening Project", "Implementing Design", "Generating Bitstream"). Do NOT use connecting words like "a", "an", "the".
5. **Steps / Instructions / Tasks** — the hands-on procedure.
6. **Summary** — NOT "Conclusion". Summarizes what was accomplished. Conclusions are rarely drawn from labs.
7. **Answers** — Answers to all questions posed within the steps.

---

## Instruction Hierarchy (4 Levels — Strictly Enforced)

```
Step X          — major/broadest aspect of solving the lab problem
  Step X-X      — significant task towards solving the step
    Step X-X-X  — finest granularity; each is a single "clickable" event
```

- **One task per click/action.** If a task contains "and", it is probably two tasks — split it.
- **Maximum 7 sub-entries** at any level of the hierarchy.
- Each instruction must have its own sub-step number.
  - Wrong: "Click this thing, then select XYZ."
  - Correct: "(1) Click this thing. (2) Select XYZ."
  - Exception: "Right-click X then select Y" — right-click is dynamic; if the student stops, the next instruction is unavailable.
- Every instruction must state **WHY** it is being executed.
  - Poor: "Click OK."
  - Better: "Click OK to accept the entered values and close the dialog box."
  - Poor: "Set the range to 64K."
  - Better: "Set the range to 64K even though the defined memory is only 8K — larger ranges require less logic and are easier to meet timing."

---

## Writing Style Rules

- **Active voice always.** Never start an instruction with the prepositional phrase "In...".
  - Wrong: "In the Flow Navigator, click Run Synthesis."
  - Better: "Using the Flow Navigator, click Run Synthesis." or "Under the Flow Navigator, click Run Synthesis."
- **Second person (you).** "Click the OK button" not "The OK button should be clicked."
- **No tool name repetition.** Once the student is working in a tool, do not keep saying "In Vivado..." or "In SDK...". Only call out the tool name when switching between tools or when invoking it for the first time.
- **No version numbers in steps** — except in the lab setup guide and the path used to launch the tool. Use AuthorIT/template variables for version references.
- **Avoid colloquialisms.** Multi-cultural, multi-linguistic audience.
- **Common naming conventions:** MicroBlaze (not uB or Microblaze) in written text. uB is acceptable in file names only.
- **No "also", "additionally"** — these words mean something was forgotten earlier. State it clearly the first time.
- **Lists must be consistent** — all capitalized or none. Repeated nouns can be removed from all items except the last.

---

## Questions in Labs

- Every step should include **probing questions** to keep students thinking about the big picture.
- Questions are meant to stimulate thought — not to test knowledge. State this in the lab FAQ.
- All question answers appear in the **Answers** section at the end of the lab.
- Lab FAQ to include: "Do your best! The questions are meant to stimulate thought, not to test your knowledge. After you've pondered the questions you can find the answers at the end of each lab."

---

## Graphics in Labs

- Every action taken should refer to a graphic — 1:1 relationship, or a multi-step graphic with numbered indicators.
- Screenshots must show only the relevant portion. Use cut-outs or resize dialogs.
- **Blur version numbers** in all screenshots (Smooth, 25% intensity).
- Store PNG and .snagx source files in the Graphics Repository.
- Take screenshots — do NOT copy text from the console.
- File name of PNG must match the lab caption exactly.

---

## General Flow Diagram Rules

- Use `<gerund> <noun>` for each box: "Opening Project", "Simulating Design", "Generating Bitstream".
- Do NOT use connecting words ("a", "an", "the") inside boxes.
- The General Flow in the real AMD template uses a VML PNG right-arrow image (18pt × 15pt) between boxes — not a text arrow character.

---

## Path and File Naming Conventions

- **Keep paths short.** Windows maximum path length: 260 characters.
- **Directory structure:**
  - Vivado: `C:\training\<class_name>\labs\<lab_name>\<board_name>\`
  - Embedded: `C:\training\<class_name>\labs\<lab_name>\<board_name>\<processor>`
  - Support: `C:\training\<class_name>\support\<lab_name>`
- **Class name and lab name must NEVER change** for updates or revisions.
- Target platform in filename: `<board_name>_base` or `<board_name>_<add-on-card>` (e.g., ZCU102_base, Zed_FMC-CE).
- Functional description required in filename — counter-example of BAD: `zynq.bit`.

---

## Environment Variables (Mandatory)

All scripts must use these environment variables — NO hard-coded paths:

| Variable | Purpose |
|---|---|
| `TRAINING_PATH` | Root path to all lab files |
| `XILINX_PATH` | Xilinx/AMD tool installation path |
| `VITIS_PATH` | Vitis installation path |
| `PETALINUX_PATH` | PetaLinux installation path |
| `XILINX_VERSION` | Current tool release version |

- Every lab introduction must note that the CustEd environment differs from a typical environment.
- The Lab Setup Guide must include instructions for customizing global environment variables.
- Tool launching instructions assume desktop/taskbar shortcut icons are available.

---

## Completer Scripts

- A completer script (`<topic>_completer.tcl` or `.py`) builds the lab from the starting point through completion.
- Must include a `make <stepN>` or `make all` function.
- `make all` builds through the last task of the last step.
- Each function/proc corresponds to one and only one instruction.
- Entering a function undoes any behavior it is about to perform (supports successive execution).
- Do NOT copy procs from `helper.tcl` into your own scripts — use them via include/source.
- Use environment variables — NO hard-coded paths.
- Standard proc naming: `createProject`, `createBlockDesign`, `saveProject`, `synthesizeDesign`, `implementDesign`, `generateBitstream`, `exportDesign`.

---

## Lab Scoring Penalties (Reference)

| Issue | Penalty |
|---|---|
| Missing lab introduction | -10 pts |
| Missing step overview | -5 pts |
| Missing instruction description | -3 pts |
| Missing action information ("Click OK" with no explanation) | -1 pt |
| Failure to use existing LRG | -10 pts |
| Unnecessary steps (tool automation available) | -3 pts |
| Erroneous step (outdated or misunderstanding) | -10 pts |
| Misuse of hierarchy | -7 pts |
| Failure to use template variables | -10 pts |
| Blurring version numbers omitted from screenshots | Rework cost |

---

## Topic Cluster Scope

- Labs run **30–60 minutes**. Total topic cluster target: **45–60 minutes**.
- Labs = student-run, in-depth, step-by-step how-to with probing questions.
- Demos = short (5–10 min), instructor-led, shows what CAN be done — not a mini-lab.
- Slides = conceptual/theoretical information only — not step-by-step tool instructions.
- **75% lab & demo, 25% slides** is the delivery ratio target.

---

## Board-Based Lab Rules (verified from MicroBlaze V 2026.1 and Spartan UltraScale+ reference labs)

### CloudShare Users Only — THREE versions (verified across all server labs)

**There are THREE different CloudShare notes. Pick the correct one based on lab type:**

---

**Version 1 — Non-board labs (software only, simulation, Makefile, HLS, AIE sim):**
Single paragraph only. No hardware mention. Source: Versal AI Engine Tool Flow [SHARED] [2025.2]/[2026.1], AIE Makefile Flow [2025.2], Versal Bare-metal [2024.2].

```json
"cloudshare_note": [
  "You are provided with three attempts to finish a lab, where the time allotted to complete each lab is twice the expected completion time. Once the timer starts, you cannot pause the timer. Each lab attempt resets the previous attempt — your work from previous attempts is not saved."
]
```

---

**Version 2 — Board-based labs (requires physical board, older format pre-2026.1):**
Two paragraphs with "hardware-based" wording. Source: MicroBlaze V [2026.1], Spartan UltraScale+ [2025.2], all SCU35 labs. Use this exact text:

```
Paragraph 1:
"You are provided with three attempts to finish a lab, where the time allotted to complete each lab is twice the expected completion time. Once the timer starts, you cannot pause the timer. Each lab attempt resets the previous attempt — your work from previous attempts is not saved."

Paragraph 2:
"Some labs are hardware-based — that is, requiring a board to perform some or all of the lab. Typically, labs requiring hardware only need the target board for the last step. The CloudShare environment does not support these parts of the hardware-based labs as there is no direct way to connect the target board with the cloud-based environment. Hence, these steps need to be performed locally. In order to complete these sections of the hardware-based labs, you need the specified evaluation board and the AMD tools installed locally on your machine. If you do not have the evaluation board, then you can only review that particular step and/or lab. For more details, review the 'Can I run the labs on my local machine?' question available under the On-Demand Labs section of the FAQs in the On-Demand Portal: https://www.amd.com/en/training/customer/adaptive-computing/faq.html."
```

---

**Version 3 — Board-based labs with Board-on-Demand (newer 2026.1 format):**
Two paragraphs with "Board-on-Demand (BoD)" wording. Source: Versal Adaptive SoC Tool Flow [SHARED] [2026.1] (Bindhu). Use when the lab is part of a 2026.1 BoD-enabled course.

```json
"cloudshare_note": [
  "You are provided with three attempts to finish a lab, where the time allotted to complete each lab is twice the expected completion time. Once the timer starts, you cannot pause the timer. Each lab attempt resets the previous attempt — your work from previous attempts is not saved.",
  "Some labs involve hardware-specific tasks that require access to a physical board. While CloudShare does not natively support direct hardware integration, remote access is available via the Board-on-Demand (BoD) portal (https://bod.designlinxhs.com). By registering and following the outlined steps, you can connect to the necessary hardware and complete the lab activities as though you are working on-site. For additional information, please refer to the On-Demand Labs section in the FAQs of the On-Demand Portal: https://www.amd.com/en/training/customer/adaptive-computing/faq.html."
]
```

**Which version to use:**

| Lab type | CloudShare version |
|---|---|
| Software only — no board at all (AIE sim, HLS, Makefile, Vivado only) | Version 1 — single paragraph |
| Board required, SCU35/ZCU/VCK boards, standard course format | Version 2 — two paragraphs, hardware-based wording |
| Board required, 2026.1 course with BoD portal support | Version 3 — two paragraphs, Board-on-Demand wording |

---

### Board step intro — exact wording

Use this pattern at the start of the board bring-up step intro:

> "If you have the hardware available, you can proceed with the following steps; otherwise, you can review this section to understand the process. For On-Demand/CloudShare users, if you have the evaluation board locally available, then copy the required project files to the local path and proceed with the steps below. You can also review the 'Can I run the labs on my local machine?' question available under the FAQ section of the On-Demand Portal. Otherwise, you can just review (without performing) these instructions."

### SCU35 Board Bring-Up — standard substeps (exact from reference lab)

The SCU35 board image goes **inside** the "Bring up the SCU35 board" action — after the Note about the board overview. Never place it before or outside this action.

```json
{"action": "Bring up the SCU35 board."},
{"note": "Note: The figure below of the SCU35 evaluation board enumerates some of its more popular features..."},
{"image": "SCU35 Overview.png", "caption": "SCU35 Overview"},
{"substep": "Ensure that the power connector is not plugged in (1)."},
{"substep": "Connect the micro-USB JTAG/UART cable between the board and the host (2)."},
{"substep": "Locate J35 on the board (3). This header configures the Spartan UltraScale+ device's boot mode, which should be set to JTAG."},
{"substep": "Set J35 as shown below to ensure that the board is configured to boot from JTAG."},
{"lab1_continue": "Boot Mode  |  Mode Pins [3:0]  |  Mode J35\nJTAG  |  101 / 0x5  |  Open\nQSPI SPI_24  |  100 / 0x4  |  Jumped"},
{"substep": "Plug in the power connector (1). You are now ready to configure the board."},
{"action": "Determine which COM port connects to the USB serial port on the development board."},
{"substep": "Identify the appropriate channel for the USB as follows: For those using the Customer Education VM, select Devices > USB > Xilinx SCU35 in the VirtualBox Manager."},
{"image": "Selecting the Hardware Target.png", "caption": "Selecting the Hardware Target"},
{"substep": "This ensures that the VM has access to the USB connection and proper USB port is allowed to cross the host/VM threshold."}
```

### GTKTerm — merge with board step, not a separate step

GTKTerm setup and board bring-up belong in the **same step** because GTKTerm cannot be configured until the board is powered on and USB is connected (COM port only appears after board connection). Use a `{"continue": "..."}` paragraph to introduce GTKTerm within the same step.

GTKTerm exact steps (from MicroBlaze V 2026.1 reference lab):

```json
{"continue": "GTK Term is an interface that only supports serial port/UART communications..."},
{"action": "Launch GTKTerm and set the port configuration."},
{"substep": "Click the GTKTerm icon ( ) from the quick launch toolbar. Alternatively, GTKTerm can be launched from a Linux terminal window (< Ctrl + Alt + T >) and entering:"},
{"command": "[host] $ sudo gtkterm"},
{"note": "Note: While the application will run as a regular user, you must be a super user to access the ports. When the GTKTerm window opens, perform the following."},
{"substep": "Select Configuration > Port to open the Configuration dialog box."},
{"substep": "Identify the port associated with your board and set the port as /dev/ttyUSBx (where x could be 0, 1, 2, 3, etc.)"},
{"substep": "Set the baud rate to 115200."},
{"substep": "Leave the rest of the settings at their default."},
{"image": "Opening GtkTerm and Selecting the Port Configuration.png", "caption": "Opening GtkTerm and Selecting the Port Configuration"},
{"note": "[Optional]: You can save these settings..."},
{"substep": "Click OK to save the settings and leave the terminal open."},
{"action": "Enable auto CR/LF mode."},
{"substep": "GTKTerm is a terminal emulator that supports automatic translation of CR (carriage return) characters to LF (line feed) characters and vice versa."},
{"substep": "Select Configuration > CR LF auto to enable auto CR/LF mode."},
{"image": "Enabling CR LF Auto in GTKTerm.png", "caption": "Enabling CR/LF Auto in GTKTerm"},
{"note": "Note: This step is optional, but it will ensure that the serial messages appear aligned on the terminal."}
```

### Images to copy from reference labs for SCU35 board labs

Source: `C:\Harsha\Course Updates 2026.1\MicroBlaze V Soft Processor Implementation [2026.1].docm`

| Image in docm | Caption | Used in |
|---|---|---|
| image34.png | SCU35 Overview | Inside "Bring up the SCU35 board" action |
| image35.png | Selecting the Hardware Target | Inside "Determine which COM port" action |
| image38.png | Opening GtkTerm and Selecting the Port Configuration | Inside GTKTerm step |
| image39.png | Enabling CR/LF Auto in GTKTerm | Inside "Enable auto CR/LF mode" action |

Copy these to: `C:\Users\hnandebo\.claude\skills\custtr-lab-doc\images\`

### Dialog box settings — use table format

When a step sets multiple fields in a dialog box, use a `{"table": {...}}` instead of individual substeps. This matches AMD lab style for dialog box configuration:

```json
{"substep": "Set the following in the Program Configuration Memory Device dialog:"},
{"table": {
  "rows": [
    ["Setting", "Value"],
    ["Configuration file", "$TRAINING_PATH/xapp1410_multiboot/lab/pdi/fallback.pdi"],
    ["Offset", "0x00180000"],
    ["Address range", "Entire Configuration Memory Device"],
    ["Actions", "Erase, Blank Check, Program, Verify"]
  ],
  "widths": [3000, 6360]
}},
{"substep": "Click OK. Wait for the Flash programming successful message before continuing."}
```

### Tool Closing Steps — MANDATORY (verified from MicroBlaze V 2026.1 and Spartan UltraScale+ reference labs)

Every lab must end with closing steps for all tools that were opened. Add these as the final actions in the last step. Use the exact wording from the reference labs.

**Vivado Design Suite closing:**
```json
{"action": "Close the Vivado Design Suite."},
{"substep": "Select File > Exit. The Exit Vivado dialog box opens."},
{"image": "Exit Vivado Dialog Box.png", "caption": "Exit Vivado Dialog Box"},
{"substep": "If you are asked to save the project or a portion of the project, select whichever elements you want to save, then click Save; otherwise, click Don't Save."}
```

**Vitis Unified IDE closing:**
```json
{"action": "Close the Vitis Unified IDE."},
{"substep": "Select File > Close Window to close the tool."}
```

**GTKTerm output + closing (board-based labs only):**
```json
{"substep": "Select the GTKTerm serial terminal to view the output from the application."},
{"image": "Output of Application.png", "caption": "Output of Application"},
{"action": "Close the GTKTerm application."}
```

**Board power off (board-based labs only — always before closing tools):**
```json
{"action": "Power off the evaluation board."}
```

**Terminal window closing:**
```json
{"action": "Close the terminal window."},
{"substep": "Return to the terminal window."},
{"substep": "Enter exit to close the terminal window."},
{"command": "exit"}
```

**Images available in `images/` folder for closing steps:**

| File | Caption | Used at | Has image? |
|------|---------|---------|-----------|
| `Exit Vivado Dialog Box.png` | Exit Vivado Dialog Box | After "Select File > Exit" substep in Vivado | ✅ Yes |
| `Output of Application.png` | Output of Application | After GTKTerm shows application output, before closing | ✅ Yes |
| Vitis Unified IDE closing | — | "Select File > Close Window" — text only, no image in reference labs | ❌ No image |
| GTKTerm closing | — | "Close the GTKTerm application" — text only, no image | ❌ No image |
| Terminal closing | — | "Return to terminal, enter exit" — text only, no image | ❌ No image |
| Board power off | — | "Power off the evaluation board" — text only, no image | ❌ No image |

Source: `Y:\Publishing\Harshavardhan\Lab (Word)\MicroBlaze V Soft Processor Implementation [2026.1]` (image24.png = Exit Vivado, image41.png = Output of Application)

**Verified across 767 labs, 16 authors — complete server scan results:**

| Closing Step | Found in labs | Has image in reference labs? |
|---|---|---|
| Close the Vitis Unified IDE | 250+ labs across all authors | ❌ Text only — `File > Close Window` |
| Close the Vivado Design Suite | 200+ labs across all authors | ✅ Yes — `Exit Vivado Dialog Box.png` |
| Close the GTKTerm | ~20 labs (board-based only) | ✅ Yes — `Output of Application.png` (GTKTerm output shown before closing) |
| Power off the evaluation board | ~25 labs (board-based only) | ❌ Text only |
| Close terminal window | Present in many labs | ❌ Text only — `Return to terminal; enter exit` |

**Key finding:** Closing steps are consistent across ALL 767 labs. Only two have images — Exit Vivado dialog and GTKTerm output. All others are text only. This is confirmed across every author folder on the server.

**Verification rule — MANDATORY:** When checking for images or wording related to any step, always go through ALL 19 author folders on the server using `-LiteralPath` in PowerShell (required because folder names contain brackets like `[2025.2]`). Never limit to a subset.

**Order for board-based labs (last step, after application runs):**
1. Close GTKTerm
2. Power off the evaluation board
3. Close the Vitis Unified IDE (or Vivado, whichever was used)
4. Close the terminal window
5. [Optional] Clean up the file system (see below)

**Order for ALL labs (non-board, software-only, command-line, Makefile-based):**
1. Close the Vitis Unified IDE (or Vivado, whichever was used) — `File > Close Window`
2. Close the terminal window — `Return to terminal → enter exit`
3. [Optional] Clean up the file system — ALWAYS last

**Rule — verified from reference labs:** The clean-up step is ALWAYS the very last action, after all tool and terminal closing steps. Never put clean-up before closing the tools. The correct order is always: Close tool → Close terminal → Clean up.

**This applies to ALL lab types including command-line / Makefile labs.** Even if the student only used make and vitis_analyzer, there is still a terminal open. Always close it before clean-up.

**Rule:** As new tools are encountered while generating labs, add their closing steps here. Never leave a lab without closing all tools that were opened during the session.

---

### Clean Up the File System — MANDATORY CLOSING STEP (Optional for student)

Every lab must include this as the final action. It is optional for the student and must not be included for CloudShare environments. Use the generic template below — replace `[lab_folder]` with the actual lab folder name for that specific lab.

**Intro text (always include before the step):**
> Some systems (particularly VMs) may be memory constrained. Removing the workspace frees a portion of the disk space, allowing other labs to be performed. You can delete the directory containing the lab you just ran by using the graphical interface or the command-line interface. You can choose either mechanism. Both processes will recursively delete all the files in the $TRAINING_PATH/[lab_folder] directory.

**Config JSON template (replace `[lab_folder]` with actual folder name):**

```json
{"action": "[Optional] [Only for local VMs — not for CloudShare] Clean up the file system."},
{"continue": "Some systems (particularly VMs) may be memory constrained. Removing the workspace frees a portion of the disk space, allowing other labs to be performed. You can delete the directory containing the lab you just ran by using the graphical interface or the command-line interface. You can choose either mechanism. Both processes will recursively delete all the files in the $TRAINING_PATH/[lab_folder] directory."},
{"substep": "Using the GUI:"},
{"substep": "Navigate to $TRAINING_PATH/[lab_folder]."},
{"substep": "Select [lab_folder]."},
{"substep": "Press <Delete>."},
{"lab1_continue": "-- OR --"},
{"substep": "[Linux users]: Using the command line:"},
{"substep": "Press <Ctrl + Alt + T> to open a terminal window."},
{"substep": "Enter the following command to delete the contents of the workspace:"},
{"command": "[host] $ rm -rf $TRAINING_PATH/[lab_folder]"}
```

**Rules:**
- Always add this as the very last action in the last step of every lab
- Replace `[lab_folder]` with the actual training folder name used in that lab (e.g. `hls_dct`, `xapp1410_multiboot`, `single_kernel_vector`)
- The `[Optional] [Only for local VMs — not for CloudShare]` prefix is mandatory — do not remove it
- Never hard-code a path — always use `$TRAINING_PATH/[lab_folder]`

---

### Step structure rules for board-based labs

1. **File preparation is a separate first step** — copy/setup of lab files runs on host only, before board is connected. Step name format: "Setting Up the Lab Files".
2. **General Flow max per row = 5** for labs with 5 steps. Use 3 per row for 6 steps.
3. **Training path** — always use `$TRAINING_PATH/xapp1410_multiboot/lab/` for lab files and `$TRAINING_PATH/xapp1410_multiboot/support/` for support files. TRAINING_PATH = `/home/amd/training` in CustEd_VM/CloudShare.
4. **Vivado launch** — always include both icon method and terminal method: `source /opt/amd/2025.2/Vivado/settings64.sh; vivado`

---

## Lab Validation Checklist (CD Responsibilities)

- All labs reviewed by PM.
- Starting points generated using scripts (SVN/LabBuilder).
- Design Doc, Lab Setup Guide, Spec Sheet, Assessment Sheet all updated and copy-edited.
- Lab files (training.zip) available.
- Customer-ready files posted on ARC are correct.

---

## Audience Skill Levels

| Level | Instruction Style |
|---|---|
| Beginner | Every step detailed; every action has a graphic |
| Intermediate | Use LRG for first occurrence; ALRG for subsequent references |
| Advanced/Expert | Extensive use of ALRG; basic tasks not spelled out |
