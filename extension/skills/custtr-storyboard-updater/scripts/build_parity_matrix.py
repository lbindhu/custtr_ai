#!/usr/bin/env python3
"""Build a variant × coverage parity matrix from deck_extract.json.

Reads product_variants from stale_terms.json (or --variant-pattern) and
checks which variants have dedicated slides, architecture diagrams, feature
detail bullets, and knowledge-check slides. Emits new_slide_candidates for
variants with zero dedicated slides when peers have >=1.

Output: parity_matrix.json
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from constants import KNOWLEDGE_RE  # noqa: E402
from json_helpers import safe_load_json  # noqa: E402

# Shape-name substrings that suggest an architecture/block diagram image or shape.
_DIAGRAM_SHAPE_NAMES = ("diagram", "arch", "block", "figure", "image")


def _slide_title(slide: dict) -> str:
    for sh in slide.get("texts") or []:
        ptype = (sh.get("placeholder_type") or "").lower()
        if ptype in {"title", "ctrtitle"}:
            return sh.get("text") or ""
    return slide.get("title") or ""


def _slide_text(slide: dict) -> str:
    parts = [sh.get("text") or "" for sh in slide.get("texts") or []]
    parts.append(slide.get("notes") or "")
    return " ".join(parts)


def _has_diagram(slide: dict) -> bool:
    for sh in slide.get("texts") or []:
        name = (sh.get("shape_name") or "").lower()
        if any(kw in name for kw in _DIAGRAM_SHAPE_NAMES):
            return True
    for img in slide.get("images") or []:
        return True  # any image counts as a potential diagram
    return False


def _has_feature_detail(slide: dict) -> bool:
    # A slide with a body shape containing >3 distinct text items is "feature detail".
    body_shapes = [
        sh for sh in (slide.get("texts") or [])
        if (sh.get("placeholder_type") or "").lower() not in {"title", "ctrtitle", ""}
        or not sh.get("placeholder_type")
    ]
    for sh in body_shapes:
        lines = [ln.strip() for ln in (sh.get("text") or "").splitlines() if ln.strip()]
        if len(lines) > 3:
            return True
    return False


def _is_knowledge_check(slide: dict) -> bool:
    return bool(KNOWLEDGE_RE.search(_slide_title(slide)) or KNOWLEDGE_RE.search(_slide_slide_text_body(slide)))


def _slide_slide_text_body(slide: dict) -> str:
    return " ".join(sh.get("text") or "" for sh in (slide.get("texts") or []))


def _is_dedicated(title: str, variant: str, all_variants: list[str]) -> bool:
    """True if title mentions this variant and does NOT mention other variants."""
    title_lower = title.lower()
    v_lower = variant.lower()
    if v_lower not in title_lower:
        return False
    others = [v.lower() for v in all_variants if v.lower() != v_lower]
    return not any(o in title_lower for o in others)


def build_matrix(slides: list[dict], variants: list[str]) -> dict:
    """Return matrix dict: variant -> {dedicated_slides, architecture_diagram, feature_detail, knowledge_check}."""
    matrix: dict[str, dict] = {}
    for v in variants:
        matrix[v] = {
            "dedicated_slides": [],
            "architecture_diagram": False,
            "feature_detail": False,
            "knowledge_check": False,
        }

    for slide in slides:
        num = slide.get("slide_number")
        title = _slide_title(slide)
        full_text = _slide_text(slide)
        is_kc = KNOWLEDGE_RE.search(title) is not None or KNOWLEDGE_RE.search(full_text) is not None
        has_diag = _has_diagram(slide)
        has_feat = _has_feature_detail(slide)

        for v in variants:
            if _is_dedicated(title, v, variants):
                matrix[v]["dedicated_slides"].append(num)
                if has_diag:
                    matrix[v]["architecture_diagram"] = True
                if has_feat:
                    matrix[v]["feature_detail"] = True
                if is_kc:
                    matrix[v]["knowledge_check"] = True

    return matrix


def find_candidates(matrix: dict, variants: list[str]) -> tuple[list[dict], list[dict]]:
    """Return (new_slide_candidates, coverage_gaps)."""
    max_dedicated = max((len(matrix[v]["dedicated_slides"]) for v in variants), default=0)
    candidates = []
    gaps = []

    for v in variants:
        m = matrix[v]
        dedicated_count = len(m["dedicated_slides"])
        missing = []
        if dedicated_count == 0:
            missing.append("dedicated_slides")
        if not m["architecture_diagram"]:
            missing.append("architecture_diagram")
        if not m["feature_detail"]:
            missing.append("feature_detail")

        peers_with_slides = [p for p in variants if p != v and len(matrix[p]["dedicated_slides"]) >= 1]
        if dedicated_count == 0 and peers_with_slides:
            peer_counts = ", ".join(
                f"{p} ({len(matrix[p]['dedicated_slides'])})"
                for p in peers_with_slides
            )
            candidates.append({
                "variant": v,
                "reason": f"0 dedicated slides; peers {peer_counts} have ≥1",
                "recommended_layout": "title_and_content",
                "priority": "high" if max_dedicated >= 2 else "medium",
            })

        if missing:
            gaps.append({"variant": v, "missing_elements": missing})

    return candidates, gaps


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--deck-extract", required=True, help="Path to deck_extract.json")
    ap.add_argument("--stale-terms", required=True, help="Path to stale_terms.json")
    ap.add_argument("--output", required=True, help="Output path for parity_matrix.json")
    ap.add_argument("--variant-pattern", default="", help="Regex to extract variant names from slide titles (fallback if stale_terms has no product_variants)")
    args = ap.parse_args()

    deck = safe_load_json(args.deck_extract, "deck_extract.json")
    stale = safe_load_json(args.stale_terms, "stale_terms.json")

    variants: list[str] = stale.get("product_variants") or []
    if not variants and args.variant_pattern:
        pat = re.compile(args.variant_pattern)
        seen: set[str] = set()
        for slide in deck.get("slides") or []:
            title = _slide_title(slide)
            for m in pat.finditer(title):
                seen.add(m.group(0))
        variants = sorted(seen)

    if not variants:
        print(json.dumps({
            "schema_version": "1.0",
            "variants": [],
            "matrix": {},
            "new_slide_candidates": [],
            "coverage_gaps": [],
            "_note": "No product_variants in stale_terms.json and no --variant-pattern supplied; skipping parity analysis.",
        }, indent=2, ensure_ascii=False))
        Path(args.output).write_text(
            json.dumps({
                "schema_version": "1.0",
                "variants": [],
                "matrix": {},
                "new_slide_candidates": [],
                "coverage_gaps": [],
                "_note": "No product_variants configured.",
            }, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return

    slides = deck.get("slides") or []
    matrix = build_matrix(slides, variants)
    candidates, gaps = find_candidates(matrix, variants)

    result = {
        "schema_version": "1.0",
        "variants": variants,
        "matrix": matrix,
        "new_slide_candidates": candidates,
        "coverage_gaps": gaps,
    }
    Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if candidates:
        print(
            f"\nWARNING: {len(candidates)} variant(s) with 0 dedicated slides while peers have ≥1. "
            "Consider add_new_slide actions for each.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
