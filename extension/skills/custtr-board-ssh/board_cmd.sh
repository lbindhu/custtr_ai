#!/usr/bin/env bash
# Run a command on the board via SSH (uses Windows OpenSSH with password via plink or ssh)
# Usage: board_cmd.sh HOST USER PASSWORD 'command to run'

HOST="$1"
USER="$2"
PASS="$3"
CMD="$4"

# Use plink with the known fingerprint to bypass cached key mismatch
FINGERPRINT=$("/c/Program Files/PuTTY/plink" -pw "$PASS" -batch "${USER}@${HOST}" 'echo ok' 2>&1 | true)

# Use plink with -hostkey to accept any key (lab network, trusted)
"/c/Program Files/PuTTY/plink" -pw "$PASS" -no-antispoof "${USER}@${HOST}" "$CMD" 2>&1
