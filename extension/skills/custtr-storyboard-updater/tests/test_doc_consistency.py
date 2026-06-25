"""Documentation consistency checks for skill architecture."""
import re
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent


def _count_numbered_rules(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    return len(re.findall(r"^\d+\. ", text, re.MULTILINE))


def test_skill_and_core_rules_rule_count_match():
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    core_block = skill.split("## Core Rules", 1)[1].split("## Required Story Questions", 1)[0]
    skill_rules = re.findall(r"^(\d+)\. ", core_block, re.MULTILINE)
    skill_nums = [int(n) for n in skill_rules]
    assert skill_nums, "SKILL.md should contain numbered core rules"
    assert skill_nums == list(range(1, max(skill_nums) + 1)), (
        f"SKILL rule numbers not contiguous: {skill_nums}"
    )

    core_count = _count_numbered_rules(SKILL_ROOT / "references" / "core_rules.md")
    assert core_count == max(skill_nums), (
        f"core_rules.md has {core_count} rules but SKILL.md lists {max(skill_nums)}"
    )


def test_workflow_phases_no_embed_concept_decomposition_in_verification_report():
    text = (SKILL_ROOT / "references" / "workflow_phases.md").read_text(encoding="utf-8").lower()
    assert "array inside `verification_report.json`" not in text
    assert "record the decomposition in a `concept_decomposition` array inside" not in text


def test_skill_detect_source_gaps_described_as_advisory():
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    scripts_section = skill.split("## Scripts", 1)[1]
    line = [ln for ln in scripts_section.splitlines() if "detect_source_gaps.py" in ln][0]
    assert "advisory" in line.lower()
    assert "identify uncovered factual claims" not in line.lower()


def test_skill_requires_cursor_plan_mode_gate():
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert "Cursor Plan Mode Gate" in skill
    assert 'SwitchMode(target_mode_id="plan")' in skill
    assert "before any deck-update workflow step" in skill


def test_final_pptx_validation_is_xml_package_only():
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    core_rules = (SKILL_ROOT / "references" / "core_rules.md").read_text(encoding="utf-8")
    new_slide_guide = (SKILL_ROOT / "references" / "new_slide_guide.md").read_text(encoding="utf-8")
    workflow_phases = (SKILL_ROOT / "references" / "workflow_phases.md").read_text(encoding="utf-8")

    for doc in (skill, core_rules):
        assert "Final PPTX validation is XML/package-only" in doc
        assert "PowerPoint, LibreOffice, COM automation, browser UI, or any presentation viewer" in doc

    assert "Final merged-output validation is XML/package-only" in new_slide_guide
    assert "Do not open the final merged deck for rendered QA" in new_slide_guide
    assert "validate_deck.py --require-fresh-merge is the final validation path" in workflow_phases


def test_lint_skill_docs_passes():
    import lint_skill_docs

    violations = lint_skill_docs.scan(SKILL_ROOT)
    assert violations == [], f"Stale phrases found: {violations[:5]}"
