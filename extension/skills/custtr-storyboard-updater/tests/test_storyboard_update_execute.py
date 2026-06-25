"""Integration-style tests for storyboard_update.py execute routing."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import storyboard_update  # noqa: E402


def test_audit_plan_scaffolds_story_model_and_stops_before_plan(monkeypatch, tmp_path):
    deck = tmp_path / "deck.pptx"
    deck.write_bytes(b"")
    work = tmp_path / "deck" / ".storyboard_update"

    commands = []
    hook_calls = []

    def fake_run(cmd, check=True):
        commands.append([str(c) for c in cmd])
        script = Path(str(cmd[1])).name if len(cmd) > 1 else ""
        if script == "extract_deck.py":
            output = Path(cmd[cmd.index("--output") + 1])
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(
                json.dumps(
                    {
                        "deck": str(deck),
                        "slide_count": 1,
                        "slides": [
                            {
                                "slide_number": 1,
                                "title": "Objectives",
                                "texts": [{"shape_id": "1", "text": "Objectives"}],
                                "notes": "",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
        elif script == "build_story_model.py":
            prompt = Path(cmd[cmd.index("--prompt-output") + 1])
            scaffold = Path(cmd[cmd.index("--scaffold-output") + 1])
            prompt.write_text("# Prompt", encoding="utf-8")
            scaffold.write_text(json.dumps({"schema_version": "2.0"}), encoding="utf-8")
        return 0

    monkeypatch.setattr(storyboard_update, "run", fake_run)
    monkeypatch.setattr(storyboard_update, "_ensure_hook_installed", lambda deck_dir: hook_calls.append(deck_dir))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "storyboard_update.py",
            "--deck",
            str(deck),
            "--target-version",
            "2026.1",
            "--mode",
            "audit-plan",
        ],
    )

    try:
        storyboard_update.main()
    except SystemExit as exc:
        assert exc.code == 2

    command_text = "\n".join(" ".join(cmd) for cmd in commands)
    assert "extract_deck.py" in command_text
    assert "build_update_plan.py" not in command_text
    assert (work / "story_model_prompt.md").exists()
    assert (work / "story_model_scaffold.json").exists()
    assert not (work / "update_plan.json").exists()
    assert hook_calls == []


def test_audit_plan_installs_resume_hook_only_when_requested(monkeypatch, tmp_path):
    deck = tmp_path / "deck.pptx"
    deck.write_bytes(b"")
    hook_calls = []

    def fake_run(cmd, check=True):
        script = Path(str(cmd[1])).name if len(cmd) > 1 else ""
        if script == "extract_deck.py":
            output = Path(cmd[cmd.index("--output") + 1])
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(
                json.dumps({"deck": str(deck), "slide_count": 1, "slides": [{"slide_number": 1, "texts": []}]}),
                encoding="utf-8",
            )
        elif script == "build_story_model.py":
            Path(cmd[cmd.index("--prompt-output") + 1]).write_text("# Prompt", encoding="utf-8")
            Path(cmd[cmd.index("--scaffold-output") + 1]).write_text(json.dumps({"schema_version": "2.0"}), encoding="utf-8")
        return 0

    monkeypatch.setattr(storyboard_update, "run", fake_run)
    monkeypatch.setattr(storyboard_update, "_ensure_hook_installed", lambda deck_dir: hook_calls.append(deck_dir))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "storyboard_update.py",
            "--deck",
            str(deck),
            "--target-version",
            "2026.1",
            "--mode",
            "audit-plan",
            "--install-resume-hook",
        ],
    )

    try:
        storyboard_update.main()
    except SystemExit as exc:
        assert exc.code == 2

    assert hook_calls == [deck.parent]


def test_execute_uses_generic_llm_additions_deck(monkeypatch, tmp_path):
    deck = tmp_path / "deck.pptx"
    deck.write_bytes(b"")
    work = tmp_path / "deck" / ".storyboard_update"
    work.mkdir(parents=True)
    plan_path = work / "update_plan.json"
    plan_path.write_text(
        json.dumps(
            {
                "schema_version": "2.0",
                "deck": str(deck),
                "target_version": "2026.1",
                "status": "approved",
                "actions": [
                    {
                        "action_id": "A-01",
                        "type": "add_new_slide",
                        "insert_after_slide": 1,
                        "reason": "architecture gap",
                        "source_basis": ["SRC-01"],
                        "finding_ids": ["NS-01"],
                        "title": "Architecture Addition",
                        "learning_goal": "Understand the architecture.",
                        "why_this_slide_exists": "Parity gap.",
                        "what_customer_should_understand": "The architecture path.",
                        "visible_content_summary": "A visual architecture slide matching the surrounding deck.",
                        "visual_approach": "LLM duplicates a nearby architecture slide and performs XML/package QA.",
                        "speaker_notes": " ".join(["architecture"] * 90),
                        "qa_expectations": ["No cutoffs", "Deck visual flow matches"],
                    },
                    {
                        "action_id": "A-02",
                        "type": "add_new_slide",
                        "insert_after_slide": 1,
                        "reason": "summary gap",
                        "source_basis": ["SRC-02"],
                        "finding_ids": ["NS-02"],
                        "title": "Capability Addition",
                        "learning_goal": "Understand the capability.",
                        "why_this_slide_exists": "Coverage gap.",
                        "what_customer_should_understand": "The feature set.",
                        "visible_content_summary": "A capability slide with a visual comparison and source note.",
                        "visual_approach": "LLM chooses the best matching existing deck pattern.",
                        "speaker_notes": " ".join(["capability"] * 90),
                        "qa_expectations": ["No overlaps", "Source note is visible"],
                    },
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (work / "stale_terms.json").write_text(
        json.dumps({"stale_terms": [], "intentionally_kept": []}),
        encoding="utf-8",
    )
    (work / "story_model.json").write_text(
        json.dumps({"schema_version": "2.0", "primary_message": "m", "key_talking_points": ["k"]}),
        encoding="utf-8",
    )
    (work / "additions.pptx").write_bytes(b"LLM-created additions deck placeholder")

    commands = []

    def fake_run(cmd, check=True):
        commands.append([str(c) for c in cmd])
        script = Path(str(cmd[1])).name if len(cmd) > 1 else ""
        if script == "extract_deck.py":
            output = Path(cmd[cmd.index("--output") + 1])
            output.write_text(json.dumps({"slide_count": 1, "slides": [{"slide_number": 1, "texts": []}]}), encoding="utf-8")
        return 0

    monkeypatch.setattr(storyboard_update, "run", fake_run)
    monkeypatch.setattr(storyboard_update, "_ensure_hook_installed", lambda _deck_dir: None)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "storyboard_update.py",
            "--deck",
            str(deck),
            "--target-version",
            "2026.1",
            "--mode",
            "execute",
            "--approved-plan",
            str(plan_path),
        ],
    )

    storyboard_update.main()

    command_text = "\n".join(" ".join(cmd) for cmd in commands)
    merge_cmd = next(cmd for cmd in commands if any("merge_storyboard.py" in part for part in cmd))
    assert "--additions" in merge_cmd
    assert str(work / "additions.pptx") in command_text
    assert str(work / "updated_base.pptx") in command_text
    assert str(work / "validation.json") in command_text
