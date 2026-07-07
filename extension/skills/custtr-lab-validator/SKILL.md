---
name: custtr-lab-validator
description: "Validates AMD training lab docx files by executing each step on a VM."
---

# Lab Validator Skill

## What this skill does

Given an AMD training lab `.docm/.docx` file, this skill:
1. Parses the lab doc and extracts all steps, commands, figures, and expected outputs
2. Auto-detects execution mode (local Claude Code vs VS Code SSH remote on VM)
3. Asks minimal questions (lab file, board if needed, VM details if local + first time)
4. Executes every step on the VM via SSH or directly
5. Verifies outputs against what the lab doc expects
6. Compares screenshots against lab doc figures
7. Produces an annotated DOCX with pass/fail per step, comments, and tracked changes

---

## Step 0 — Auto-detect execution mode

Run this to check if we're already on the VM:

```bash
which vitis-run 2>/dev/null || which vivado 2>/dev/null || echo "NOT_ON_VM"
```

- If output contains a path → **Remote Mode** (already on VM, no SSH needed)
- If output is `NOT_ON_VM` → **Local Mode** (need SSH to reach VM)

Store mode as `EXEC_MODE = "remote" | "local"`.

---

## Step 1 — Find lab file

Scan current directory and `C:/Training/Temp/` for `.docm` and `.docx` files:

```bash
find "C:/Training/Temp" -name "*.docm" -o -name "*.docx" 2>/dev/null | grep -v "~\$"
```

Also check current working directory.

Present list to user and ask:
> "Which lab file would you like to validate?"

If only one file found → use it automatically without asking.

---

## Step 2 — Copy and parse lab doc

Copy to shared volume:
```bash
cp "<lab_file_path>" "~/.psas-ai/shared/lab_current.docm"
```

Extract full text and figures using Python:
```bash
python3 -c "
import zipfile, re, os, json

shared = os.path.expanduser('~/.psas-ai/shared')
path = f'{shared}/lab_current.docm'

# Extract text
with zipfile.ZipFile(path) as z:
    with z.open('word/document.xml') as f:
        xml = f.read().decode('utf-8')
text = re.sub(r'<[^>]+>', ' ', xml)
text = re.sub(r'\s+', ' ', text).strip()

# Extract figures
out_dir = f'{shared}/lab_figures'
os.makedirs(out_dir, exist_ok=True)
with zipfile.ZipFile(path) as z:
    imgs = [f for f in z.namelist() if f.startswith('word/media/')]
    for img in imgs:
        fname = os.path.basename(img)
        with z.open(img) as f:
            with open(f'{out_dir}/{fname}', 'wb') as o:
                o.write(f.read())

print(f'FIGURES:{len(imgs)}')
print('TEXT_START')
print(text[:50000])
"
```

From the extracted text, identify:
- **Tool type**: search for `vitis-run`, `v++`, `vivado -mode`, `vitis -w` keywords
- **Board references**: search for `ZCU104`, `VCK190`, `xczu7ev`, `xcvc1902`
- **All steps**: numbered sequences starting with step headings
- **All commands**: lines starting with `[host]$` or inside code blocks
- **Expected outputs**: phrases like "Results are good", "Pass!", "observe the", "note that"
- **Figure references**: "Figure 1-X" occurrences

Store parsed structure as a step list.

---

## Step 3 — Ask board type (only if needed)

Check if any extracted step contains board-specific part numbers or board names.

If yes, ask:
> "This lab targets a specific board. Which board are you using?"
> - ZCU104 (xczu7ev-ffvc1156-2-e)
> - VCK190 (xcvc1902-vsva2197-2MP-e-S)

If no board reference found → skip this question entirely.

---

## Step 4 — VM connection setup (Local Mode only)

If `EXEC_MODE = "local"`:

Check if config exists:
```bash
cat "~/.claude/custtr-lab-validator-config.json" 2>/dev/null
```

If config missing or incomplete, ask:
> "First time setup — what is your VM IP address?"
> "What is the path to your SSH private key? (e.g. ~/.ssh/id_ed25519_vm)"
> "What is the VM username? (default: amd)"

Save config:
```bash
python3 -c "
import json, os
config = {'vm_ip': '<IP>', 'ssh_key': '<KEY_PATH>', 'vm_user': '<USER>'}
with open(os.path.expanduser('~/.claude/custtr-lab-validator-config.json'), 'w') as f:
    json.dump(config, f, indent=2)
print('Config saved')
"
```

Define SSH command prefix for all subsequent remote commands:
```
SSH_CMD = "ssh -i <ssh_key> -o StrictHostKeyChecking=no <vm_user>@<vm_ip>"
```

If `EXEC_MODE = "remote"` → `SSH_CMD = ""` (run directly)

---

## Step 5 — Verify VM environment

Run on VM:
```bash
<SSH_CMD> "
echo TRAINING_PATH=\$TRAINING_PATH
which vitis-run 2>/dev/null && echo VITIS_OK || echo VITIS_MISSING
which vivado 2>/dev/null && echo VIVADO_OK || echo VIVADO_MISSING
tmux ls 2>/dev/null || tmux new-session -d -s lab
echo TMUX_OK
"
```

If `TRAINING_PATH` is empty → set it:
```bash
<SSH_CMD> "echo 'export TRAINING_PATH=/home/amd/training' >> ~/.bashrc"
```

---

## Step 6 — Setup VNC (for GUI steps)

Check if VNC is running:
```bash
<SSH_CMD> "vncserver -list 2>/dev/null | grep ':1' || echo VNC_DOWN"
```

If VNC_DOWN → start it:
```bash
<SSH_CMD> "vncserver :1 2>&1 | tail -2"
```

Launch xterm on VNC display for user to watch:
```bash
<SSH_CMD> "export DISPLAY=:1 && xterm -title 'Lab Validator' -fa 'Monospace' -fs 12 -geometry 200x50+0+0 -e 'tmux attach -t lab' &"
```

Remind user:
> "VNC is running. Connect to localhost:5901 via VNC Viewer to watch execution live."
> "Make sure you have the SSH tunnel running: `ssh -L 5901:localhost:5901 <user>@<vm_ip> -N`"

---

## Step 7 — Execute steps one by one

For each parsed step, determine step type and execute accordingly:

### Type A — Source/environment setup
Commands like `source /opt/amd/.../settings64.sh`:
```bash
<SSH_CMD> "tmux send-keys -t lab 'source /opt/amd/2025.2/Vitis/settings64.sh' Enter"
```

### Type B — CLI command (`[host]$` prefix)
Extract the command, substitute board-specific values, run via tmux:
```bash
<SSH_CMD> "tmux send-keys -t lab '<command>' Enter"
sleep <estimated_wait>
<SSH_CMD> "tmux capture-pane -t lab -p | tail -20 > /tmp/step_output.txt"
<SSH_CMD> "cat /tmp/step_output.txt"
```

Wait times by command type:
- `vitis-run --csim` → 60s
- `v++ -c --mode hls` → 120s
- `vitis-run --cosim` → 180s
- `vitis-run --impl` → 600s
- `vivado` commands → 60-300s

### Type C — File edit
Apply change directly:
```bash
<SSH_CMD> "sed -i 's/<old>/<new>/' <file>"
```
Or write file content directly.

### Type D — GUI step (launch app / click / review)
```bash
<SSH_CMD> "export DISPLAY=:1 && <gui_command> &"
sleep 10
# Take screenshot
<SSH_CMD> "export DISPLAY=:1 && scrot /tmp/step_screenshot.png"
scp -i <ssh_key> <user>@<vm_ip>:/tmp/step_screenshot.png "~/.psas-ai/shared/step_screenshot.png"
```
Then `Read` the screenshot to verify visually.

### Type E — Review/verify step
Read the relevant report file or output:
```bash
<SSH_CMD> "cat <report_file>"
```
Compare against expected output described in lab doc.

---

## Step 8 — Verify each step output

After each step, check:

**For CLI steps:**
- Look for success keywords: `Pass!`, `Results are good`, `PASS`, `elapsed time`, `Successfully`
- Look for failure keywords: `ERROR`, `FAILED`, `error generated`
- Compare numeric values (latency, resources) if lab doc specifies expected values

**For figure steps:**
- Extract corresponding lab doc figure (from `lab_figures/`)
- Read both the screenshot and lab figure
- Compare: layout, key values, UI elements present
- Note any differences

**Record result per step:**
```
STEP_RESULTS = [
  {
    "step": "2-2",
    "description": "Run C Simulation",
    "status": "PASS" | "FAIL" | "WARN",
    "actual_output": "...",
    "expected_output": "...",
    "figure_match": True | False | None,
    "notes": "..."
  }
]
```

---

## Step 9 — Generate validation report in chat

Print summary table:

```
Lab Validation Report: <lab_name>
Board: <board>
Date: <date>

| Step | Description | Status | Notes |
|------|-------------|--------|-------|
| 1-1  | Launch Vitis | ✅ PASS | |
| 2-2  | C Simulation | ✅ PASS | "Pass!" confirmed |
| 2-4  | Synthesis report | ⚠️ WARN | Figure 1-14: pragma syntax differs |
| ...  | ...          | ...    | ... |

Issues Found: <N>
Figures Verified: <N>/<total>
```

---

## Step 10 — Annotate DOCX with results

Use Python to add comments to the DOCX at each step location:

```bash
python3 ~/.claude/skills/custtr-lab-validator/scripts/annotate_docx.py \
  "~/.psas-ai/shared/lab_current.docm" \
  "~/.psas-ai/shared/lab_results.json" \
  "~/.psas-ai/shared/lab_validated.docm"
```

The annotation script expects `lab_results.json` as a flat list (not nested under a key):
```json
[{"step": "1-3", "description": "...", "status": "PASS", "notes": "...", "actual_output": "..."}]
```

The annotation script:
- Adds a ✅/⚠️/❌ comment at each step with actual output
- Adds strikethrough + new text where steps need correction
- Adds figure comparison notes at each figure reference
- Adds a validation summary at the top of the document

Copy annotated file back:
```bash
cp "~/.psas-ai/shared/lab_validated.docm" "<original_dir>/<lab_name>_VALIDATED.docm"
```

Tell user:
> "Validation complete. Annotated lab doc saved to: <path>"

---

## Part numbers by board

| Board | Part Number |
|---|---|
| ZCU104 | xczu7ev-ffvc1156-2-e |
| VCK190 | xcvc1902-vsva2197-2MP-e-S |

---

## Tool detection keywords

| Tool | Keywords in doc |
|---|---|
| Vitis HLS CLI | `vitis-run`, `v++ -c --mode hls` |
| Vitis IDE GUI | `vitis -w`, `Flow view`, `Vitis Components` |
| Vivado | `vivado -mode`, `open_project`, `launch_runs` |
| Mixed | Multiple tool keywords present |

---

## VM defaults

| Setting | Default |
|---|---|
| TRAINING_PATH | `/home/amd/training` |
| Vitis install | `/opt/amd/2025.2/Vitis/settings64.sh` |
| VNC display | `:1` |
| tmux session | `lab` |
| VNC port | `5901` |

---

## Notes

- Never overwrite the original lab file
- Always use absolute paths on VM to avoid relative path issues
- If a step fails, record it but continue to next step — don't abort
- For timing violations in HLS labs — these are expected and noted, not flagged as failures
- cosim errors on `ap_ctrl_none` designs are expected behavior — note as informational
- Figure comparison is semantic not pixel-perfect — look for same UI elements and values
- If VNC disconnects mid-run, auto-restart and continue
