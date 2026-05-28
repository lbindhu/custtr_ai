#!/usr/bin/env python3
"""PostCompact hook for custtr-storyboard-updater.

Installed automatically into <deck_dir>/.claude/settings.json by
storyboard_update.py on first run. Searches the working directory tree
for an active session_state.json and prints targeted recovery
instructions. Silent if no workflow is in progress.
"""
import glob
import json
import sys
from pathlib import Path


def main():
    files = glob.glob("**/.storyboard_update/session_state.json", recursive=True)
    if not files:
        sys.exit(0)

    try:
        st = json.loads(Path(files[0]).read_text(encoding="utf-8"))
    except Exception:
        sys.exit(0)

    skill_dir = st.get("skill_dir", "")
    deck = st.get("deck", "")
    work_dir = st.get("work_dir", "")

    print()
    print("COMPACTION NOTICE: Storyboard workflow in progress.")
    print(f"  Deck:     {deck}")
    print(f"  Work dir: {work_dir}")
    print("  Run this to see where you left off:")
    print(f'    python3 "{skill_dir}/scripts/storyboard_update.py" --deck "{deck}" --mode status')
    print("  Re-read references/workflow_phases.md before resuming Phase 3.")
    print()


if __name__ == "__main__":
    main()
