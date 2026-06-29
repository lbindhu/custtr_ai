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
