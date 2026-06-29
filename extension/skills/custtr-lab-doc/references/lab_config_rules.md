# Lab Config Rules — MANDATORY

Read this file before writing ANY lab_config.json.

---

## Rule 1: ALWAYS start from the base template

Every new lab_config.json MUST be built from:

```
C:\Users\hnandebo\.claude\skills\custtr-lab-doc\references\lab_config_template.json
```

Never build from scratch. Open the template, copy it, and fill in the content.
This ensures every lab has all required structural elements without exception.

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
