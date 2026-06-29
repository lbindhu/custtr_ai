#!/usr/bin/env bash
# Test SSH connectivity to the board. Prints OK or a descriptive error.
# Usage: board_connect_test.sh HOST USER PASSWORD

HOST="$1"
USER="$2"
PASS="$3"

PLINK="/c/Program Files/PuTTY/plink"

if [ -z "$HOST" ] || [ -z "$USER" ] || [ -z "$PASS" ]; then
    echo "Usage: board_connect_test.sh HOST USER PASSWORD" >&2
    exit 1
fi

# Quick network reachability check first
if ! ping -n 1 -w 2000 "$HOST" > /dev/null 2>&1; then
    echo "FAIL: Host $HOST is not reachable on the network (ping failed). Check IP and cable/WiFi."
    exit 1
fi

# Try SSH echo test
RESULT=$("$PLINK" -batch -pw "$PASS" "${USER}@${HOST}" "echo CONNECTION_OK" 2>&1)

if echo "$RESULT" | grep -q "CONNECTION_OK"; then
    echo "OK: Connected to ${USER}@${HOST}"
    exit 0
elif echo "$RESULT" | grep -qi "access denied\|authentication failed\|wrong password"; then
    echo "FAIL: Authentication error — wrong username or password."
    exit 2
elif echo "$RESULT" | grep -qi "connection refused"; then
    echo "FAIL: Connection refused — SSH daemon may not be running on the board."
    exit 3
elif echo "$RESULT" | grep -qi "timed out\|timeout"; then
    echo "FAIL: Connection timed out — check firewall or that SSH is enabled."
    exit 4
else
    echo "FAIL: $RESULT"
    exit 5
fi
