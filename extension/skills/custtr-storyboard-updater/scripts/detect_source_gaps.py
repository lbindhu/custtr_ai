#!/usr/bin/env python3
"""Phase 2.5 — Advisory claim-token coverage lint.

For every content slide in deck_extract.json, extract candidate factual claims
(numeric specs, IP names, protocol versions, channel/lane counts, recommendation
verbs, etc.) and check whether matching tokens appear in reference_extract.json.
Emits coverage_gaps.json listing claim-token lint signals that may need more
source gathering.

Important: token overlap is not proof that a source supports a claim, and
missing token overlap is not proof that no source exists. The LLM-authored audit
must judge source-to-claim entailment and disposition each signal.

Output schema:
  {
    "schema_version": "1.0",
    "advisory": true,
    "llm_disposition_required": bool,
    "deck": "...",
    "total_slides": N,
    "slides_fully_covered": [int, ...],
    "slides_with_gaps": [
      {
        "slide_number": int,
        "title": str,
        "uncovered_claims": [str, ...],
        "claim_token_lint_signals": [str, ...],
        "suggested_sources": [str, ...]
      },
      ...
    ],
    "summary": {
      "total_uncovered_claims": int,
      "slides_needing_source_gathering": int
    }
  }

Exit codes:
  0  no claim-token lint signals were emitted
  1  one or more advisory claim-token lint signals were emitted
  2  hard error (missing inputs, malformed JSON)

The planner may use these signals as search hints. It must not treat them as
authoritative proof of support or lack of support.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from json_helpers import safe_load_json  # noqa: E402

# ─── Claim extractors ──────────────────────────────────────────────────────
# Each regex extracts a normalized "claim token" that we look up in the
# reference corpus. Matches are only lint signals; the LLM must still decide
# whether the source actually supports, contradicts, or merely mentions a claim.

# Numeric specs with units. e.g. "32 GT/s", "1.7 GHz", "256-bit", "8 lanes"
RATE_RE = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(GT/s|MT/s|GHz|MHz|Gbps|Mbps|Gb/s|Mb/s|GB/s|MB/s|"
    r"bit|bits|KB|MB|GB|TB|lanes?|channels?|cores?|vectors?|tags?|VCs?|"
    r"vector|nm)\b",
    re.IGNORECASE,
)

# Protocol / standard versions. e.g. "PCIe Gen 6", "PCIe 6.1", "CXL 3.1",
# "AXI4-MM", "PCIe 5.0"
VERSION_RE = re.compile(
    r"\b(PCIe|CXL|CCIX|AXI|JESD|DDR|HBM|LPDDR|USB|UCIe|Arm|ARM|Cortex)\b"
    r"[\s-]*"
    r"(Gen\s*\d+|v?\d+\.\d+(?:\.\d+)?|\d+)\b",
    re.IGNORECASE,
)

# IP / block names — single capitalized tokens or short multi-word that look
# like AMD product names: CPM6, MDB5, QDMA, XDMA, NoC, PMC, PL, PS, RPU, APU,
# CCIX, CXL, AER, ECRC, ATS, ACS, ARI, PASID, SR-IOV, MSI-X.
IP_RE = re.compile(
    r"\b("
    r"CPM[0-9]|MDB[0-9]|QDMA|XDMA|HDMA|NoC|PMC|RPU|APU|"
    r"AER|ECRC|ATS|ACS|ARI|PASID|SR-IOV|MSI-X|"
    r"Cortex-[ARM][0-9]+[A-Z]*|"
    r"Versal\s+(?:AI\s+Edge|Premium|Prime|HBM|RF)(?:\s+Series\s+Gen\s+\d)?"
    r")\b"
)

# Recommendation / definitive statements (lower precision; only flagged when
# nothing else matches the slide).
RECOMMEND_RE = re.compile(
    r"\b(recommended|recommend|deprecated|obsolete|replaces?|supersedes?|"
    r"successor|new in|starting (?:in|with)|introduced in)\b",
    re.IGNORECASE,
)


def extract_claims(text: str) -> list[str]:
    """Return normalized claim tokens found in `text`. Order-preserving, deduped."""
    seen: dict[str, None] = {}
    if not text:
        return []

    for m in RATE_RE.finditer(text):
        # Normalize unit casing for matching
        unit = m.group(2).lower().replace("gb/s", "gbps").replace("mb/s", "mbps")
        token = f"{m.group(1)} {unit}"
        seen.setdefault(token, None)

    for m in VERSION_RE.finditer(text):
        family = m.group(1).upper()
        ver = re.sub(r"\s+", " ", m.group(2)).strip()
        token = f"{family} {ver}"
        seen.setdefault(token, None)

    for m in IP_RE.finditer(text):
        token = re.sub(r"\s+", " ", m.group(0).strip())
        seen.setdefault(token, None)

    # Recommendations are only included if we found at least one other claim
    # in the same text (avoids flagging headers like "Recommended for New Designs"
    # in isolation).
    if seen:
        for m in RECOMMEND_RE.finditer(text):
            seen.setdefault(f"recommendation:{m.group(0).lower()}", None)

    return list(seen.keys())


def build_source_index(reference_extract: dict) -> tuple[set[str], list[dict]]:
    """Return (claim_token_set, raw_entries) extracted from reference_extract.json.

    Looks at every entry's `claim_keys`, `title`, `content`, `summary`, `text`
    field — whichever exist. claim_keys is the canonical place to put
    pre-normalized tokens; the rest are fallback content scans.
    """
    if isinstance(reference_extract, list):
        entries = reference_extract
    else:
        entries = reference_extract.get("entries") or reference_extract.get("sources") or reference_extract.get("chunks") or []
    if not isinstance(entries, list):
        entries = []

    tokens: set[str] = set()
    for e in entries:
        # Explicit pre-tagged claim_keys (preferred)
        ck = e.get("claim_keys") or []
        if isinstance(ck, list):
            tokens.update(str(k).lower() for k in ck)
        # Fallback: scan free-form content for claim patterns
        blob_parts = []
        for fname in ("title", "summary", "content", "text", "body", "excerpt"):
            v = e.get(fname)
            if isinstance(v, str):
                blob_parts.append(v)
            elif isinstance(v, list):
                blob_parts.extend(str(x) for x in v)
        blob = "\n".join(blob_parts)
        for tok in extract_claims(blob):
            tokens.add(tok.lower())

    return tokens, entries


def suggest_sources(uncovered: list[str]) -> list[str]:
    """Heuristic: turn uncovered claim tokens into source-search suggestions."""
    suggestions: list[str] = []
    upper = " ".join(uncovered).upper()
    if "QDMA" in upper or "XDMA" in upper or "HDMA" in upper:
        suggestions.append("AMD docs.amd.com PG347 (QDMA Subsystem for PCIe)")
        suggestions.append("AMD docs.amd.com PG195 (XDMA Subsystem)")
    if "CPM" in upper or "PCIE" in upper:
        suggestions.append("AMD docs.amd.com PG346 (CPM PCIe Controller)")
        suggestions.append("AMD docs.amd.com PG343 (PL PCIe Controller)")
    if "MDB" in upper:
        suggestions.append("AMD docs.amd.com MDB DMA/Bridge Subsystem product guide")
    if "CXL" in upper:
        suggestions.append("CXL Consortium spec 3.1")
        suggestions.append("AMD Versal Premium Gen 2 CXL solution brief")
    if "PCIE GEN 6" in upper or "PCIE 6" in upper:
        suggestions.append("PCI-SIG PCIe Base Specification Rev 6.1")
    if "ARM" in upper or "CORTEX" in upper:
        suggestions.append("Arm Technical Reference Manual for the relevant Cortex core")
    if "MSI-X" in upper or "SR-IOV" in upper or "AER" in upper or "ATS" in upper:
        suggestions.append("PCI-SIG PCI Express Base Specification (capabilities section)")
    if "VERSAL" in upper:
        suggestions.append("AMD Versal Adaptive SoC product brief (target release)")
    if not suggestions:
        suggestions.append("Targeted NABU / Confluence / web search for the uncovered claim tokens")
    return suggestions


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--deck-extract", required=True)
    ap.add_argument("--reference-extract", required=True,
                    help="Path to reference_extract.json (the source corpus)")
    ap.add_argument("--output", required=True, help="Path for coverage_gaps.json")
    ap.add_argument("--ignore-boilerplate", action="store_true", default=True,
                    help="Skip title, objectives, disclaimer, and obviously boilerplate slides")
    ap.add_argument("--min-claims-to-audit", type=int, default=1,
                    help="Slides with fewer extracted claims than this are skipped as low-signal")
    args = ap.parse_args(argv)

    deck_path = Path(args.deck_extract)
    ref_path = Path(args.reference_extract)
    if not deck_path.is_file():
        print(f"ERROR: deck_extract not found: {deck_path}", file=sys.stderr)
        return 2
    if not ref_path.is_file():
        print(f"ERROR: reference_extract not found: {ref_path}", file=sys.stderr)
        print("       Run Phase 2 source collection first.", file=sys.stderr)
        return 2

    deck = safe_load_json(deck_path, "deck_extract.json")
    ref = safe_load_json(ref_path, "reference_extract.json")

    src_tokens, _entries = build_source_index(ref)

    slides = deck.get("slides") or []
    slides_fully_covered: list[int] = []
    slides_with_gaps: list[dict] = []

    boilerplate_titles = (
        "title", "objectives", "agenda", "disclaimer", "attributions",
        "thank you", "questions", "summary",  # summary is included if it has gaps
    )

    for s in slides:
        slide_no = s.get("slide_number")
        title = (s.get("title") or "").strip()
        title_lc = title.lower()

        if args.ignore_boilerplate and any(b in title_lc for b in ("disclaimer", "attribution", "thank you")):
            continue

        # Combine every shape's text and the speaker notes (if present)
        blob_parts: list[str] = []
        for t in s.get("texts") or []:
            tx = t.get("text") if isinstance(t, dict) else str(t)
            if tx:
                blob_parts.append(tx)
        notes = s.get("notes") or s.get("speaker_notes") or ""
        if notes:
            blob_parts.append(notes)
        blob = "\n".join(blob_parts)

        claims = extract_claims(blob)
        if len(claims) < args.min_claims_to_audit:
            slides_fully_covered.append(slide_no)
            continue

        uncovered = [c for c in claims if c.lower() not in src_tokens]
        if not uncovered:
            slides_fully_covered.append(slide_no)
            continue

        slides_with_gaps.append({
            "slide_number": slide_no,
            "title": title,
            "uncovered_claims": uncovered,
            "claim_token_lint_signals": uncovered,
            "covered_claims": [c for c in claims if c.lower() in src_tokens],
            "suggested_sources": suggest_sources(uncovered),
            "advisory": True,
            "llm_disposition_required": True,
        })

    payload = {
        "schema_version": "1.0",
        "advisory": True,
        "llm_disposition_required": bool(slides_with_gaps),
        "deck": deck.get("deck") or deck.get("source_pptx") or "",
        "total_slides": len(slides),
        "slides_fully_covered": slides_fully_covered,
        "slides_with_gaps": slides_with_gaps,
        "summary": {
            "total_uncovered_claims": sum(len(s["uncovered_claims"]) for s in slides_with_gaps),
            "total_claim_token_lint_signals": sum(len(s["claim_token_lint_signals"]) for s in slides_with_gaps),
            "slides_needing_source_gathering": len(slides_with_gaps),
        },
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps({
        "slides_fully_covered": len(slides_fully_covered),
        "slides_with_gaps": len(slides_with_gaps),
        "total_uncovered_claims": payload["summary"]["total_uncovered_claims"],
        "output": str(out),
    }, indent=2))

    return 1 if slides_with_gaps else 0


if __name__ == "__main__":
    sys.exit(main())
