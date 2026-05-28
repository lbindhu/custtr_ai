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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deck-extract", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    deck = safe_load_json(args.deck_extract, "deck_extract.json")
    slides = deck["slides"]
    objectives = extract_objectives(slides)
    roles = []
    for slide in slides:
        text = "\n".join(i["text"] for i in slide.get("texts", []))
        roles.append({
            "slide_number": slide["slide_number"],
            "title": slide.get("title", ""),
            "role": classify_slide(slide.get("title", ""), text, slide.get("notes", "")),
        })

    title = infer_deck_title(slides) or next((s.get("title", "") for s in slides if s.get("title")), "")
    talking_points = derive_key_talking_points(slides, objectives)
    primary_message = (
        f"Teach customers the purpose, architecture, tradeoffs, and recommended use of {title}."
        if title else
        "Teach customers the purpose, architecture, tradeoffs, and recommended use of the module topic."
    )

    summary_slides = [r["slide_number"] for r in roles if r["role"] == "summary"]
    knowledge_checks = [r["slide_number"] for r in roles if r["role"] == "knowledge_check"]

    model = {
        "schema_version": "1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "deck": deck["deck"],
        "title": title,
        "primary_message": primary_message,
        "audience": "AMD customer training learners; exact audience should be confirmed from course context when available.",
        "learning_objectives": objectives,
        "key_talking_points": talking_points,
        "slide_roles": roles,
        "knowledge_checks": knowledge_checks,
        "summary_slides": summary_slides,
        "concept_coverage": concept_coverage(slides, objectives),
        "flow_questions": [
            "What is the primary message of this deck?",
            "What are the key talking points derived from objectives and the full slide flow?",
            "What is new from AMD in this topic area?",
            "Which existing claims, examples, recommendations, knowledge checks, and summary statements become outdated or incomplete?",
            "After updates, does the deck still form a logical learning path?",
        ],
        "flow_validation": {
            "status": "requires_human_or_source_augmented_review",
            "reason": "Story model is inferred from deck text. Audit deltas from sources must be mapped to objectives, body, assessments, and summary before execution.",
        },
        "generational_questions": [
            "What generation does this deck primarily cover (e.g. Gen 1 Versal Premium, Gen 2 Versal Premium)?",
            "What are the top 5 most impactful changes between that generation and the target generation?",
            "Which of those changes affect slides that do NOT obviously mention the changed topic (cross-domain impact)?",
            "Which slides are generation-agnostic (e.g. generic architecture concepts) vs. generation-specific (e.g. specific IP versions, feature tables)?",
            "For each product variant or IP block mentioned in the deck, has it changed in the target generation or is it carried forward unchanged?",
        ],
        "stale_terms_template": infer_stale_terms_template(slides),
    }
    Path(args.output).write_text(json.dumps(model, indent=2, ensure_ascii=False), encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
