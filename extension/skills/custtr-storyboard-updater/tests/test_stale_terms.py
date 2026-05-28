"""Tests for stale_terms.iter_findings() and is_intentionally_kept()."""

from stale_terms import iter_findings, is_intentionally_kept


class TestIterFindings:
    def test_basic_match(self, sample_stale_terms):
        hits = list(iter_findings("The MI250X accelerator", sample_stale_terms))
        tokens = [e["token"] for e, _ in hits]
        assert "MI250X" in tokens

    def test_case_insensitive(self, sample_stale_terms):
        hits = list(iter_findings("the mi250x card", sample_stale_terms))
        tokens = [e["token"] for e, _ in hits]
        assert "MI250X" in tokens

    def test_skip_preceded_by(self, sample_stale_terms):
        hits = list(iter_findings("legacy ROCm 5.x stack", sample_stale_terms))
        tokens = [e["token"] for e, _ in hits]
        assert "ROCm 5.x" not in tokens

    def test_skip_followed_by(self, sample_stale_terms):
        hits = list(iter_findings("ROCm 5.x (deprecated) note", sample_stale_terms))
        tokens = [e["token"] for e, _ in hits]
        assert "ROCm 5.x" not in tokens

    def test_no_guards_match(self, sample_stale_terms):
        hits = list(iter_findings("Use ROCm 5.x for training", sample_stale_terms))
        tokens = [e["token"] for e, _ in hits]
        assert "ROCm 5.x" in tokens

    def test_multiple_tokens(self, sample_stale_terms):
        hits = list(iter_findings("MI250X and Radeon Pro W7900", sample_stale_terms))
        tokens = {e["token"] for e, _ in hits}
        assert "MI250X" in tokens
        assert "Radeon Pro W7900" in tokens

    def test_empty_text(self, sample_stale_terms):
        hits = list(iter_findings("", sample_stale_terms))
        assert hits == []

    def test_empty_terms(self):
        hits = list(iter_findings("some text", {"stale_terms": []}))
        assert hits == []


class TestIsIntentionallyKept:
    def test_kept_on_listed_slide(self, sample_stale_terms):
        assert is_intentionally_kept("MI250X", 3, sample_stale_terms) is True

    def test_not_kept_on_unlisted_slide(self, sample_stale_terms):
        assert is_intentionally_kept("MI250X", 5, sample_stale_terms) is False

    def test_case_insensitive_kept(self, sample_stale_terms):
        assert is_intentionally_kept("mi250x", 3, sample_stale_terms) is True
