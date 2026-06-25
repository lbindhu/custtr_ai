#!/usr/bin/env python3
"""Single source of truth for layout, action, regex, and quality constants.

Every script that previously defined these locally now imports from here.
"""

import re

# ── Action types ──────────────────────────────────────────────────────

VALID_ACTION_TYPES = {
    "fragment_replace",
    "update_existing",
    "add_new_slide",
    "notes_update",
    "knowledge_check_update",
    "remove_or_deprecate",
}

MUTATING_ACTIONS = {
    "fragment_replace",
    "update_existing",
    "add_new_slide",
    "notes_update",
    "knowledge_check_update",
    "remove_or_deprecate",
}

# New slides are LLM-authored. The skill no longer constrains them to a
# fixed layout enum or routes them through script-specific renderers.

# ── Regex patterns ────────────────────────────────────────────────────

VERSION_RE = re.compile(r"\b20\d{2}\.\d\b")
SUMMARY_RE = re.compile(r"\b(summary|recap|key\s+takeaways|wrap[-\s]?up)\b", re.I)
KNOWLEDGE_RE = re.compile(r"\b(apply your knowledge|knowledge check|quiz|review question)\b", re.I)

# ── Quality-bar constants ─────────────────────────────────────────────

BANNED_OPENERS = (
    "on this slide",
    "on the previous slide",
    "this slide",
    "these slides",
    "to recap",
    "this is the knowledge check",
    "here we see",
    "here we have",
    "in this section",
)

DATASHEET_HEADINGS = {
    "what it is", "why it matters", "customer value",
    "what", "why", "value", "overview", "benefits",
}

DATASHEET_BULLET_RE = re.compile(
    r"^[A-Z][A-Za-z0-9 /()-]{2,40}:\s+[A-Z].*$"
)

# ── Exit codes ───────────────────────────────────────────────────────
EXIT_OK = 0
EXIT_ERROR = 1
EXIT_FATAL = 2
