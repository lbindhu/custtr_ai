"""Tests for audit_gate.notes_structure_issues()."""

from audit_gate import notes_structure_issues


class TestNotesStructureIssues:
    def test_clean_plan(self):
        plan = {"actions": [
            {"type": "add_new_slide", "slide_number": 5, "speaker_notes": "ok"},
        ]}
        assert notes_structure_issues(plan) == []

    def test_speaker_notes_on_existing_slide(self):
        plan = {"actions": [
            {"type": "update_existing", "slide_number": 3, "speaker_notes": "bad"},
        ]}
        issues = notes_structure_issues(plan)
        assert len(issues) == 1
        assert "speaker_notes" in issues[0]
        assert "slide 3" in issues[0]

    def test_notes_update_with_speaker_notes(self):
        plan = {"actions": [
            {"type": "notes_update", "slide_number": 7, "speaker_notes": "bad"},
        ]}
        issues = notes_structure_issues(plan)
        assert len(issues) == 1

    def test_empty_notes_change_fragment(self):
        plan = {"actions": [
            {
                "type": "notes_update",
                "slide_number": 4,
                "notes_changes": [
                    {"match_fragment": "", "replacement_fragment": "new text"},
                ],
            },
        ]}
        issues = notes_structure_issues(plan)
        assert len(issues) == 1
        assert "match_fragment" in issues[0]

    def test_valid_notes_changes(self):
        plan = {"actions": [
            {
                "type": "notes_update",
                "slide_number": 4,
                "notes_changes": [
                    {"match_fragment": "old text", "replacement_fragment": "new text"},
                ],
            },
        ]}
        assert notes_structure_issues(plan) == []
