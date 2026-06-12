"""Fail-open read-nudge attribution logging for jig-context-check.sh."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import re
from pathlib import Path

READ_ATTRIBUTION_LOG = "context-growth-read-events.jsonl"

_SPEC_RE = re.compile(r"(?m)^\s*spec\s*=\s*(\d{1,3})\s*$")
_SLICE_RE = re.compile(r"(?m)^\s*slice\s*=\s*(\d{1,3})-(\d{1,2})\s*$")


def read_spec_ref(project_dir) -> "tuple[str, str]":
    """Return ``(spec, slice)`` from ``<project_dir>/.jig/spec-ref``.

    The hook deliberately uses only this exact marker for attribution. Missing,
    unreadable, or malformed markers leave both fields empty; no heuristic is
    allowed in the hook path.
    """
    try:
        text = (Path(project_dir) / ".jig" / "spec-ref").read_text(
            encoding="utf-8", errors="replace")
    except Exception:
        return "", ""
    spec_match = _SPEC_RE.search(text)
    slice_match = _SLICE_RE.search(text)
    if not spec_match or not slice_match:
        return "", ""
    spec = f"{int(spec_match.group(1)):03d}"
    slice_id = f"{int(slice_match.group(1)):03d}-{int(slice_match.group(2)):02d}"
    return spec, slice_id


def append_read_nudge_event(project_dir, session_id, decision) -> None:
    """Append one bounded JSONL event for a read nudge.

    Best effort by design: all errors are swallowed so telemetry can never
    block or suppress the user-facing nudge.
    """
    try:
        project = Path(project_dir)
        spec, slice_id = read_spec_ref(project)
        event = {
            "timestamp": datetime.now(timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z"),
            "session_id": session_id or "default",
            "event": "read_nudge",
            "kind": decision.get("kind") or "",
            "file_path": decision.get("file_path") or "",
            "threshold_bytes": int(decision.get("threshold_bytes") or 0),
            "ranged": bool(decision.get("ranged")),
            "spec": spec,
            "slice": slice_id,
            "source_hook": "jig-context-check",
        }
        size = decision.get("size_bytes")
        if isinstance(size, bool):
            size = None
        if isinstance(size, (int, float)) and size >= 0:
            event["size_bytes"] = int(size)

        log_dir = project / ".claude"
        log_dir.mkdir(parents=True, exist_ok=True)
        with (log_dir / READ_ATTRIBUTION_LOG).open(
            "a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, sort_keys=True) + "\n")
    except Exception:
        pass
