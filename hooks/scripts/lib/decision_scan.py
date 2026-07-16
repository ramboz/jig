"""Session decision scan (slice 083-04).

Pure-function scan over a Stop-hook `messages` payload, surfacing *candidate*
decisions for owner-gated triage. The scan is honest about its reach:

- Tier 1 — AskUserQuestion answers (structured)        -> high confidence
- Tier 2 — explicit user corrections / overrides       -> high confidence
- Tier 3 — agent statements of settled choices         -> low (best-effort)

It deliberately does NOT try to catch trigger-phrase-free *load-bearing*
decisions — a precision-first lexical scan is structurally biased to miss them
(see docs/specs/083-.../reviews/slice-04-frame-critique.md). Those are owned by
083-06's reconciliation / memory-sync judgment prompt, not this scan.

Provenance is preserved per message (who decided + quote + turn) — unlike
jig-task-capture.sh, which flattens all content into one string and so cannot
attribute. The hook (jig-decision-capture.sh) calls `scan()` over the payload
and surfaces `render_summary()` as additionalContext; it never writes.

Python 3.9 compatible.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace

# Common words dropped before containment token-matching. Decision-bearing words
# ("not", "default", "instead") are deliberately NOT stopwords.
STOPWORDS = frozenset({
    "a", "an", "the", "be", "is", "are", "was", "were", "to", "of", "on", "in",
    "for", "and", "or", "but", "so", "we", "i", "it", "this", "that", "with",
    "as", "at", "by", "our", "us", "you", "your",
})

# Tier 2 — user corrections / overrides. Precision-first: strong markers only.
# `actually` is a high-signal correction opener and Tier 2 is user-role-only, so
# its false-positive surface is small (and the owner-gate catches the rest).
_TIER2 = [
    re.compile(r"\bshould\s+not\b", re.IGNORECASE),
    re.compile(r"\binstead\b", re.IGNORECASE),
    re.compile(r"\bactually\b", re.IGNORECASE),
    re.compile(r"\boverride\b.*\bdefault\b", re.IGNORECASE),
    re.compile(r"\breverse\b.*\bdefault\b", re.IGNORECASE),
]

# Tier 3 — agent settled choices. Best-effort, low confidence.
_TIER3 = [
    re.compile(r"\bchose\b.*\bover\b", re.IGNORECASE),
    re.compile(r"\brejected\b.*\bbecause\b", re.IGNORECASE),
    re.compile(r"\bgoing with\b", re.IGNORECASE),
    re.compile(r"\bdecided\s+(?:to|on|against)\b", re.IGNORECASE),
]

_DUPLICATE_CONTAINMENT = 0.6
# Candidates with fewer meaningful tokens than this are never flagged — a 1-2
# token quote trivially clears the containment threshold against any recorded
# entry sharing those tokens, so the hint would be noise rather than signal.
_DUPLICATE_MIN_TOKENS = 3
_MAX_QUOTE = 240


@dataclass
class Candidate:
    tier: int
    who: str          # "user" | "agent"
    quote: str
    turn: int
    confidence: str   # "high" | "low"
    possible_duplicate: bool = False   # overlaps a recorded decision — owner triages


def normalize_tokens(text):
    """Lowercase alphanumeric word tokens with stopwords removed."""
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    return {w for w in words if w not in STOPWORDS}


def _extract_text(content):
    """Return only human-prose text from a message's content.

    Plain strings pass through; for a content-block list, only `text` blocks are
    joined — tool_use / tool_result blocks are handled separately (Tier 1) and
    must not be scanned as user/agent prose.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return " ".join(parts)
    return ""


def _result_text(content):
    """Flatten an AskUserQuestion tool_result's content to a string answer."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                parts.append(block.get("text") or block.get("content") or "")
            elif isinstance(block, str):
                parts.append(block)
        return " ".join(p for p in parts if p)
    return ""


def _clip(text):
    text = " ".join((text or "").split())
    return text if len(text) <= _MAX_QUOTE else text[: _MAX_QUOTE - 1] + "…"


def clip(text):
    """Public alias for the quote-clipping helper (reused by decision_scratch)."""
    return _clip(text)


def is_user_override(text):
    """True iff `text` carries a Tier-2 user override/correction marker.

    The in-flight UserPromptSubmit capture (slice 083-07) reuses the *same*
    Tier-2 markers the Stop scan uses, so in-flight and end-of-session capture
    agree on what counts as a user override (no pattern drift)."""
    return any(p.search(text or "") for p in _TIER2)


def _scan_askuserquestion(messages):
    """Tier 1: pair each AskUserQuestion tool_use with its tool_result answer."""
    asked = {}  # tool_use_id -> turn it was asked
    for turn, msg in enumerate(messages):
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use" and block.get("name") == "AskUserQuestion":
                tid = block.get("id")
                if tid:
                    asked[tid] = turn
            elif block.get("type") == "tool_result":
                tid = block.get("tool_use_id")
                if tid in asked:
                    answer = _result_text(block.get("content"))
                    if answer.strip():
                        yield Candidate(
                            tier=1, who="user", quote=_clip(answer),
                            turn=turn, confidence="high")


def scan(messages):
    """Scan a Stop-hook `messages` payload -> list[Candidate], in turn order."""
    if not isinstance(messages, list):
        return []
    candidates = []
    candidates.extend(_scan_askuserquestion(messages))
    for turn, msg in enumerate(messages):
        if not isinstance(msg, dict):
            continue
        role = msg.get("role")
        prose = _extract_text(msg.get("content"))
        if not prose.strip():
            continue
        if role == "user":
            if any(p.search(prose) for p in _TIER2):
                candidates.append(Candidate(
                    tier=2, who="user", quote=_clip(prose),
                    turn=turn, confidence="high"))
        elif role == "assistant":
            if any(p.search(prose) for p in _TIER3):
                candidates.append(Candidate(
                    tier=3, who="agent", quote=_clip(prose),
                    turn=turn, confidence="low"))
    candidates.sort(key=lambda c: (c.turn, c.tier))
    return candidates


def token_sets(texts):
    """Stopword-filtered token sets for `texts`, dropping any that come out empty."""
    return [t for t in (normalize_tokens(x) for x in (texts or [])) if t]


def is_contained(quote, others):
    """True iff >= `_DUPLICATE_CONTAINMENT` of `quote`'s tokens appear in some set.

    Below `_DUPLICATE_MIN_TOKENS` the answer is always False: a 1-2 token quote
    clears any threshold against a set that happens to share those tokens.

    Sole home of the containment rule: every caller — this module against recorded
    decisions, `decision_scratch` against recorded decisions and against in-flight
    stubs — comes through here, so the sites cannot drift apart.
    """
    tokens = normalize_tokens(quote)
    if len(tokens) < _DUPLICATE_MIN_TOKENS:
        return False
    return any(len(tokens & other) / len(tokens) >= _DUPLICATE_CONTAINMENT
               for other in others)


def flag_duplicates(candidates, recorded_texts):
    """Flag candidates overlapping a recorded decision. Never drops one.

    Overlap cannot distinguish a restatement from a reversal — a decision that
    overturns a recorded one shares its vocabulary — so the flag is a hint for
    the owner, never a verdict. Dropping on it silently loses reversals
    (bug 011).
    """
    recorded = token_sets(recorded_texts)
    return [replace(c, possible_duplicate=is_contained(c.quote, recorded))
            for c in candidates]


def render_summary(candidates):
    """Owner-gated additionalContext text. Empty string when no candidates."""
    if not candidates:
        return ""
    lines = []
    any_flagged = False
    for c in candidates:
        marker = "?" if c.confidence == "low" else "-"
        tags = "tier %d, %s, %s" % (c.tier, c.who, c.confidence)
        if c.possible_duplicate:
            tags += ", possible duplicate"
            any_flagged = True
        lines.append("%s [%s] %s" % (marker, tags, c.quote))
    body = "\n".join(lines)
    duplicate_note = (
        " `possible duplicate` = overlaps a recorded decision; overlap cannot "
        "tell a repeat from a reversal, so check each."
        if any_flagged else "")
    return (
        "Decision-capture scan found %d candidate decision(s) this session:\n"
        "%s\n\n"
        "Please triage each: record durable ones in "
        "docs/decisions/lightweight-decisions.md (lightweight), write an ADR "
        "(load-bearing / rejected alternatives), park in refinement-todo.md "
        "(still open), or drop (ephemeral). Low-confidence (?) items are "
        "best-effort guesses — confirm before recording.%s Nothing has been "
        "written; this is a triage prompt only."
        % (len(candidates), body, duplicate_note))
