#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from constants import MARP_ELIGIBLE_LAYOUTS  # noqa: E402
from json_helpers import safe_load_json  # noqa: E402


MERGE_STATUS_FILENAME = ".merge_status.json"


def merger_path():
    here = Path(__file__).resolve()
    skill_root = here.parents[1]
    skills_root = skill_root.parent
    candidates = [
        skills_root / "psas-pptx-merger" / "scripts" / "pptx_merger.py",
        Path.home() / ".claude" / "skills" / "psas-pptx-merger" / "scripts" / "pptx_merger.py",
    ]
    env_path = os.environ.get("PSAS_PPTX_MERGER")
    if env_path:
        candidates.insert(0, Path(env_path))
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise SystemExit("Could not locate psas-pptx-merger/scripts/pptx_merger.py. Set PSAS_PPTX_MERGER.")


def ranges(nums):
    nums = sorted(set(nums))
    if not nums:
        return []
    out = []
    start = prev = nums[0]
    for n in nums[1:]:
        if n == prev + 1:
            prev = n
        else:
            out.append(f"{start}-{prev}" if start != prev else str(start))
            start = prev = n
    out.append(f"{start}-{prev}" if start != prev else str(start))
    return out


def check_output_writable(output_path: Path) -> None:
    """Verify the output path is writable BEFORE invoking the merger.

    On Windows, an open PowerPoint instance holds an exclusive lock on the
    file, which causes os.replace() inside pptx_merger.py to raise
    PermissionError WinError 5 only AFTER the entire merge has happened
    (wasting the work). Catch it up front and emit a clear instruction.

    Never silently fall back to a different filename — the user must close
    the deck so the expected output name is produced.
    """
    if not output_path.exists():
        # Parent must exist and be writable
        parent = output_path.parent
        if not parent.exists():
            return  # merger will create it / fail loudly later
        try:
            test = parent / f".merge_writability_test_{os.getpid()}"
            test.write_bytes(b"x")
            test.unlink()
        except OSError as e:
            raise SystemExit(
                f"ERROR: cannot write to output directory {parent}: {e}"
            )
        return

    # File exists — try to open for append (won't truncate, will fail if locked)
    try:
        with open(output_path, "ab"):
            pass
    except PermissionError:
        raise SystemExit(
            f"ERROR: output file is locked: {output_path}\n"
            f"       This typically means the deck is open in PowerPoint.\n"
            f"       Close the deck and re-run. Do NOT fall back to a different name."
        )
    except OSError as e:
        raise SystemExit(f"ERROR: cannot open output for writing: {output_path}: {e}")


def write_merge_status(output_path: Path, exit_code: int) -> None:
    """Write a small sidecar so downstream tools can detect stale artifacts.

    The sidecar is stored as `<output>.merge_status.json` and contains the
    exit code, the timestamp at which the merge finished, and the output file's
    mtime captured immediately after. validate_deck.py / post_apply_check.py
    can compare these to refuse running against a stale prior artifact.
    """
    sidecar = output_path.with_suffix(output_path.suffix + ".merge_status.json")
    try:
        mtime = output_path.stat().st_mtime if output_path.exists() else None
    except OSError:
        mtime = None
    payload = {
        "output_path": str(output_path),
        "exit_code": exit_code,
        "completed_at": time.time(),
        "output_mtime_at_save": mtime,
    }
    try:
        sidecar.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError as e:
        print(f"WARNING: could not write merge status sidecar {sidecar}: {e}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--additions", help="Script-generated additions PPTX (diagram layouts)")
    ap.add_argument("--marp-additions", help="MARP-generated additions PPTX (table/cards/column/takeaway layouts)")
    ap.add_argument("--plan", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    plan = safe_load_json(args.plan, "update_plan.json")
    slide_count = plan.get("base_slide_count")
    if not slide_count:
        raise SystemExit("update_plan.json must contain base_slide_count")

    remove = {a["slide_number"] for a in plan.get("actions", []) if a.get("type") == "remove_or_deprecate" and a.get("slide_number")}
    remove.discard(slide_count)  # always preserve the trailing AMD logo slide
    add_actions = [a for a in plan.get("actions", []) if a.get("type") == "add_new_slide"]

    for a in add_actions:
        ias = a.get("insert_after_slide")
        if ias is not None and (ias < 0 or ias > slide_count):
            raise SystemExit(
                f"ERROR: add_new_slide '{a.get('title', '<untitled>')}' has "
                f"insert_after_slide={ias} but deck has {slide_count} slides "
                f"(valid range: 0-{slide_count})"
            )

    script_actions = [a for a in add_actions if a.get("slide_layout") not in MARP_ELIGIBLE_LAYOUTS]
    marp_actions = [a for a in add_actions if a.get("slide_layout") in MARP_ELIGIBLE_LAYOUTS]

    # Build insertion groups: list of (insert_after_slide, source_file, slide_index_in_source)
    insertions = []
    if args.additions and script_actions:
        for idx, action in enumerate(script_actions, 1):
            insertions.append((action.get("insert_after_slide", slide_count), args.additions, idx))
    if args.marp_additions and marp_actions:
        for idx, action in enumerate(marp_actions, 1):
            # MARP additions PPTX has title+closing wrapper slides;
            # content slides start at index 2 (1-based)
            insertions.append((action.get("insert_after_slide", slide_count), args.marp_additions, idx + 1))

    groups = {}
    for after, src, idx in insertions:
        groups.setdefault(after, []).append((src, idx))

    sources = []
    cursor = 1
    for after in sorted(groups):
        keep = [n for n in range(cursor, min(after, slide_count) + 1) if n not in remove]
        for r in ranges(keep):
            sources.append(f"{args.base}:{r}")
        for src, idx in groups[after]:
            sources.append(f"{src}:{idx}")
        cursor = after + 1
    keep = [n for n in range(cursor, slide_count + 1) if n not in remove]
    for r in ranges(keep):
        sources.append(f"{args.base}:{r}")

    cmd = [sys.executable, str(merger_path())]
    if args.dry_run:
        cmd.append("--dry-run")
    cmd.extend([args.output, *sources])
    print(" ".join(cmd))

    # Pre-write file-lock check (Windows: catches "open in PowerPoint")
    output_path = Path(args.output)
    if not args.dry_run:
        check_output_writable(output_path)

    result = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print(result.stderr, file=sys.stderr, end="")
    print(result.stdout, end="")

    # Drop a fresh status sidecar so downstream gates can detect stale artifacts.
    if not args.dry_run:
        write_merge_status(output_path, result.returncode)
        if result.returncode != 0:
            print(
                "ERROR: merge_storyboard.py exited non-zero. Do NOT proceed to "
                "validate_deck.py / post_apply_check.py against the prior on-disk "
                f"file; the sidecar at {output_path}.merge_status.json records the failure.",
                file=sys.stderr,
            )

    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
