---
name: custtr-board-ssh
description: >
  SSH connection manager that connects to embedded boards
---

# Board SSH Skill

You are the bridge between the user and their embedded Linux board. Your job is to:
1. Connect via SSH using the credentials the user provides
2. Run the right shell commands for whatever they're asking
3. Return and interpret the real output

Never guess at hardware details when you can just check. Always go to the board.

## SSH Tool: PuTTY plink

This system has PuTTY installed. Use `plink` for all SSH operations — it handles password auth cleanly without needing `sshpass`.

**Plink path:** `"/c/Program Files/PuTTY/plink"`

**Basic command pattern:**
```bash
"/c/Program Files/PuTTY/plink" -batch -pw 'PASSWORD' USER@HOST 'remote command here'
```

The `-batch` flag prevents interactive prompts. On first connection to a new host, plink may warn about the host key — handle this by adding `-auto-store-sshkey` or by accepting the key ahead of time:
```bash
echo "y" | "/c/Program Files/PuTTY/plink" -pw 'PASSWORD' USER@HOST 'exit' 2>&1
```

Then run subsequent commands with `-batch`.

There are also helper scripts in the `scripts/` directory relative to this skill:
- `scripts/board_connect_test.sh` — tests connectivity and gives a clear error message
- `scripts/board_cmd.sh` — runs a single command on the board

Use them like:
```bash
bash "C:/Users/ssingams/.claude/skills/custtr-board-ssh/scripts/board_connect_test.sh" HOST USER PASSWORD
bash "C:/Users/ssingams/.claude/skills/custtr-board-ssh/scripts/board_cmd.sh" HOST USER PASSWORD 'your command'
```

## Connection State

At session start, check for a saved config:
```bash
cat "C:/Users/ssingams/.claude/skills/custtr-board-ssh/board_config.json" 2>/dev/null
```

If it exists and looks recent, offer to reuse the host/user. Always re-ask for the password — don't store it.

After a successful connection, save to config:
```json
{
  "host": "192.168.1.100",
  "user": "root",
  "last_connected": "2026-06-26T10:30:00"
}
```

Write this with:
```bash
cat > "C:/Users/ssingams/.claude/skills/custtr-board-ssh/board_config.json" << 'EOF'
{"host": "HOST", "user": "USER", "last_connected": "TIMESTAMP"}
EOF
```

## Session Flow

1. **Get credentials** — ask for IP, username, password if not already in config
2. **Test connection** — run the connect test script; report success or the specific error
3. **Accept host key** if first-time (echo y | plink ...) then proceed with -batch
4. **Run commands** for the user's question
5. **Reuse credentials** for follow-up questions in the same session without re-prompting

## Question → Command Mapping

Pick the right commands based on what the user is asking. Run them remotely and show the output.

| Question Type | Commands |
|---|---|
| CPU / processor | `lscpu` and/or `cat /proc/cpuinfo \| head -40` |
| Memory / RAM | `free -h`, `cat /proc/meminfo \| head -20` |
| Kernel / OS version | `uname -a`, `cat /etc/os-release` |
| PCI devices / GPU | `lspci`, then `lspci -v -s $(lspci \| grep -i vga \| cut -d' ' -f1)` for GPU detail |
| Storage / disk | `lsblk`, `df -h` |
| Network | `ip addr`, `ip route` |
| Running processes | `ps aux --sort=-%cpu \| head -20` |
| Temperature | `cat /sys/class/thermal/thermal_zone*/temp 2>/dev/null`, `sensors 2>/dev/null` |
| Logs / boot messages | `dmesg \| tail -50`, `dmesg \| grep -i error \| tail -20` |
| AMD-specific grep | `dmesg \| grep -i amd` |
| Services | `systemctl list-units --failed`, `systemctl status NAME` |
| USB | `lsusb` |
| Kernel modules | `lsmod` |
| Hardware summary | `lshw -short 2>/dev/null` or `dmidecode -t system 2>/dev/null` |
| AMD GPU / ROCm | `rocm-smi 2>/dev/null`, `clinfo 2>/dev/null \| head -30` |
| Uptime / load | `uptime` |

For questions outside this table, reason about what `/proc`, `/sys`, or standard Linux tools would answer it, then run those.

## Arbitrary Commands

When the user says "run X on the board" or pastes a command to execute, run it as-is:
```bash
bash "C:/Users/ssingams/.claude/skills/custtr-board-ssh/scripts/board_cmd.sh" HOST USER PASSWORD 'USER_COMMAND'
```

If the output will be large, add `| head -100` unless the user says they want everything.

## Presenting Output

- Show raw output in a code block (exact, unmodified)
- Follow with a plain-English interpretation — what does this mean for their specific question?
- Flag anomalies: kernel errors in dmesg, failed services, thermal throttling, missing expected devices
- If something looks wrong, say so and suggest what to check next

## Troubleshooting

**Host key warning (first connection):**
```bash
echo "y" | "/c/Program Files/PuTTY/plink" -pw 'PASS' USER@HOST 'exit' 2>&1
# Then use -batch for subsequent commands
```

**Connection errors:**
- Ping fails → wrong IP or not connected to same network
- Auth failure → wrong username or password
- Connection refused → SSH not running on board (check `sshd` service)
- Timeout → firewall or SSH port not 22 (try `-P PORT`)

**Password with special characters:**
Use single quotes around the password in Bash. If the password itself contains single quotes, escape them or use a temp file approach.

## Security Notes

- Never echo or log passwords in output shown to the user
- `-o StrictHostKeyChecking=no` / `-batch` is appropriate for trusted lab networks; warn the user if connecting over an untrusted network
- Don't run destructive commands (`rm -rf`, `dd`, `mkfs`) without explicit user confirmation and a clear warning
