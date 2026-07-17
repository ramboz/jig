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

# Harness-injected wrappers (slice 094-01). Text arriving inside these was not
# typed by the owner: the host generates it and delivers it through the same
# field a real prompt uses, so `who: "user"` has to be earned by the text rather
# than assumed from the event. Precision-first, like the tier markers above —
# only wrappers we can name, so prose the owner writes *about* them still counts
# as theirs.
_MACHINE_TAGS = (
    "task-notification",
    "command-name",
    "command-message",
    "command-args",
    "local-command-stdout",
    "local-command-stderr",
    "system-reminder",
)
# `(?![-\w])` rather than `\b`: `-` is a non-word character, so `\b` would let
# `<command-name-extra>` match a wrapper we never named.
_MACHINE_ANY_TAG = re.compile(
    r"<(/?)(%s)(?![-\w])[^>]*>" % "|".join(_MACHINE_TAGS), re.IGNORECASE)
# Tags with no matching partner — an orphan closer, or an opener whose content
# was never wrapped. Only the tag goes; anything around it is left standing,
# because we cannot tell an unpaired opener from the owner naming one in prose
# ("the <command-args> block should not be scanned"), and dropping their words
# is the failure #108 is about.
_MACHINE_TAG = re.compile(
    r"</?(%s)(?![-\w])[^>]*>" % "|".join(_MACHINE_TAGS), re.IGNORECASE)


def _machine_block_spans(text):
    """Half-open spans of the well-formed wrapper blocks in `text`.

    Depth-counted per tag name rather than matched to the *first* closer: a
    wrapper can contain its own tag name — the host quotes an edited file back
    inside a `<system-reminder>`, and files in this repo contain the literal tag
    — and pairing the opener with the first closer would leave the outer block's
    tail standing as if the owner had typed it.

    An opener that never balances is left for `_MACHINE_TAG`, which keeps the
    unpaired-tag policy above intact.
    """
    spans = []
    depth = {}
    start = {}
    for m in _MACHINE_ANY_TAG.finditer(text):
        name = m.group(2).lower()
        if not m.group(1):
            if not depth.get(name):
                start[name] = m.start()
            depth[name] = depth.get(name, 0) + 1
        elif depth.get(name):
            depth[name] -= 1
            if not depth[name]:
                spans.append((start[name], m.end()))
    return spans


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


def clip(text):
    """Public alias for the quote-clipping helper (reused by decision_scratch)."""
    return _clip(text)


def is_user_override(text):
    """True iff `text` carries a Tier-2 user override/correction marker.

    The in-flight UserPromptSubmit capture (slice 083-07) reuses the *same*
    Tier-2 markers the Stop scan uses, so in-flight and end-of-session capture
    agree on what counts as a user override (no pattern drift)."""
    return any(p.search(text or "") for p in _TIER2)


def strip_machine_text(text):
    """Return only what the owner plausibly typed, whitespace-normalized.

    The in-flight capture (slice 083-07) stamps `who: "user"` on everything
    arriving via `UserPromptSubmit`, but the host delivers its own notifications
    and command expansions through that same field — so issue #108 found
    `<task-notification>` blobs recorded as the owner's words. Attribution has to
    be earned by the text, and so does the quote: a caller both gates on this
    (empty means the payload was nothing but machinery, so there is no owner to
    attribute it to) and stores it (so an injection riding along with typed prose
    is not quoted back as theirs).

    Removing paired blocks before unpaired tags is what makes both halves work:
    a well-formed block is dropped whole, contents included, while a bare tag the
    owner mentioned in passing loses only the tag.

    The asymmetry is deliberate and unavoidable: a *paired* `<tag>…</tag>` the
    owner merely names in prose ("wrap it in <system-reminder> … </system-reminder>")
    is byte-for-byte indistinguishable from a real injection, so it is dropped
    like one — costing a few words of quote fidelity in that rare case. A
    heuristic to tell them apart would be the same evidence-free guard slice
    094-01 already deleted (`_MACHINE_UNCLOSED`), trading a real recall risk for
    a speculative one. A lone tag stays cheap to keep; a balanced pair does not.
    """
    if not text:
        return ""
    kept = []
    cursor = 0
    for begin, end in sorted(_machine_block_spans(text)):
        # Spans of different tag names can interleave; a span starting inside
        # one already dropped is part of it.
        if begin >= cursor:
            kept.append(text[cursor:begin])
        cursor = max(cursor, end)
    kept.append(text[cursor:])
    out = _MACHINE_TAG.sub(" ", " ".join(kept))
    return " ".join(out.split())


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
        "written; this is a triage prompt only.\n\n"
        # Names the command, not a path. This string is agent-facing in every
        # install mode, and a plugin-root env literal resolves in only one of
        # them — scaffold installs leave it unset, and the host packages use
        # different roots. Sibling hooks resolve modes at runtime via
        # SCRIPT_DIR for the same reason (see jig-decision-capture.sh); a
        # literal here would hand the agent an unusable path, which is the
        # defect this nudge exists to fix.
        "To record a lightweight decision, use /jig:memory-sync's "
        "`decisions.py add-lightweight` helper — it is idempotent, and it "
        "seeds the record home from jig's template if this project has none:\n"
        "    decisions.py add-lightweight --title \"<short title>\" "
        "--decision \"<what>\" \\\n"
        "      --context \"<why>\" --scope \"<where>\"\n\n"
        "Do NOT hand-write the file in your own format. Entries live under an "
        "`## Entries` heading, one block each:\n"
        "    ### <YYYY-MM-DD> — <short title>\n"
        "    **Decision:** ...  **Context:** ...  **Scope:** ...\n"
        % (len(candidates), body))
