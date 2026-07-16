"""In-flight decision scratch log (slice 083-07).

Captures the Tier-1 *structured* decision subset at decision time — recall-free —
instead of reconstructing it from end-of-session prose (083-04's scan). Two
in-flight hook points append one-line JSON stubs to a per-session scratch log:

- `PostToolUse(AskUserQuestion)` — the user's answer (source `askuserquestion`).
- `UserPromptSubmit` matching a Tier-2 override marker — a user default-override
  (source `user-override`), reusing `decision_scan.is_user_override` so in-flight
  and end-of-session capture agree on what counts.

At session end the Stop hook (`jig-decision-capture.sh`) reads the stubs, merges
them with the scan, and dedups so a decision captured *both* ways surfaces once.
It then prunes the stubs whose decision is now recorded and persists the rest, so
an un-recorded stub re-surfaces on the next Stop — durability parity with a scan
candidate. The scratch log is per-session, ephemeral, and git-ignored.

Composes with 083-04: the Tier-1 subset is already caught recall-free by the
scan; this is a *resilience* layer over that cell — it survives a Stop payload
that drops the AskUserQuestion tool blocks and persists before Stop so a decision
survives an abnormal session end. Python 3.9 compatible. Fail-open throughout.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

# Sibling-module import that works both as `lib.decision_scratch` (hook context,
# scripts dir on sys.path) and as top-level `decision_scratch` (unit test, lib
# dir on sys.path).
try:  # pragma: no cover - exercised by both import paths
    from decision_scan import (
        _DEDUP_CONTAINMENT,
        _DEDUP_MIN_TOKENS,
        Candidate,
        clip,
        is_machine_text,
        is_user_override,
        normalize_tokens,
    )
except ImportError:  # pragma: no cover
    from lib.decision_scan import (
        _DEDUP_CONTAINMENT,
        _DEDUP_MIN_TOKENS,
        Candidate,
        clip,
        is_machine_text,
        is_user_override,
        normalize_tokens,
    )

_SCRATCH_DIR = Path(".jig") / "decision-scratch"
_SOURCE_TIER = {"askuserquestion": 1, "user-override": 2}


def _sanitize_session(session_id) -> str:
    """A safe single-path-component filename stem for a session id."""
    sid = str(session_id or "default")
    safe = "".join(c if (c.isalnum() or c in "-_") else "-" for c in sid)
    return safe[:128] or "default"


def scratch_path(project_dir, session_id) -> Path:
    """Path to the per-session scratch log under `.jig/decision-scratch/`."""
    return Path(project_dir) / _SCRATCH_DIR / (_sanitize_session(session_id) + ".log")


def _now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def append_stub(project_dir, session_id, who, quote, source, turn=None) -> bool:
    """Append one decision stub to the session scratch log.

    Returns True when a stub was written, False when skipped (blank quote — i.e.
    ephemera produce no stub) or on any error (fail-open: capture must never
    break the session).
    """
    try:
        clipped = clip(quote)
        if not clipped:
            return False
        path = scratch_path(project_dir, session_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        stub = {
            "timestamp": _now_iso(),
            "who": who or "user",
            "quote": clipped,
            "source": source or "",
        }
        if turn is not None:
            stub["turn"] = turn
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(stub, sort_keys=True) + "\n")
        return True
    except Exception:
        return False


def read_stubs(project_dir, session_id) -> list:
    """Read the session's stubs as a list of dicts (tolerant; fail-open)."""
    try:
        path = scratch_path(project_dir, session_id)
        if not path.exists():
            return []
        stubs = []
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if isinstance(obj, dict) and obj.get("quote"):
                stubs.append(obj)
        return stubs
    except Exception:
        return []


def clear_scratch(project_dir, session_id) -> None:
    """Remove the session's scratch log entirely (fail-open)."""
    try:
        scratch_path(project_dir, session_id).unlink()
    except Exception:
        pass


def write_stubs(project_dir, session_id, stubs) -> None:
    """Rewrite the session's scratch log to exactly `stubs` (fail-open).

    Removes the file when `stubs` is empty so an emptied scratch leaves no
    residue. Used by the Stop-hook triage to prune recorded stubs while keeping
    un-recorded ones for re-surfacing.
    """
    try:
        if not stubs:
            clear_scratch(project_dir, session_id)
            return
        path = scratch_path(project_dir, session_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = [json.dumps(s, sort_keys=True) for s in stubs if isinstance(s, dict)]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except Exception:
        pass


def prune_recorded_stubs(stubs, recorded_texts) -> list:
    """Keep only stubs whose decision is NOT yet recorded.

    Mirrors `decision_scan.dedup`'s containment rule (and its terse-quote floor)
    on the raw stub dicts: a stub is dropped when >= `_DEDUP_CONTAINMENT` of its
    stopword-filtered tokens appear in some recorded decision. Un-recorded stubs
    survive so they re-surface on the next Stop — same durability as a scan
    candidate (a stub is not silently dropped after a single surfacing).
    """
    recorded_token_sets = [normalize_tokens(t) for t in (recorded_texts or [])]
    kept = []
    for stub in stubs or []:
        if not isinstance(stub, dict) or not stub.get("quote"):
            continue
        tokens = normalize_tokens(stub.get("quote"))
        if len(tokens) < _DEDUP_MIN_TOKENS:
            kept.append(stub)
            continue
        recorded = False
        for rec in recorded_token_sets:
            if rec and len(tokens & rec) / len(tokens) >= _DEDUP_CONTAINMENT:
                recorded = True
                break
        if not recorded:
            kept.append(stub)
    return kept


def stubs_to_candidates(stubs) -> list:
    """Map stub dicts to `decision_scan.Candidate`s (high confidence)."""
    candidates = []
    for stub in stubs or []:
        if not isinstance(stub, dict):
            continue
        quote = stub.get("quote")
        if not quote:
            continue
        source = stub.get("source") or ""
        tier = _SOURCE_TIER.get(source, 2)
        turn = stub.get("turn")
        candidates.append(Candidate(
            tier=tier,
            who=stub.get("who") or "user",
            quote=quote,
            turn=turn if isinstance(turn, int) else -1,
            confidence="high",
        ))
    return candidates


def dedup_scan_against_stubs(scan_candidates, stub_candidates) -> list:
    """Drop scan candidates already captured in-flight (no double-surface).

    A scan candidate is suppressed when >= `_DEDUP_CONTAINMENT` of its
    stopword-filtered tokens appear in some stub candidate's tokens — the same
    containment rule `decision_scan.dedup` uses against recorded decisions.
    """
    stub_token_sets = [normalize_tokens(c.quote) for c in (stub_candidates or [])]
    kept = []
    for cand in scan_candidates or []:
        cand_tokens = normalize_tokens(cand.quote)
        if len(cand_tokens) < _DEDUP_MIN_TOKENS:
            # Mirror decision_scan.dedup's terse-quote floor: too few tokens to
            # dedup confidently — keep (a re-surface is cheaper than a silent drop).
            kept.append(cand)
            continue
        suppressed = False
        for stub_tokens in stub_token_sets:
            if not stub_tokens:
                continue
            if len(cand_tokens & stub_tokens) / len(cand_tokens) >= _DEDUP_CONTAINMENT:
                suppressed = True
                break
        if not suppressed:
            kept.append(cand)
    return kept


def _collect_strings(obj, out, budget=40):
    """Collect string leaves from a nested dict/list payload (bounded)."""
    if len(out) >= budget:
        return
    if isinstance(obj, str):
        s = obj.strip()
        if s:
            out.append(s)
    elif isinstance(obj, dict):
        for value in obj.values():
            _collect_strings(value, out, budget)
    elif isinstance(obj, list):
        for item in obj:
            _collect_strings(item, out, budget)


def extract_askuserquestion_answer(tool_response) -> str:
    """The owner's answer from a PostToolUse(AskUserQuestion) payload, or "".

    Defensive across host payload shapes: collects string leaves from the tool
    response, which is where the selection lives. A response with no answer text
    means the dialog was dismissed, and that yields "" — so `append_stub`'s
    blank-quote guard drops it and nothing is recorded.

    This reads only the response *by construction* (slice 094-02). It previously
    also took the tool input and fell back to it, quoting the agent's own
    question when no answer came back, on the premise that "a noisy stub is
    cheap; a missed one is not". Issue #108 measured that premise: 17 of 27
    unique scratch entries were the agent's own dialog, and the reported one
    quoted a dialog the owner had explicitly dismissed. The asymmetry runs the
    other way — a fallback stub is not merely noisy but wrong about who spoke,
    it is durable (083-07 re-surfaces un-recorded stubs until something covering
    them is written), and it costs agent attention every Stop, which specs
    055/057 price as the dominant cost. Nor is a dismissed dialog a missed
    decision: dismissal is the owner declining to decide, so there is nothing
    to miss. Dropping the parameter keeps the fallback from being re-introduced
    by accident.
    """
    parts: list = []
    _collect_strings(tool_response, parts)
    return clip(" ".join(parts))


def is_override(text) -> bool:
    """True iff `text` is a user default-override (reuses the scan's markers)."""
    return is_user_override(text)


def is_machine(text) -> bool:
    """True iff `text` is harness output, not the owner (reuses the scan's rule).

    Same reason `is_override` delegates: one home for the markers, so in-flight
    capture and the Stop scan cannot drift apart on what counts (slice 094-01).
    """
    return is_machine_text(text)
