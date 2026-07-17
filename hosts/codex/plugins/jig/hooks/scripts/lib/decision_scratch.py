"""In-flight decision scratch log (slice 083-07).

Captures the Tier-1 *structured* decision subset at decision time — recall-free —
instead of reconstructing it from end-of-session prose (083-04's scan). Two
in-flight hook points append one-line JSON stubs to a per-session scratch log:

- `PostToolUse(AskUserQuestion)` — the user's answer (source `askuserquestion`).
- `UserPromptSubmit` matching a Tier-2 override marker — a user default-override
  (source `user-override`), reusing `decision_scan.is_user_override` so in-flight
  and end-of-session capture agree on what counts.

At session end the Stop hook (`jig-decision-capture.sh`) reads the stubs, merges
them with the scan, and collapses a decision captured *both* ways into one line.
Stubs whose decision looks already recorded are *flagged*, never pruned (bug 011
/ issue #109 — overlap cannot distinguish a reversal from a restatement, so the
owner triages), and every stub persists and re-surfaces on the next Stop —
durability parity with a scan candidate. The scratch log is per-session and
git-ignored; since nothing is pruned it is rewritten rather than emptied, so a
populated log outlives its session on disk.

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
        Candidate,
        clip,
        is_contained,
        is_user_override,
        normalize_tokens,
        strip_machine_text,
        token_sets,
    )
except ImportError:  # pragma: no cover
    from lib.decision_scan import (
        Candidate,
        clip,
        is_contained,
        is_user_override,
        normalize_tokens,
        strip_machine_text,
        token_sets,
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
    residue. The Stop-hook triage writes back the full flagged list, so in
    practice a populated scratch is rewritten, never emptied (bug 011).
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


def flag_recorded_stubs(stubs, recorded_texts) -> list:
    """Flag stubs overlapping a recorded decision. Never drops one.

    Same rule and same reason as `decision_scan.flag_duplicates`: overlap cannot
    tell a restatement from a reversal, so the owner triages (bug 011). Stubs
    with no usable quote are skipped — `read_stubs` already filters those.
    """
    recorded = token_sets(recorded_texts)
    flagged = []
    for stub in stubs or []:
        if not isinstance(stub, dict) or not stub.get("quote"):
            continue
        flagged.append(dict(stub,
                            possible_duplicate=is_contained(stub["quote"], recorded)))
    return flagged


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
            possible_duplicate=bool(stub.get("possible_duplicate")),
        ))
    return candidates


def dedup_scan_against_stubs(scan_candidates, stub_candidates) -> list:
    """Drop scan candidates already captured in-flight (no double-surface).

    Deliberately still a *drop*, unlike the recorded-corpus paths: this collapses
    one decision captured both ways into a single line — duplication with no
    triage value, not suppression of a distinct decision. The covering stub is
    surfaced in the same nudge, so the decision still reaches the owner.

    Residual (bug 011, accepted): a Tier-3 *agent* restatement that in fact
    reverses a stub is dropped here, since agent prose never produces a stub of
    its own to survive as. Low value — Tier 3 is low-confidence by construction.
    """
    stubs = token_sets(c.quote for c in (stub_candidates or []))
    return [c for c in (scan_candidates or [])
            if not is_contained(c.quote, stubs)]


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
    response, which is where the selection lives. Returning "" is a contract,
    not an accident — it is how a dismissed dialog reaches `append_stub`'s
    blank-quote guard and records nothing.

    Takes the response and *not* the tool input on purpose: the input holds the
    agent's own question, which is not the owner's words even when no answer
    comes back. An earlier cut fell back to it and #108 measured the result, so
    the parameter is gone rather than merely unused — see slice 094-02 for the
    reasoning. Do not re-add it for robustness.
    """
    parts: list = []
    _collect_strings(tool_response, parts)
    return clip(" ".join(parts))


def is_override(text) -> bool:
    """True iff `text` is a user default-override (reuses the scan's markers)."""
    return is_user_override(text)


def typed_by_owner(text) -> str:
    """The part of `text` the owner typed, harness injections removed.

    Same reason `is_override` delegates: one home for the markers, so in-flight
    capture and the Stop scan cannot drift apart on what counts (slice 094-01).
    Empty means nothing was typed — so there is nobody to attribute it to.
    """
    return strip_machine_text(text)
