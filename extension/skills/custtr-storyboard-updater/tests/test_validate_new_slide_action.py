"""Tests for create_additions_deck.validate_new_slide_action()."""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from create_additions_deck import validate_new_slide_action


def _action(**overrides):
    base = {
        "title": "Test Slide",
        "learning_goal": "Understand X",
        "why_this_slide_exists": "Parity gap",
        "what_customer_should_understand": "Key takeaway",
        "speaker_notes": " ".join(["word"] * 85),
        "slide_layout": "cards",
        "cards": [
            {"heading": "Card A", "bullets": ["bullet 1"]},
            {"heading": "Card B", "bullets": ["bullet 2"]},
        ],
    }
    base.update(overrides)
    return base


class TestRequiredFields:
    def test_valid_action_passes(self):
        validate_new_slide_action(_action())

    def test_missing_title(self):
        with pytest.raises(ValueError, match="missing.*title"):
            validate_new_slide_action(_action(title=""))

    def test_missing_learning_goal(self):
        with pytest.raises(ValueError, match="missing.*learning_goal"):
            validate_new_slide_action(_action(learning_goal=""))

    def test_missing_speaker_notes(self):
        with pytest.raises(ValueError, match="missing.*speaker_notes"):
            validate_new_slide_action(_action(speaker_notes=""))

    def test_short_speaker_notes(self):
        with pytest.raises(ValueError, match=">=80 words"):
            validate_new_slide_action(_action(speaker_notes="too short"))


class TestLayoutValidation:
    def test_missing_layout(self):
        with pytest.raises(ValueError, match="missing slide_layout"):
            validate_new_slide_action(_action(slide_layout=""))

    def test_invalid_layout(self):
        with pytest.raises(ValueError, match="unknown slide_layout"):
            validate_new_slide_action(_action(slide_layout="fancy_layout"))

    def test_body_field_rejected(self):
        with pytest.raises(ValueError, match="'body' is not a valid field"):
            validate_new_slide_action(_action(body="some text"))

    def test_cards_missing_data_field(self):
        a = _action()
        del a["cards"]
        with pytest.raises(ValueError, match="missing required field 'cards'"):
            validate_new_slide_action(a)

    def test_comparison_table_missing_table(self):
        with pytest.raises(ValueError, match="missing required field 'table'"):
            validate_new_slide_action(_action(slide_layout="comparison_table"))

    def test_block_diagram_missing_diagram(self):
        with pytest.raises(ValueError, match="missing required field 'diagram'"):
            validate_new_slide_action(_action(slide_layout="block_diagram"))

    def test_ascii_diagram_missing_ascii_art(self):
        with pytest.raises(ValueError, match="missing required field 'ascii_art'"):
            validate_new_slide_action(_action(slide_layout="ascii_diagram"))

    def test_two_column_missing_columns(self):
        with pytest.raises(ValueError, match="missing required field 'columns'"):
            validate_new_slide_action(_action(slide_layout="two_column"))

    def test_key_takeaway_missing_statement(self):
        with pytest.raises(ValueError, match="missing required field 'statement'"):
            validate_new_slide_action(_action(slide_layout="key_takeaway"))

    def test_valid_comparison_table(self):
        validate_new_slide_action(_action(
            slide_layout="comparison_table",
            table={"headers": ["A", "B"], "rows": [["1", "2"]]},
        ))

    def test_valid_key_takeaway(self):
        validate_new_slide_action(_action(
            slide_layout="key_takeaway",
            statement="The key insight is X.",
        ))


class TestStrictQuality:
    def test_strict_cards_generic_heading(self):
        with pytest.raises(ValueError, match="generic anti-pattern"):
            validate_new_slide_action(
                _action(cards=[
                    {"heading": "What it is", "bullets": ["x"]},
                    {"heading": "Card B", "bullets": ["y"]},
                ]),
                strict_quality=True,
            )

    def test_strict_cards_too_few(self):
        with pytest.raises(ValueError, match=">=2 cards"):
            validate_new_slide_action(
                _action(cards=[{"heading": "Only one", "bullets": ["x"]}]),
                strict_quality=True,
            )

    def test_strict_comparison_table_too_few_columns(self):
        with pytest.raises(ValueError, match=">=3 columns"):
            validate_new_slide_action(
                _action(
                    slide_layout="comparison_table",
                    table={"headers": ["A", "B"], "rows": [["1", "2"], ["3", "4"]]},
                ),
                strict_quality=True,
            )

    def test_strict_comparison_table_too_few_rows(self):
        with pytest.raises(ValueError, match=">=2 rows"):
            validate_new_slide_action(
                _action(
                    slide_layout="comparison_table",
                    table={"headers": ["A", "B", "C"], "rows": [["1", "2", "3"]]},
                ),
                strict_quality=True,
            )

    def test_strict_block_diagram_no_boxes(self):
        with pytest.raises(ValueError, match="no diagram.boxes"):
            validate_new_slide_action(
                _action(
                    slide_layout="block_diagram",
                    diagram={"boxes": [], "connectors": []},
                ),
                strict_quality=True,
            )
