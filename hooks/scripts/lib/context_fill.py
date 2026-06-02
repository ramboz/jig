"""Context-fill estimator for jig's SessionStart soft-warn hook.

Spec 026 (slice 026-01): factor out a byte/token estimator that

  - measures the always-loaded primer footprint (CLAUDE.md +
    docs/memory/*.md);
  - returns a stable dict shape so servo (spec 003 hard-gate) can
    subprocess-invoke this module without re-implementing the math;
  - stays pure (no printing, no env-touching side effects) — the
    hook script does the I/O.

Bytes → tokens conversion
-------------------------

``est_tokens = bytes // RATIO`` with ``RATIO = 4``. Four bytes per token
is the well-worn English-prose heuristic (OpenAI tokenizer docs, Andrej
Karpathy's tokenizer notebooks) — close enough for a soft warning where
the absolute number matters less than the order of magnitude. The hook
surfaces the ratio in its warning so the user can mentally calibrate.

Default window size
-------------------

``DEFAULT_WINDOW_BYTES = 800_000`` — sized for Opus 4.7's nominal
~200K-token context window (200_000 × 4 = 800_000 bytes). Override via
``JIG_CONTEXT_WINDOW_BYTES`` (int) when running against a different
model. Future spec 026 slices may wire in model-name detection; the env
var stays as the manual override.

Default threshold
-----------------

``DEFAULT_THRESHOLD = 0.30`` — 30% of the window. Pre-dumb-zone: the
CLAUDE.md hot cache cites Horthy's 40% degradation knee, so a 30%
warning gives the user time to act (run ``/jig:memory-sync`` and
``/compact``) before recall actually starts slipping. Override via
``JIG_CONTEXT_SOFT_WARN_PCT`` — **set as a fraction (e.g. 0.30), not
a percent (30)**. The var name says PCT but the value is a fraction
in (0, 1]; out-of-range or non-numeric values silently fall back to
the default so a typo never crashes the hook.

Public surface
--------------

``estimate(project_root: Path) -> dict`` returns::

    {
        "bytes":        int,    # sum of contributing-file sizes
        "est_tokens":   int,    # bytes // RATIO
        "ratio":        float,  # bytes / window_bytes
        "threshold":    float,  # the configured soft-warn threshold
        "breakdown":    dict,   # {relative_path: bytes} per contribution
        "window_bytes": int,    # effective window size used for ratio
    }

The caller decides what to do with the result — typically
``ratio >= threshold`` → emit a warning.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict


RATIO = 4
"""Bytes per token (rough English-prose heuristic)."""

DEFAULT_WINDOW_BYTES = 200_000 * RATIO  # = 800_000
"""Opus 4.7-sized default context window in bytes (~200K tokens)."""

DEFAULT_THRESHOLD = 0.30
"""Soft-warn at 30% of the window — pre-dumb-zone (40% per Horthy)."""

DEFAULT_GROWTH_THRESHOLD = 0.40
"""In-session growth nudge fires at 40% of the window — the dumb-zone line
itself (Horthy's 40% recall-degradation knee), slice 055-02. This is the
*first* band; higher bands escalate (see ``GROWTH_BANDS``). Override via
``JIG_CONTEXT_GROWTH_WARN_PCT`` (a fraction in (0, 1], same out-of-range
fallback as ``JIG_CONTEXT_SOFT_WARN_PCT``). The first band tracks the
configured threshold; the 0.60 / 0.80 escalation bands are fixed offsets."""

GROWTH_BANDS = (DEFAULT_GROWTH_THRESHOLD, 0.60, 0.80)
"""Escalation bands for the in-session growth nudge (slice 055-02, spec
Decisions §3). The nudge fires at most once per band per session, re-arming
when the estimate drops back below a band. The first band is replaced by the
configured ``JIG_CONTEXT_GROWTH_WARN_PCT`` at evaluation time; 0.60 / 0.80 are
fixed. All are fractions of the configurable token-window, never hardcoded
token counts."""


def _resolve_window_bytes() -> int:
    """Read ``JIG_CONTEXT_WINDOW_BYTES`` from env, falling back to the
    Opus 4.7 default. Malformed values silently fall back so a typo in
    the env doesn't crash the hook."""
    raw = os.environ.get("JIG_CONTEXT_WINDOW_BYTES")
    if raw is None:
        return DEFAULT_WINDOW_BYTES
    try:
        value = int(raw)
        if value <= 0:
            return DEFAULT_WINDOW_BYTES
        return value
    except ValueError:
        return DEFAULT_WINDOW_BYTES


def _resolve_threshold() -> float:
    """Read ``JIG_CONTEXT_SOFT_WARN_PCT`` from env, falling back to 0.30."""
    raw = os.environ.get("JIG_CONTEXT_SOFT_WARN_PCT")
    if raw is None:
        return DEFAULT_THRESHOLD
    try:
        value = float(raw)
        if value <= 0 or value > 1:
            return DEFAULT_THRESHOLD
        return value
    except ValueError:
        return DEFAULT_THRESHOLD


def _resolve_growth_threshold() -> float:
    """Read ``JIG_CONTEXT_GROWTH_WARN_PCT`` from env, falling back to 0.40.

    Mirrors ``_resolve_threshold`` exactly: the value is a fraction in
    (0, 1]; out-of-range or non-numeric values silently fall back to the
    default so a typo never crashes the hook (slice 055-02)."""
    raw = os.environ.get("JIG_CONTEXT_GROWTH_WARN_PCT")
    if raw is None:
        return DEFAULT_GROWTH_THRESHOLD
    try:
        value = float(raw)
        if value <= 0 or value > 1:
            return DEFAULT_GROWTH_THRESHOLD
        return value
    except ValueError:
        return DEFAULT_GROWTH_THRESHOLD


def token_window() -> int:
    """The context window expressed in tokens: ``JIG_CONTEXT_WINDOW_BYTES``
    (resolved, with fallback) divided by ``RATIO``.

    The in-session growth nudge compares ``cache_read_input_tokens`` (a token
    count) against fractions of this token-window, so the bands stay
    fractions of the *configurable* window rather than hardcoded token
    counts (slice 055-02 AC #3)."""
    return _resolve_window_bytes() // RATIO


def _measure(path: Path) -> int:
    """File size in bytes, or 0 if the file does not exist."""
    try:
        return path.stat().st_size
    except (OSError, FileNotFoundError):
        return 0


def estimate(project_root: Path) -> Dict[str, object]:
    """Estimate the always-loaded context footprint under ``project_root``.

    See module docstring for the dict shape and the threshold / window
    semantics.

    The function is pure: it reads files via ``Path.stat()`` and never
    prints, mutates the environment, or raises on missing inputs. A
    missing ``CLAUDE.md`` or absent ``docs/memory/`` simply contributes
    zero bytes to the total — the hook surface stays unconditional.
    """
    project_root = Path(project_root)
    breakdown: Dict[str, int] = {}

    primer = project_root / "CLAUDE.md"
    primer_bytes = _measure(primer)
    if primer_bytes > 0:
        breakdown["CLAUDE.md"] = primer_bytes

    memory_dir = project_root / "docs" / "memory"
    if memory_dir.is_dir():
        # Sort for deterministic breakdown ordering — tests assert on
        # specific keys, not on order, but stability is friendlier to
        # downstream consumers (servo, logs).
        for md_file in sorted(memory_dir.glob("*.md")):
            size = _measure(md_file)
            if size > 0:
                rel = md_file.relative_to(project_root).as_posix()
                breakdown[rel] = size

    total_bytes = sum(breakdown.values())
    window_bytes = _resolve_window_bytes()
    threshold = _resolve_threshold()
    ratio = total_bytes / window_bytes if window_bytes > 0 else 0.0

    return {
        "bytes": total_bytes,
        "est_tokens": total_bytes // RATIO,
        "ratio": ratio,
        "threshold": threshold,
        "breakdown": breakdown,
        "window_bytes": window_bytes,
    }


# --------------------------------------------------------------------------
# In-session growth nudge (slice 055-02)
#
# Two pure helpers the hook delegates to:
#   - read_tail_cache_read_tokens(): the cheap transcript-tail read (AC #2).
#   - evaluate_growth(): the band / re-arm decision (AC #3 / #4), keeping the
#     policy out of brittle shell. The hook owns only the state-file I/O.
# --------------------------------------------------------------------------

# Read at most this many bytes from the transcript tail. A single assistant
# record (with tool calls + usage) is a few KB; 256 KB comfortably covers the
# last several records without ever scanning a multi-MB transcript (AC #2).
_TAIL_READ_BYTES = 256 * 1024


def read_tail_cache_read_tokens(transcript_path) -> "int | None":
    """Return the last assistant record's ``cache_read_input_tokens`` from a
    JSONL transcript, read **cheaply from the tail** (never a full scan).

    Returns ``None`` — never raises — when the path is falsy, missing,
    empty, malformed, or contains no parseable assistant record with a usage
    block. The caller treats ``None`` as "no signal → stay silent" (AC #5).

    Strategy: seek to the end, read the final ``_TAIL_READ_BYTES`` window,
    split into lines, and walk **backwards** parsing each as JSON. The first
    line that parses as an ``assistant`` record carrying
    ``message.usage.cache_read_input_tokens`` wins. Unparseable / non-matching
    lines are skipped, so a corrupt final line never masks an earlier valid
    record reachable from the tail.
    """
    if not transcript_path:
        return None
    try:
        path = Path(transcript_path)
        size = path.stat().st_size
        if size <= 0:
            return None
        with path.open("rb") as fh:
            if size > _TAIL_READ_BYTES:
                fh.seek(-_TAIL_READ_BYTES, os.SEEK_END)
                # Drop the (likely partial) first line of the window.
                chunk = fh.read()
                first_nl = chunk.find(b"\n")
                if first_nl != -1:
                    chunk = chunk[first_nl + 1:]
            else:
                chunk = fh.read()
        text = chunk.decode("utf-8", errors="replace")
    except Exception:
        return None

    for line in reversed(text.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if not isinstance(obj, dict) or obj.get("type") != "assistant":
            continue
        usage = (obj.get("message") or {}).get("usage")
        if not isinstance(usage, dict):
            continue
        value = usage.get("cache_read_input_tokens")
        if isinstance(value, bool):  # bool is an int subclass — reject
            continue
        if isinstance(value, int):
            return value
    return None


def _growth_bands() -> "tuple[float, ...]":
    """The active escalation bands: ``GROWTH_BANDS`` with the first band
    replaced by the configured ``JIG_CONTEXT_GROWTH_WARN_PCT``. Returns a
    sorted, de-duplicated tuple so a configured threshold that coincides with
    or exceeds a fixed band doesn't double-fire."""
    first = _resolve_growth_threshold()
    bands = {first} | {b for b in GROWTH_BANDS[1:] if b > first}
    return tuple(sorted(bands))


def evaluate_growth(cache_read_tokens, warned_bands) -> "dict":
    """Decide whether the in-session growth nudge should fire this turn.

    Pure: no I/O, no env mutation. The hook reads the per-session state file
    (the list of already-warned bands), calls this, then writes back the
    returned ``warned_bands``.

    Parameters
    ----------
    cache_read_tokens:
        The current context-size proxy (last assistant
        ``cache_read_input_tokens``), or ``None`` when there is no assistant
        turn yet.
    warned_bands:
        The list of band fractions already warned this session (the prior
        state). Order-insensitive.

    Returns a dict::

        {
            "nudge":        bool,            # fire a nudge this turn?
            "band":         float | None,    # highest newly-crossed band
            "ratio":        float,           # tokens / token_window
            "warned_bands": list[float],     # next state to persist
        }

    Semantics (AC #4):
      - A band is "crossed" when ``ratio >= band``.
      - Bands the estimate has dropped **below** are cleared from the
        warned set → **re-armed** (e.g. after ``/compact``).
      - Among currently-crossed bands, any not already warned are *newly*
        crossed → nudge once (reporting the highest), and all crossed bands
        are recorded so re-crossing stays silent.
    """
    window = token_window()
    bands = _growth_bands()

    if cache_read_tokens is None or window <= 0:
        # No signal → silent, state unchanged.
        return {
            "nudge": False,
            "band": None,
            "ratio": 0.0,
            "warned_bands": sorted(set(warned_bands or [])),
        }

    ratio = cache_read_tokens / window

    crossed = [b for b in bands if ratio >= b]
    prior = set(warned_bands or [])

    # Re-arm: keep only previously-warned bands the estimate is still at/above.
    retained = {b for b in prior if any(abs(b - c) < 1e-9 for c in crossed)}

    # Newly crossed = crossed bands not already retained from the prior set.
    newly = [b for b in crossed
             if not any(abs(b - r) < 1e-9 for r in retained)]

    next_warned = sorted(retained | set(crossed))

    if newly:
        return {
            "nudge": True,
            "band": max(newly),
            "ratio": ratio,
            "warned_bands": next_warned,
        }
    return {
        "nudge": False,
        "band": None,
        "ratio": ratio,
        "warned_bands": next_warned,
    }


def growth_nudge_text(band: float, ratio: float) -> str:
    """The soft `additionalContext` nudge body (slice 055-02 AC #1 / AC #6).

    References the ``docs/workflow.md`` "Context-cost discipline" section
    (landed by 055-01) and recommends `/compact` or delegating the next
    read-heavy step to an isolated subagent."""
    band_pct = band * 100
    actual_pct = ratio * 100
    return (
        f"Context-growth nudge: the orchestrator's context is ~{actual_pct:.0f}% "
        f"of the window (past the {band_pct:.0f}% mark — the 'dumb zone' line "
        "where recall starts to degrade). The orchestrator is re-read every "
        "turn, so this cost compounds. Consider running /compact now, or "
        "delegating the next read-heavy step (file reads, searches, analysis) "
        "to an isolated Explore / general-purpose subagent so the bulk never "
        "enters the main session. See the \"Context-cost discipline\" section "
        "of docs/workflow.md."
    )


def _state_file(state_dir, session_id: str) -> Path:
    """Per-session state-file path, keyed by session id, under ``state_dir``
    (typically ``$TMPDIR``). A non-filesystem-safe session id is reduced to
    its safe characters so the path stays valid."""
    safe = "".join(c if (c.isalnum() or c in "-_.") else "_"
                   for c in (session_id or "default"))
    if not safe:
        safe = "default"
    return Path(state_dir) / f"jig-context-growth-{safe}.json"


def _read_warned_bands(state_path: Path) -> "list[float]":
    """Load the warned-band list from the per-session state file. Returns an
    empty list on any error (missing / malformed) — never raises."""
    try:
        data = json.loads(state_path.read_text())
        bands = data.get("warned_bands")
        if isinstance(bands, list):
            return [float(b) for b in bands
                    if isinstance(b, (int, float)) and not isinstance(b, bool)]
    except Exception:
        pass
    return []


def _write_warned_bands(state_path: Path, warned_bands) -> None:
    """Persist the warned-band list. Best-effort — swallows I/O errors so the
    hook never blocks on a read-only / missing TMPDIR."""
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps({"warned_bands": list(warned_bands)}))
    except Exception:
        pass


def growth_nudge_for_turn(transcript_path, session_id, state_dir) -> "str | None":
    """Top-level orchestration for the UserPromptSubmit growth nudge.

    Reads the transcript tail → loads the per-session warned-band state →
    evaluates → persists the new state → returns the nudge text, or ``None``
    when nothing should fire. Never raises (AC #5): any failure path returns
    ``None`` so the hook stays silent and non-blocking.

    Deferred-by-design (055-02 reconciliation): the per-session state file is
    left to the OS tmp-reaper rather than self-cleaned (tiny JSON, unique
    session ids → no correctness issue); the state read-modify-write is
    unguarded — safe because ``UserPromptSubmit`` turns are serial within a
    session.
    """
    try:
        tokens = read_tail_cache_read_tokens(transcript_path)
        state_path = _state_file(state_dir, session_id)
        prior = _read_warned_bands(state_path)
        decision = evaluate_growth(tokens, prior)
        # Persist the next state whenever it changed — this is what makes the
        # band re-arm on drop (Clarification Q3): a sub-band estimate clears
        # the higher warned bands so a later climb nudges again.
        if decision["warned_bands"] != sorted(set(prior)):
            _write_warned_bands(state_path, decision["warned_bands"])
        if decision["nudge"] and decision["band"] is not None:
            return growth_nudge_text(decision["band"], decision["ratio"])
        return None
    except Exception:
        return None
