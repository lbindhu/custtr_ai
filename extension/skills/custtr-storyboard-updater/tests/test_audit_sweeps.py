"""Tests for audit_gate.py sweep functions and helpers."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from audit_gate import (
    has_banned_opener,
    notes_structure_issues,
    source_inventory_entries,
    action_ids,
    action_source_tokens,
    slide_title,
    is_boilerplate,
)


class TestHasBannedOpener:
    def test_on_this_slide(self):
        assert has_banned_opener("On this slide, we cover...") is not None

    def test_here_we_see(self):
        assert has_banned_opener("Here we see the architecture...") is not None

    def test_to_recap(self):
        assert has_banned_opener("To recap, the key points are...") is not None

    def test_clean_opener(self):
        assert has_banned_opener("CPM6 supports PCIe Gen 6 at 64 GT/s.") is None

    def test_empty_string(self):
        assert has_banned_opener("") is None

    def test_case_insensitive(self):
        assert has_banned_opener("on this slide we discuss...") is not None

    def test_in_this_section(self):
        assert has_banned_opener("In this section we explore...") is not None


class TestNotesStructureIssues:
    def test_clean_plan(self):
        plan = {"actions": [
            {"type": "notes_update", "slide_number": 7,
             "notes_changes": [{"match_fragment": "old", "replacement_fragment": "new"}]}
        ]}
        assert notes_structure_issues(plan) == []

    def test_wholesale_speaker_notes_rejected(self):
        plan = {"actions": [
            {"type": "notes_update", "slide_number": 7,
             "speaker_notes": "New full notes text"}
        ]}
        issues = notes_structure_issues(plan)
        assert len(issues) == 1
        assert "speaker_notes" in issues[0]

    def test_update_existing_with_speaker_notes_rejected(self):
        plan = {"actions": [
            {"type": "update_existing", "slide_number": 5,
             "speaker_notes": "Some notes"}
        ]}
        issues = notes_structure_issues(plan)
        assert len(issues) == 1

    def test_empty_match_fragment(self):
        plan = {"actions": [
            {"type": "notes_update", "slide_number": 7,
             "notes_changes": [{"match_fragment": "", "replacement_fragment": "new"}]}
        ]}
        issues = notes_structure_issues(plan)
        assert len(issues) == 1
        assert "non-empty" in issues[0]

    def test_add_new_slide_speaker_notes_allowed(self):
        plan = {"actions": [
            {"type": "add_new_slide", "slide_number": 7,
             "speaker_notes": "Full notes for new slide"}
        ]}
        assert notes_structure_issues(plan) == []


class TestSourceInventoryEntries:
    def test_queries_key(self):
        src = {"queries": [{"source_id": "S1"}, {"source_id": "S2"}]}
        assert len(source_inventory_entries(src)) == 2

    def test_entries_key(self):
        src = {"entries": [{"source_id": "S1"}]}
        assert len(source_inventory_entries(src)) == 1

    def test_none_input(self):
        assert source_inventory_entries(None) == []

    def test_list_input(self):
        assert source_inventory_entries([1, 2]) == []


class TestActionIds:
    def test_finding_ids(self):
        action = {"finding_ids": ["F-01", "F-02"]}
        assert action_ids(action) == {"F-01", "F-02"}

    def test_verification_ids(self):
        action = {"verification_ids": ["V-01"]}
        assert action_ids(action) == {"V-01"}

    def test_string_value(self):
        action = {"finding_ids": "F-01"}
        assert action_ids(action) == {"F-01"}

    def test_combined(self):
        action = {"finding_ids": ["F-01"], "addresses_findings": ["F-02"]}
        assert action_ids(action) == {"F-01", "F-02"}


class TestActionSourceTokens:
    def test_source_basis_list_of_dicts(self):
        action = {"source_basis": [{"source_id": "SRC-01"}, {"source_id": "SRC-02"}]}
        tokens = action_source_tokens(action)
        assert "SRC-01" in tokens
        assert "SRC-02" in tokens

    def test_audit_basis_fallback(self):
        action = {"audit_basis": [{"source_id": "SRC-01"}]}
        assert "SRC-01" in action_source_tokens(action)

    def test_empty(self):
        assert action_source_tokens({}) == set()


class TestSlideTitle:
    def test_from_placeholder(self):
        slide = {"texts": [{"placeholder_type": "title", "text": "My Title"}]}
        assert slide_title(slide) == "My Title"

    def test_fallback_to_title_key(self):
        slide = {"title": "Fallback Title", "texts": []}
        assert slide_title(slide) == "Fallback Title"

    def test_empty(self):
        slide = {"texts": []}
        assert slide_title(slide) == ""


class TestIsBoilerplate:
    def test_blank_slide(self):
        assert is_boilerplate({"is_blank": True, "texts": []})

    def test_disclaimer(self):
        slide = {"texts": [{"placeholder_type": "title", "text": "Disclaimer"}]}
        assert is_boilerplate(slide)

    def test_content_slide(self):
        slide = {"texts": [{"placeholder_type": "title", "text": "CPM6 Architecture"}]}
        assert not is_boilerplate(slide)
