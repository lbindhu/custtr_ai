# board-ssh Skill

SSH connection manager and remote command runner for embedded Linux boards (AMD Ryzen Embedded, development boards, Linux targets).

## What This Skill Does

- Connects to any IP-accessible Linux board via SSH using PuTTY `plink`
- Runs shell commands remotely and returns real output — no guessing
- Automatically saves the last-used host/username for fast reconnection
- Interprets raw command output in plain English (CPU model, kernel version, errors, etc.)

## Prerequisites

- **PuTTY** installed at `C:/Program Files/PuTTY/` (provides `plink`)
- Board must be reachable by IP on the same network
- SSH daemon (`sshd`) must be running on the board

## How to Trigger

Invoke the skill with any of these prompts (Claude will detect the intent automatically):

- **"Connect to my board at 10.140.176.218, user amd, password mypassword"**
- **"SSH to 192.168.1.50 as root with password rootpass and show me the CPU info"**
- **"Check on the board — what kernel version is it running?"**
- **"Run `lspci` on the board"**
- **"Tell me the features of the CPU on the target"**

> Tip: If a board was connected previously, Claude will offer to reuse the saved host/user — you only need to provide the password again.

## Example Prompts

### 1. Initial Connection + CPU Info

```
Connect to my board at 10.140.176.218 using username amd and password amdpass123.
Tell me the CPU model and features.
```

Claude will:
1. SSH to `amd@10.140.176.218`
2. Run `lscpu` and `cat /proc/cpuinfo | head -40`
3. Return the raw output + plain-English summary of CPU model, core count, clock speeds, and ISA features (e.g., AVX2, AES, SHA)

---

### 2. Kernel Version and OS

```
What kernel version and Linux distro is running on the board?
```

Claude will run:
```bash
uname -a
cat /etc/os-release
```

Example output you'll see:
```
Linux amd-board 6.6.30-yocto-standard #1 SMP PREEMPT Fri May 10 10:22:04 UTC 2024 x86_64 GNU/Linux

NAME="poky"
VERSION="4.3 (nanbield)"
```

---

### 3. Memory Info

```
How much RAM does the board have? Is it all usable?
```

Claude will run `free -h` and `cat /proc/meminfo | head -20`.

---

### 4. PCI Devices and GPU

```
List all PCI devices on the board. Is there a GPU detected?
```

Claude will run `lspci` and detail any VGA/GPU entries.

---

### 5. Temperature and Thermal State

```
Is the board running hot? What temperatures do the sensors report?
```

Claude will run:
```bash
cat /sys/class/thermal/thermal_zone*/temp
sensors 2>/dev/null
```

---

### 6. Storage and Disk Layout

```
Show me the disk layout and how much space is used.
```

Claude will run `lsblk` and `df -h`.

---

### 7. Run a Custom Command

```
Run `dmesg | grep -i amd` on the board.
```

Claude will execute the command exactly as given and show the live output.

---

## Helper Scripts

Located in `scripts/`:

| Script | Purpose | Usage |
|--------|---------|-------|
| `board_connect_test.sh` | Tests SSH connectivity, reports clear error if it fails | `bash scripts/board_connect_test.sh HOST USER PASSWORD` |
| `board_cmd.sh` | Runs a single command on the board via SSH | `bash scripts/board_cmd.sh HOST USER PASSWORD 'command'` |

### board_connect_test.sh

Checks:
1. Network reachability (ping)
2. SSH authentication
3. Returns `OK` or a specific error: auth failure, connection refused, timeout

### board_cmd.sh

Runs any shell command on the board. Uses `plink` with the stored credentials. Output is returned directly to Claude's context.

---

## Connection Config

Claude saves connection state in `board_config.json` after a successful connection:

```json
{
  "host": "10.140.176.218",
  "user": "amd",
  "last_connected": "2026-06-26"
}
```

**Passwords are never stored.** You will always be asked for the password when starting a new Claude session.

---

## Features Claude Can Report From the Board

| Feature | What You Learn |
|---------|---------------|
| CPU model and features | Name, family, core/thread count, clock speed, ISA extensions (AVX2, AES, SHA, etc.) |
| Kernel version | Full `uname -a` string — version, build date, architecture |
| OS / distro | Yocto, Ubuntu, Debian, Buildroot — name + version from `/etc/os-release` |
| RAM | Total, used, free, available — from `free -h` |
| PCI devices | All detected peripherals — GPU, NIC, SATA controller, USB host |
| Storage layout | Partition table, mount points, disk usage via `lsblk` and `df -h` |
| Network interfaces | IP addresses, link state, routing table |
| Temperature | Thermal zone temperatures, `sensors` output if `lm-sensors` is installed |
| Running processes | Top CPU consumers via `ps aux` |
| Boot/driver logs | `dmesg` — AMD driver init, hardware detection, errors |
| Failed services | `systemctl list-units --failed` |
| USB devices | `lsusb` — connected peripherals |
| Kernel modules | `lsmod` — loaded drivers |
| AMD GPU / ROCm | `rocm-smi`, `clinfo` if ROCm stack is present |
| Uptime / load | `uptime` — system load averages |

---

## Troubleshooting

| Problem | Likely Cause | Fix |
|---------|-------------|-----|
| Ping fails | Wrong IP or not on same network | Verify IP, check cable/WiFi |
| Authentication failed | Wrong username or password | Re-enter credentials |
| Connection refused | `sshd` not running on board | Start SSH daemon on board |
| Timeout | Firewall blocking port 22 | Check firewall, try `-P PORT` for non-standard SSH port |
| Host key warning | First-time connection | Claude accepts the key automatically on first connect |
| Password has special chars | Shell quoting issue | Use simple alphanumeric password or ask Claude to handle escaping |

---

## Security Notes

- Passwords are **never echoed** in Claude's output
- Intended for trusted lab/development networks — not production/internet-facing boards
- Destructive commands (`rm -rf`, `dd`, `mkfs`) will always prompt for confirmation before running
