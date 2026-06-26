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
from dataclasses import dataclass

# Common words dropped before dedup token-matching. Decision-bearing words
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

_DEDUP_CONTAINMENT = 0.6
# Candidates with fewer meaningful tokens than this are never deduped away — a
# 1-2 token quote trivially clears the containment threshold against any recorded
# entry sharing those tokens, which would over-suppress terse novel decisions.
_DEDUP_MIN_TOKENS = 3
_MAX_QUOTE = 240


@dataclass
class Candidate:
    tier: int
    who: str          # "user" | "agent"
    quote: str
    turn: int
    confidence: str   # "high" | "low"


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


def dedup(candidates, recorded_texts):
    """Drop candidates already covered by a recorded decision.

    Containment match: a candidate is suppressed when >= 60% of its
    stopword-filtered tokens appear in some recorded decision's tokens.
    """
    recorded_token_sets = [normalize_tokens(t) for t in (recorded_texts or [])]
    kept = []
    for cand in candidates:
        cand_tokens = normalize_tokens(cand.quote)
        if len(cand_tokens) < _DEDUP_MIN_TOKENS:
            # Too few tokens to dedup confidently — keep (favor a re-surface over
            # a silent drop; the owner-gate makes a duplicate cheap).
            kept.append(cand)
            continue
        suppressed = False
        for rec in recorded_token_sets:
            if not rec:
                continue
            containment = len(cand_tokens & rec) / len(cand_tokens)
            if containment >= _DEDUP_CONTAINMENT:
                suppressed = True
                break
        if not suppressed:
            kept.append(cand)
    return kept


def render_summary(candidates):
    """Owner-gated additionalContext text. Empty string when no candidates."""
    if not candidates:
        return ""
    lines = []
    for c in candidates:
        marker = "?" if c.confidence == "low" else "-"
        lines.append(
            "%s [tier %d, %s, %s] %s" % (marker, c.tier, c.who, c.confidence, c.quote))
    body = "\n".join(lines)
    return (
        "Decision-capture scan found %d candidate decision(s) this session:\n"
        "%s\n\n"
        "Please triage each: record durable ones in "
        "docs/decisions/lightweight-decisions.md (lightweight), write an ADR "
        "(load-bearing / rejected alternatives), park in refinement-todo.md "
        "(still open), or drop (ephemeral). Low-confidence (?) items are "
        "best-effort guesses — confirm before recording. Nothing has been "
        "written; this is a triage prompt only." % (len(candidates), body))
