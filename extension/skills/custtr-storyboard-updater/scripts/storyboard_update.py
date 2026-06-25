#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from json_helpers import safe_load_json, try_load_json  # noqa: E402

HERE = Path(__file__).resolve().parent
STALE_TERMS_EXAMPLE = HERE.parent / "references" / "stale_terms.example.json"


def run(cmd, check=True):
    print("+ " + " ".join(map(str, cmd)))
    r = subprocess.run([str(c) for c in cmd])
    if check and r.returncode != 0:
        raise SystemExit(r.returncode)
    return r.returncode


def work_dir(deck):
    deck = Path(deck)
    return deck.parent / deck.with_suffix("").name / ".storyboard_update"


_HOOK_MARKER = "compact_hook.py"  # unique substring to detect our installed hook

def _ensure_hook_installed(deck_dir: Path) -> None:
    """Install the PostCompact hook into <deck_dir>/.claude/settings.json if absent.

    Merges safely — existing hooks in the file are preserved.  Idempotent.
    """
    claude_dir = deck_dir / ".claude"
    settings_path = claude_dir / "settings.json"

    # Read existing settings (or start fresh)
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
        except Exception:
            settings = {}
    else:
        settings = {}

    # Check if our hook is already present anywhere in PostCompact
    hooks_block = settings.get("hooks", {})
    existing_post = hooks_block.get("PostCompact", [])
    for entry in existing_post:
        for h in entry.get("hooks", []):
            if _HOOK_MARKER in (h.get("command") or ""):
                return  # already installed

    # Build the hook command — delegates to the hook script so no inline escaping hell
    skill_dir = str(HERE.parent).replace("\\", "/")
    hook_script = skill_dir + "/scripts/compact_hook.py"
    hook_cmd = f"python3 \"{hook_script}\""

    new_entry = {
        "matcher": "",
        "hooks": [{"type": "command", "command": hook_cmd}],
    }

    if "hooks" not in settings:
        settings["hooks"] = {}
    if "PostCompact" not in settings["hooks"]:
        settings["hooks"]["PostCompact"] = []
    settings["hooks"]["PostCompact"].append(new_entry)

    claude_dir.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[storyboard-updater] PostCompact hook installed -> {settings_path}")


def _write_session_state(wd: Path, deck: Path, mode: str) -> None:
    state = {
        "deck": str(deck),
        "work_dir": str(wd),
        "mode": mode,
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "skill_dir": str(HERE.parent),
    }
    (wd / "session_state.json").write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def _artifact_status(path: Path, label: str = "") -> str:
    tag = label or path.name
    return f"[DONE]  {tag}" if path.exists() else f"[MISSING]  {tag}"


def _run_status(deck_hint: str = "") -> None:
    # Resolve work dir: prefer deck argument, fall back to session_state.json search
    wd: Path | None = None
    deck_path: str = deck_hint

    if deck_hint:
        wd = work_dir(deck_hint)
    else:
        # Search cwd tree for session_state.json
        candidates = sorted(Path.cwd().rglob(".storyboard_update/session_state.json"))
        if candidates:
            state = json.loads(candidates[0].read_text(encoding="utf-8"))
            wd = Path(state["work_dir"])
            deck_path = state.get("deck", "")

    if wd is None or not wd.exists():
        print("No active storyboard work directory found.")
        print("Run with --deck to specify the deck being updated.")
        return

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"=== Storyboard Update Status ===")
    print(f"Deck:     {deck_path or '(unknown)'}")
    print(f"Work dir: {wd}")
    print(f"Checked:  {now}")
    print()

    # Phase 1
    extract = wd / "deck_extract.json"
    story_model = wd / "story_model.json"
    story_prompt = wd / "story_model_prompt.md"
    story_scaffold = wd / "story_model_scaffold.json"
    if extract.exists():
        deck_data = try_load_json(extract) or {}
        slide_count = deck_data.get("slide_count", "?")
        story_status = "story_model.json" if story_model.exists() else "story_model_prompt.md + story_model_scaffold.json"
        print(f"Phase 1   [DONE]  deck_extract.json ({slide_count} slides), {story_status}")
    else:
        print(f"Phase 1   [MISSING]  deck_extract.json")

    # Phase 1.5
    notes = wd / "original_notes.json"
    if notes.exists():
        notes_data = try_load_json(notes) or {}
        n_notes = len(notes_data) if isinstance(notes_data, dict) else "?"
        print(f"Phase 1.5 [DONE]  original_notes.json ({n_notes} notes)")
    else:
        print(f"Phase 1.5 [MISSING]  original_notes.json")

    # Phase 2
    src_inv = wd / "source_inventory.json"
    ref_ext = wd / "reference_extract.json"
    if src_inv.exists():
        src_data = try_load_json(src_inv) or {}
        queries = src_data.get("queries") or src_data.get("entries") or []
        ref_chunks = 0
        if ref_ext.exists():
            ref_data = try_load_json(ref_ext) or {}
            entries = ref_data.get("entries") or ref_data.get("sources") or []
            if isinstance(entries, list):
                ref_chunks = len(entries)
        channels = sorted({
            str(q.get("server") or q.get("source_type") or q.get("kind") or "unknown").lower()
            for q in queries
            if isinstance(q, dict)
        })
        channel_note = f", channels: {', '.join(channels[:6])}" if channels else ""
        ref_note = f", {ref_chunks} reference_extract chunk(s)" if ref_chunks else ""
        print(
            f"Phase 2   [DONE]  source_inventory.json "
            f"({len(queries)} entries{ref_note}{channel_note})"
        )
    else:
        print(f"Phase 2   [MISSING]  source_inventory.json")

    # Phase 2.5
    gaps = wd / "coverage_gaps.json"
    parity = wd / "parity_matrix.json"
    if gaps.exists():
        gaps_data = try_load_json(gaps) or {}
        gap_rows = gaps_data.get("slides_with_gaps")
        if gap_rows is None:
            gap_rows = gaps_data.get("gaps") or []
        lint_slides = len(gap_rows)
        recon = wd / "coverage_gap_reconciliation.json"
        recon_tag = ", coverage_gap_reconciliation.json" if recon.exists() else ""
        parity_tag = ", advisory parity_matrix.json" if parity.exists() else ""
        print(
            f"Phase 2.5 [DONE]  coverage_gaps.json "
            f"({lint_slides} slide(s) with advisory lint signals{recon_tag}{parity_tag})"
        )
    else:
        print(f"Phase 2.5 [MISSING]  coverage_gaps.json")

    # Phase 3 — slide rows
    slide_count_total: int = 0
    if extract.exists():
        deck_data = try_load_json(extract) or {}
        slide_count_total = deck_data.get("slide_count", 0)

    rows_dir = wd / "slide_rows"
    sidecars = sorted(rows_dir.glob("s*_verification.json")) if rows_dir.exists() else []
    batches = sorted(rows_dir.glob("batch_*.json")) if rows_dir.exists() else []
    merge_sources = len(sidecars) + len(batches)
    vr = wd / "verification_report.json"
    xval = wd / "cross_validation_report.json"
    cd = wd / "concept_decomposition.json"

    if vr.exists() and xval.exists() and cd.exists():
        print(f"Phase 3   [DONE]  verification_report.json, cross_validation_report.json, concept_decomposition.json")
    else:
        if sidecars:
            audited_nums = []
            total_findings = 0
            for s in sidecars:
                try:
                    d = json.loads(s.read_text(encoding="utf-8"))
                    if isinstance(d, dict):
                        audited_nums.append(int(d.get("slide_number") or 0))
                        total_findings += len(d.get("findings") or [])
                except Exception:
                    pass
            audited_nums = sorted(n for n in audited_nums if n > 0)
            done_count = len(audited_nums)
            last_done = audited_nums[-1] if audited_nums else 0
            next_slide = last_done + 1 if last_done else 1
            print(f"Phase 3   [IN PROGRESS]")
            if slide_count_total:
                print(f"          slide_rows/: {done_count} of {slide_count_total} slides audited (slides {audited_nums[0] if audited_nums else '?'}-{last_done} done)")
                print(f"          slides remaining: {next_slide}-{slide_count_total}")
            else:
                print(f"          slide_rows/: {done_count} slides audited, last: slide {last_done}")
            print(f"          open findings so far: {total_findings}")
            print(f"          concept_decomposition.json: {'DONE' if cd.exists() else 'MISSING (author after audit complete)'}")
            print(f"          verification_report.json: {'DONE' if vr.exists() else 'MISSING (run merge_slide_rows.py when done)'}")
            if merge_sources and not vr.exists():
                print(f"          merge ready: {merge_sources} slide_rows file(s) ({len(batches)} batch, {len(sidecars)} legacy)")
            print(f"          cross_validation_report.json: {'DONE' if xval.exists() else 'MISSING'}")
        else:
            print(f"Phase 3   [NOT STARTED]")

    # Phase 4
    update_plan = wd / "update_plan.json"
    if update_plan.exists():
        print(f"Phase 4   [DONE]  update_plan.json")
    elif vr.exists() and xval.exists() and cd.exists():
        print(f"Phase 4   [READY]  audit_gate.py not yet run; author update_plan.json")
    else:
        print(f"Phase 4   [BLOCKED — Phase 3 not complete]")

    # Phase 5
    validation = wd / "validation.json"
    if validation.exists():
        print(f"Phase 5   [DONE]  validation.json")
    elif update_plan.exists():
        print(f"Phase 5   [READY]  run with --mode execute")
    else:
        print(f"Phase 5   [BLOCKED]")

    # Next step guidance
    print()
    if sidecars and not vr.exists():
        last_done = max(
            (int(json.loads(s.read_text(encoding="utf-8")).get("slide_number") or 0) for s in sidecars),
            default=0,
        )
        next_slide = last_done + 1
        print(f"Next step: Resume Phase 3 audit at slide {next_slide}.")
        print(f"           Write each slide's row to slide_rows/sNN_verification.json before advancing.")
    elif not (wd / "source_inventory.json").exists():
        print("Next step: Complete Phase 2 — gather authoritative sources for deck claim clusters; save source_inventory.json and reference_extract.json.")
    elif not (wd / "deck_extract.json").exists():
        print("Next step: Run Phase 1 — storyboard_update.py --mode audit-plan.")
    elif vr.exists() and xval.exists() and cd.exists() and not update_plan.exists():
        print("Next step: Run audit_gate.py, then author update_plan.json.")
    elif update_plan.exists() and not validation.exists():
        print("Next step: Run with --mode execute --approved-plan <plan>.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deck", required=False, default="")
    ap.add_argument("--target-version", default="")
    ap.add_argument("--sources", nargs="*", default=[])
    ap.add_argument("--focus", default="")
    ap.add_argument("--source-deltas")
    ap.add_argument("--mode", choices=["audit-plan", "execute", "audit-only", "status"], required=True)
    ap.add_argument("--approved-plan")
    ap.add_argument("--output")
    ap.add_argument("--require-sources", action="store_true",
                    help="Pass through to audit_gate.py — requires documented source coverage entries.")
    ap.add_argument("--install-resume-hook", action="store_true",
                    help="Opt in to installing the PostCompact resume hook in the deck directory.")
    ap.add_argument("--lenient-whitespace", action="store_true",
                    help="Pass through to apply_existing_updates.py.")
    args = ap.parse_args()

    # --mode status may work without --deck if session_state.json can be found
    if args.mode == "status":
        _run_status(args.deck)
        return

    if not args.deck:
        raise SystemExit("--deck is required for modes other than status")

    deck = Path(args.deck)
    if args.install_resume_hook:
        _ensure_hook_installed(deck.parent)
    wd = work_dir(deck)
    wd.mkdir(parents=True, exist_ok=True)
    extract = wd / "deck_extract.json"
    story_model = wd / "story_model.json"
    story_prompt = wd / "story_model_prompt.md"
    story_scaffold = wd / "story_model_scaffold.json"
    plan = Path(args.approved_plan) if args.approved_plan else wd / "update_plan.json"
    stale_terms_path = wd / "stale_terms.json"

    # Write session marker so the PostCompact hook can surface recovery instructions
    _write_session_state(wd, deck, args.mode)

    if args.mode in {"audit-plan", "audit-only"}:
        run([sys.executable, HERE / "extract_deck.py", deck, "--output", extract])
        run([
            sys.executable, HERE / "build_story_model.py",
            "--deck-extract", extract,
            "--prompt-output", story_prompt,
            "--scaffold-output", story_scaffold,
            "--target-version", args.target_version,
        ])
        if not story_model.exists():
            print(
                f"LLM-authored story_model.json is required before scans or planning.\n"
                f"Prompt written to: {story_prompt}\n"
                f"Scaffold written to: {story_scaffold}\n"
                f"Author {story_model}, then run validate_story_model.py and resume."
            )
            raise SystemExit(2)
        run([
            sys.executable, HERE / "validate_story_model.py",
            "--deck-extract", extract,
            "--story-model", story_model,
        ])
        # Skill v2: stale_terms.json must be authored by the LLM before scans run.
        if not stale_terms_path.exists():
            template = safe_load_json(STALE_TERMS_EXAMPLE, "stale_terms_example.json")
            template["target_release"] = args.target_version or template.get("target_release", "")
            template["deck"] = str(deck)
            template["stale_terms"] = []
            template["intentionally_kept"] = []
            template["_authoring_note"] = (
                "This file MUST be authored from sources before the scans run. "
                "See references/stale_terms_schema.md. Remove this key when complete."
            )
            stale_terms_path.write_text(
                json.dumps(template, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            raise SystemExit(
                f"stale_terms.json scaffold written to {stale_terms_path}. "
                f"Author per-deck stale tokens (see references/stale_terms_schema.md) "
                f"and re-run."
            )
        # Mechanical scans — these populate the inputs audit_gate.py requires.
        run([sys.executable, HERE / "stale_term_scan.py",
             "--deck-extract", extract,
             "--stale-terms", stale_terms_path,
             "--output-json", wd / "stale_term_scan.json",
             "--output-md", wd / "stale_term_scan.md"])
        run([sys.executable, HERE / "scope_consistency_scan.py",
             "--deck-extract", extract,
             "--stale-terms", stale_terms_path,
             "--output", wd / "scope_consistency.json"])
        run([sys.executable, HERE / "consistency_scan.py",
             "--deck-extract", extract,
             "--output", wd / "consistency_scan.json"])
        run([sys.executable, HERE / "build_parity_matrix.py",
             "--deck-extract", extract,
             "--stale-terms", stale_terms_path,
             "--output", wd / "parity_matrix.json"], check=False)
        if args.mode == "audit-only":
            print(f"Audit complete. See:\n  {wd / 'stale_term_scan.md'}\n  {wd / 'scope_consistency.json'}\n  {wd / 'consistency_scan.json'}")
            return
        print(f"Field-name reference (read before authoring ANY JSON): {HERE.parent / 'references' / 'artifact_schemas.md'}")
        print(f"Story model: {story_model}")
        print(f"Mechanical scans: {wd / 'stale_term_scan.md'}, {wd / 'scope_consistency.json'}, {wd / 'consistency_scan.json'}")
        print(f"Advisory parity lint: {wd / 'parity_matrix.json'}")
        print(f"Concept decomposition (author before audit_gate): {wd / 'concept_decomposition.json'}")
        print("Before authoring update_plan.json, complete Phase 3 artifacts, run audit_gate.py "
              "--stage pre-plan, and present the mandatory user checkpoint.")
        return

    if not args.approved_plan:
        raise SystemExit("--approved-plan is required in execute mode")

    updated_base = wd / "updated_base.pptx"
    additions = wd / "additions.pptx"
    final = Path(args.output) if args.output else deck.with_name(f"{deck.stem}_V1.pptx")
    validation = wd / "validation.json"

    run([sys.executable, HERE / "extract_deck.py", deck, "--output", extract])
    if not story_model.exists():
        run([
            sys.executable, HERE / "build_story_model.py",
            "--deck-extract", extract,
            "--prompt-output", story_prompt,
            "--scaffold-output", story_scaffold,
            "--target-version", args.target_version,
        ])
        print(
            f"LLM-authored story_model.json is required for execute mode.\n"
            f"Prompt written to: {story_prompt}\n"
            f"Scaffold written to: {story_scaffold}\n"
            f"Author and validate {story_model}, then re-run execute mode."
        )
        raise SystemExit(2)
    run([
        sys.executable, HERE / "validate_story_model.py",
        "--deck-extract", extract,
        "--story-model", story_model,
    ])
    data = safe_load_json(extract, "deck_extract.json")
    plan_data = safe_load_json(plan, "update_plan.json")
    plan_data["base_slide_count"] = data["slide_count"]
    plan.write_text(json.dumps(plan_data, indent=2, ensure_ascii=False), encoding="utf-8")

    run([sys.executable, str(HERE / "validate_plan.py"),
         "--plan", str(plan),
         "--story-model", str(story_model)])

    # Refresh mechanical scans against the current deck snapshot before gating.
    if not stale_terms_path.exists():
        raise SystemExit(
            f"stale_terms.json missing at {stale_terms_path}. "
            f"Re-run in --mode audit-plan to scaffold and author it."
        )
    run([sys.executable, HERE / "stale_term_scan.py",
         "--deck-extract", extract,
         "--stale-terms", stale_terms_path,
         "--output-json", wd / "stale_term_scan.json",
         "--output-md", wd / "stale_term_scan.md"])
    run([sys.executable, HERE / "scope_consistency_scan.py",
         "--deck-extract", extract,
         "--stale-terms", stale_terms_path,
         "--output", wd / "scope_consistency.json"])
    run([sys.executable, HERE / "consistency_scan.py",
         "--deck-extract", extract,
         "--output", wd / "consistency_scan.json"])
    # Assemble verification_report.json from per-slide sidecars (if present)
    run([sys.executable, HERE / "merge_slide_rows.py", "--work-dir", wd], check=False)
    gate_cmd = [sys.executable, HERE / "audit_gate.py", "--work-dir", wd]
    if args.require_sources:
        gate_cmd.append("--require-sources")
    rc = run(gate_cmd, check=False)
    if rc != 0:
        raise SystemExit(
            "audit_gate.py refused to advance. Fix the listed findings or "
            "add explicit clears to cross_validation_report.json, then re-run."
        )

    unresolved = [
        a for a in plan_data.get("actions", [])
        if a.get("requires_human_authored_text")
    ]
    if unresolved:
        details = ", ".join(f"{a.get('type')}@{a.get('slide_number') or a.get('insert_after_slide')}" for a in unresolved[:8])
        raise SystemExit(
            "Approved plan still has actions requiring human-authored text. "
            f"Resolve these before execute mode: {details}"
        )

    apply_cmd = [sys.executable, HERE / "apply_existing_updates.py", "--deck", deck, "--plan", plan, "--output", updated_base]
    if args.lenient_whitespace:
        apply_cmd.append("--lenient-whitespace")
    run(apply_cmd)

    # Post-apply differential check: did promised removals actually take effect?
    run([sys.executable, HERE / "post_apply_check.py",
         "--original", deck,
         "--updated", updated_base,
         "--stale-terms", stale_terms_path,
         "--plan", plan,
         "--output", wd / "post_apply_check.json"])

    add_actions = [a for a in plan_data.get("actions", []) if a.get("type") == "add_new_slide"]
    additions_arg = ""
    if add_actions:
        if not additions.exists():
            raise SystemExit(
                f"Plan contains {len(add_actions)} add_new_slide action(s), but {additions} "
                "does not exist. Create the additions deck under LLM control, verify it through "
                "XML/package inspection, then re-run execute mode."
            )
        additions_arg = additions

    cmd = [sys.executable, HERE / "merge_storyboard.py", "--base", updated_base, "--plan", plan, "--output", final]
    if additions_arg:
        cmd.extend(["--additions", additions_arg])
    run(cmd)
    run([
        sys.executable, HERE / "validate_deck.py", final,
        "--plan", plan,
        "--output", validation,
        "--work-dir", str(wd),
        "--require-fresh-merge",
    ])
    print(f"Updated deck: {final}")
    print(f"Validation: {validation}")


if __name__ == "__main__":
    main()
