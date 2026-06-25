"""Tests for build_parity_matrix.py."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from build_parity_matrix import build_matrix, find_candidates, _is_dedicated


def _slide(num, title, *body_texts, images=None):
    texts = [{"placeholder_type": "title", "shape_name": "Title", "text": title}]
    for bt in body_texts:
        texts.append({"placeholder_type": "body", "shape_name": "Content Placeholder", "text": bt})
    s = {"slide_number": num, "texts": texts}
    if images is not None:
        s["images"] = images
    return s


def _deck(*slides):
    return {"slides": list(slides)}


VARIANTS = ["CPM5", "CPM6", "MDB"]


class TestIsDedicated:
    def test_exact_match(self):
        assert _is_dedicated("CPM6 Architecture", "CPM6", VARIANTS)

    def test_not_in_title(self):
        assert not _is_dedicated("PCIe Overview", "CPM6", VARIANTS)

    def test_peer_also_present(self):
        assert not _is_dedicated("CPM5 and CPM6 Comparison", "CPM6", VARIANTS)

    def test_case_insensitive(self):
        assert _is_dedicated("cpm6 features", "CPM6", VARIANTS)


class TestBuildMatrix:
    def test_no_variants(self):
        slides = [_slide(1, "Overview")]
        assert build_matrix(slides, []) == {}

    def test_single_variant_dedicated(self):
        slides = [_slide(3, "CPM5 Architecture")]
        m = build_matrix(slides, ["CPM5"])
        assert 3 in m["CPM5"]["dedicated_slides"]

    def test_variant_absent(self):
        slides = [_slide(3, "CPM5 Architecture"), _slide(5, "MDB Overview")]
        m = build_matrix(slides, VARIANTS)
        assert m["CPM6"]["dedicated_slides"] == []

    def test_architecture_diagram_detected_by_image(self):
        slides = [_slide(3, "CPM5 Architecture", images=[{"src": "img1.png"}])]
        m = build_matrix(slides, ["CPM5"])
        assert m["CPM5"]["architecture_diagram"] is True

    def test_feature_detail_from_body(self):
        body = "Line 1\nLine 2\nLine 3\nLine 4"
        slides = [_slide(4, "CPM5 Features", body)]
        m = build_matrix(slides, ["CPM5"])
        assert m["CPM5"]["feature_detail"] is True

    def test_knowledge_check_detected(self):
        slides = [_slide(7, "CPM5 Knowledge Check")]
        m = build_matrix(slides, ["CPM5"])
        assert m["CPM5"]["knowledge_check"] is True


class TestFindCandidates:
    def test_no_gap_when_all_equal(self):
        variants = ["CPM5", "CPM6"]
        m = {
            "CPM5": {"dedicated_slides": [3], "architecture_diagram": True, "feature_detail": True, "knowledge_check": False},
            "CPM6": {"dedicated_slides": [5], "architecture_diagram": True, "feature_detail": True, "knowledge_check": False},
        }
        candidates, gaps = find_candidates(m, variants)
        assert candidates == []

    def test_gap_detected_for_zero_dedicated(self):
        variants = ["CPM5", "CPM6", "MDB"]
        m = {
            "CPM5": {"dedicated_slides": [3, 4], "architecture_diagram": True, "feature_detail": True, "knowledge_check": False},
            "CPM6": {"dedicated_slides": [], "architecture_diagram": False, "feature_detail": False, "knowledge_check": False},
            "MDB": {"dedicated_slides": [7], "architecture_diagram": True, "feature_detail": True, "knowledge_check": False},
        }
        candidates, gaps = find_candidates(m, variants)
        assert any(c["variant"] == "CPM6" for c in candidates)
        assert not any(c["variant"] == "CPM5" for c in candidates)
        cpm6 = next(c for c in candidates if c["variant"] == "CPM6")
        assert cpm6["advisory"] is True
        assert cpm6["llm_disposition_required"] is True

    def test_no_candidate_when_single_variant(self):
        variants = ["CPM5"]
        m = {"CPM5": {"dedicated_slides": [], "architecture_diagram": False, "feature_detail": False, "knowledge_check": False}}
        candidates, _ = find_candidates(m, variants)
        # Single variant — no peers, so no candidate
        assert candidates == []

    def test_coverage_gaps_populated(self):
        variants = ["CPM5", "CPM6"]
        m = {
            "CPM5": {"dedicated_slides": [3], "architecture_diagram": True, "feature_detail": True, "knowledge_check": False},
            "CPM6": {"dedicated_slides": [], "architecture_diagram": False, "feature_detail": False, "knowledge_check": False},
        }
        _, gaps = find_candidates(m, variants)
        cpm6_gap = next((g for g in gaps if g["variant"] == "CPM6"), None)
        assert cpm6_gap is not None
        assert "dedicated_slides" in cpm6_gap["missing_elements"]
        assert cpm6_gap["advisory"] is True

    def test_priority_high_when_peer_has_2_plus(self):
        variants = ["CPM5", "CPM6"]
        m = {
            "CPM5": {"dedicated_slides": [3, 4], "architecture_diagram": True, "feature_detail": True, "knowledge_check": False},
            "CPM6": {"dedicated_slides": [], "architecture_diagram": False, "feature_detail": False, "knowledge_check": False},
        }
        candidates, _ = find_candidates(m, variants)
        cpm6 = next(c for c in candidates if c["variant"] == "CPM6")
        assert cpm6["priority"] == "high"

    def test_schema_keys_present(self):
        variants = ["CPM5", "CPM6"]
        m = {
            "CPM5": {"dedicated_slides": [3], "architecture_diagram": True, "feature_detail": True, "knowledge_check": False},
            "CPM6": {"dedicated_slides": [], "architecture_diagram": False, "feature_detail": False, "knowledge_check": False},
        }
        candidates, gaps = find_candidates(m, variants)
        cpm6 = next(c for c in candidates if c["variant"] == "CPM6")
        assert "variant" in cpm6
        assert "reason" in cpm6
        assert "visual_intent" in cpm6
        assert "priority" in cpm6
        assert "advisory" in cpm6
        assert "llm_disposition_required" in cpm6
