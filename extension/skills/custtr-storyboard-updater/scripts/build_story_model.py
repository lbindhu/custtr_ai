#!/usr/bin/env python3
import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from json_helpers import safe_load_json  # noqa: E402


STOP = {
    "the", "and", "for", "with", "that", "this", "from", "into", "are", "you",
    "will", "able", "after", "completing", "module", "describe", "identify",
    "support", "supports", "slide", "your", "knowledge", "apply", "solution",
    "solutions", "overview", "features", "devices", "device",
    # Generic AMD/product words that appear in every deck and add no signal
    "amd", "soc", "its", "list", "slice", "adaptive", "versal", "xilinx",
    "vivado", "vitis", "has", "can", "used", "use", "use", "using",
    "each", "also", "when", "how", "two", "one", "all", "any",
}


def norm(text):
    return re.sub(r"\s+", " ", text or "").strip()


def tokens(text):
    return [
        t.lower()
        for t in re.findall(r"[A-Za-z][A-Za-z0-9+/-]{2,}", text or "")
        if t.lower() not in STOP
    ]


def classify_slide(title, text, notes):
    low = f"{title} {text}".lower()
    if not title and not text.strip():
        return "blank"
    if "objective" in low:
        return "objectives"
    if "apply your knowledge" in low or "correct answers" in (notes or "").lower():
        return "knowledge_check"
    if "summary" in low:
        return "summary"
    if "disclaimer" in low or "attributions" in low:
        return "boilerplate"
    if "recommended" in low or "recommendation" in low:
        return "recommendation"
    if any(k in low for k in ["comparison", "versus", " vs "]):
        return "comparison"
    if any(k in low for k in ["architecture", "overview", "basics", "concept"]):
        return "concept_setup"
    return "deep_dive"


def extract_objectives(slides):
    for slide in slides:
        if classify_slide(slide.get("title", ""), "\n".join(i["text"] for i in slide.get("texts", [])), slide.get("notes", "")) == "objectives":
            objective_text = []
            for item in slide.get("texts", []):
                txt = norm(item["text"])
                if "OBJECTIVE" in txt or txt.lower().startswith("after completing"):
                    continue
                if len(txt) > 12:
                    objective_text.append(txt)
            return objective_text
    return []


def infer_deck_title(slides):
    if not slides:
        return ""
    first = slides[0]
    candidates = []
    if first.get("title"):
        candidates.append(first["title"])
    for item in first.get("texts", []):
        txt = norm(item.get("text", "").replace("\n", " "))
        if len(txt) > 8 and not txt.startswith("202"):
            candidates.append(txt)
    if not candidates:
        return ""
    return max(candidates, key=len)


def concept_coverage(slides, objectives):
    concepts = []
    objective_tokens = Counter()
    for objective in objectives:
        objective_tokens.update(tokens(objective))
    for word, _ in objective_tokens.most_common(12):
        covered = []
        assessed = []
        for slide in slides:
            hay = f"{slide.get('title','')} " + " ".join(i["text"] for i in slide.get("texts", []))
            if word in tokens(hay):
                role = classify_slide(slide.get("title", ""), hay, slide.get("notes", ""))
                if role == "knowledge_check":
                    assessed.append(slide["slide_number"])
                elif role not in {"objectives", "summary", "boilerplate", "blank"}:
                    covered.append(slide["slide_number"])
        concepts.append({"concept": word, "covered_on": covered, "assessed_on": assessed})
    return concepts


def derive_key_talking_points(slides, objectives):
    counts = Counter()
    for slide in slides:
        role = classify_slide(slide.get("title", ""), " ".join(i["text"] for i in slide.get("texts", [])), slide.get("notes", ""))
        if role in {"boilerplate", "blank", "knowledge_check"}:
            continue
        counts.update(tokens(slide.get("title", "")))
        for item in slide.get("texts", []):
            counts.update(tokens(item["text"]))
    for objective in objectives:
        counts.update(tokens(objective))
    return [word for word, _ in counts.most_common(10)]


VERSION_RE = re.compile(r"\b(20\d{2}\.\d)\b")
PRODUCT_RE = re.compile(
    r"\b("
    r"[A-Z]{2,5}\d{1,2}"          # e.g. CPM5, GTY4, LPDDR5
    r"|Gen\s*\d+"                  # e.g. Gen 5, Gen6
    r"|PCIe\b"
    r"|CXL\b"
    r"|DDR[45]\b"
    r"|LPDDR[45]\b"
    r"|HBM\d?\b"
    r"|[A-Z][a-z]+\s+(?:Premium|AI\s+Core|AI\s+Edge|Prime|HBM)"  # e.g. Versal Premium
    r")\b",
    re.IGNORECASE,
)


def infer_stale_terms_template(slides):
    """Scan deck text for version tokens and product/IP names to seed stale_terms.json."""
    version_hits = Counter()
    product_hits = Counter()
    for slide in slides:
        role = classify_slide(
            slide.get("title", ""),
            " ".join(i["text"] for i in slide.get("texts", [])),
            slide.get("notes", ""),
        )
        if role in {"boilerplate", "blank"}:
            continue
        hay = f"{slide.get('title', '')} " + " ".join(i["text"] for i in slide.get("texts", []))
        hay += " " + (slide.get("notes") or "")
        for m in VERSION_RE.finditer(hay):
            version_hits[m.group(1)] += 1
        for m in PRODUCT_RE.finditer(hay):
            product_hits[m.group(1).strip()] += 1

    entries = []
    for token, count in version_hits.most_common(10):
        entries.append({
            "_template": True,
            "token": token,
            "type": "version",
            "occurrences_in_deck": count,
            "replacement": "",
            "rationale": "TODO: confirm whether this version token is stale in the target release",
            "source_ids": [],
        })
    for token, count in product_hits.most_common(15):
        entries.append({
            "_template": True,
            "token": token,
            "type": "product_or_ip",
            "occurrences_in_deck": count,
            "replacement": "",
            "rationale": "TODO: confirm whether this product/IP name has changed or been superseded",
            "source_ids": [],
        })
    return entries


def _shape_evidence(slide):
    evidence = []
    for item in slide.get("texts", [])[:6]:
        quote = norm(item.get("text", ""))
        if not quote:
            continue
        evidence.append({
            "type": "shape",
            "slide_number": slide.get("slide_number"),
            "shape_id": item.get("shape_id"),
            "quote": quote[:240],
        })
    if slide.get("notes"):
        evidence.append({
            "type": "notes",
            "slide_number": slide.get("slide_number"),
            "quote": norm(slide.get("notes", ""))[:240],
        })
    return evidence


def build_scaffold(deck, target_version=""):
    slides = deck["slides"]
    objectives = extract_objectives(slides)
    roles = []
    interpretations = []
    for slide in slides:
        text = "\n".join(i["text"] for i in slide.get("texts", []))
        role = classify_slide(slide.get("title", ""), text, slide.get("notes", ""))
        roles.append({
            "slide_number": slide["slide_number"],
            "title": slide.get("title", ""),
            "role": role,
        })
        interpretations.append({
            "slide_number": slide["slide_number"],
            "title": slide.get("title", ""),
            "role": role,
            "role_rationale": "TODO: confirm or refine this heuristic role from slide content.",
            "teaching_purpose": "",
            "core_claims": [],
            "concepts_introduced": [],
            "concepts_reinforced": [],
            "generation_specificity": "unknown",
            "visual_dependency": "medium",
            "notes_dependency": "medium" if slide.get("notes") else "none",
            "evidence": _shape_evidence(slide),
        })

    title = infer_deck_title(slides) or next((s.get("title", "") for s in slides if s.get("title")), "")
    talking_points = derive_key_talking_points(slides, objectives)
    return {
        "schema_version": "2.0",
        "_status": "scaffold_requires_llm_completion",
        "_authoring_note": (
            "This is a scaffold generated from deterministic deck extraction. "
            "The LLM must complete instructional interpretation fields and remove "
            "_status/_authoring_note before validation."
        ),
        "deck_identity": {
            "deck": deck["deck"],
            "title": title,
            "target_version": target_version,
            "audience": "AMD customer training learners; confirm from course context when available.",
            "module_scope": "",
        },
        "title": title,
        "primary_message": "",
        "key_talking_points": talking_points,
        "slide_interpretations": interpretations,
        "learning_objectives": [
            {
                "objective": objective,
                "source_slide": None,
                "covered_by_slides": [],
                "assessed_by_slides": [],
            }
            for objective in objectives
        ],
        "concept_flow": [],
        "knowledge_check_alignment": [],
        "summary_alignment": [],
        "source_research_hypotheses": [],
        "stale_terms_candidates": infer_stale_terms_template(slides),
        "slide_roles": roles,
        "knowledge_checks": [r["slide_number"] for r in roles if r["role"] == "knowledge_check"],
        "summary_slides": [r["slide_number"] for r in roles if r["role"] == "summary"],
        "concept_coverage": concept_coverage(slides, objectives),
    }


def build_prompt(deck, scaffold_path, target_version=""):
    slide_count = deck.get("slide_count", len(deck.get("slides") or []))
    target = target_version or "(target version not supplied)"
    return f"""# LLM Story Model Authoring Prompt

You are authoring `story_model.json` for an AMD storyboard update.

Inputs:
- `deck_extract.json`: deterministic extraction of every slide, text shape, and speaker-note block.
- `story_model_scaffold.json`: a heuristic scaffold. Treat it as a starting point, not truth.
- `references/story_model_guide.md`: required authoring rules and schema.

Task:
1. Read `deck_extract.json` and the scaffold at `{scaffold_path}`.
2. Replace heuristic placeholders with your own instructional interpretation.
3. Produce `story_model.json` with `schema_version: "2.0"`.
4. Cover all {slide_count} slides exactly once in `slide_interpretations`.
5. Use evidence references to existing shape IDs or notes quotes from `deck_extract.json`.
6. Do not make source-backed clears, findings, or correctness claims. Source-backed audit happens later.
7. After writing `story_model.json`, run:

```bash
python3 "$SKILL/scripts/validate_story_model.py" \\
  --deck-extract "$WORK/deck_extract.json" \\
  --story-model "$WORK/story_model.json"
```

Target version: {target}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deck-extract", required=True)
    ap.add_argument("--output")
    ap.add_argument("--prompt-output")
    ap.add_argument("--scaffold-output")
    ap.add_argument("--target-version", default="")
    args = ap.parse_args()

    deck = safe_load_json(args.deck_extract, "deck_extract.json")
    scaffold = build_scaffold(deck, args.target_version)

    scaffold_output = Path(args.scaffold_output or args.output) if (args.scaffold_output or args.output) else None
    if scaffold_output:
        scaffold_output.write_text(json.dumps(scaffold, indent=2, ensure_ascii=False), encoding="utf-8")
        print(scaffold_output)

    if args.prompt_output:
        scaffold_ref = scaffold_output or Path("story_model_scaffold.json")
        prompt = build_prompt(deck, scaffold_ref, args.target_version)
        Path(args.prompt_output).write_text(prompt, encoding="utf-8")
        print(args.prompt_output)


if __name__ == "__main__":
    main()
