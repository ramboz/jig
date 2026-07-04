"""Gate-bypass telemetry (spec 078 / ADR-0011).

jig's gates are deliberateness signals with an env-var escape hatch, not
human-only enforcement (ADR-0011) — but the escapes were previously
un-instrumented: a bypassed gate left no trace. This module gives each gate
a one-line, content-free way to record that its override fired, so a
maintainer can audit *how often* a gate is bypassed without the gate
becoming any harder to bypass (078's non-goal).

Events append to `.claude/skill-usage.jsonl`, the same sink spec 041 writes
`skill_invoked` / `task_spawned` rows to (already gitignored). `gate-stats`
(078-02, `workflow.py`) reads them back filtered on
``event == "gate_bypassed"``, mirroring `routing_stats`'s `skill_invoked`
filter — one shared file, readers agree to filter by `event`.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def emit_gate_bypass(project_dir, gate: str, env_var: str,
                      spec_ref: str = "") -> None:
    """Append one ``gate_bypassed`` event to
    ``<project_dir>/.claude/skill-usage.jsonl``.

    Content-free by design (078 non-goal): only the gate name, the env var
    that bypassed it, a timestamp, and a best-effort spec ref — never the
    diff, secret, or prompt content the gate was protecting.

    Fail-open: any failure (unwritable dir, bad `project_dir`, ...) is
    swallowed silently. The gate already decided to allow the operation;
    a telemetry hiccup must never turn that into a block.
    """
    try:
        log_dir = Path(project_dir) / ".claude"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "skill-usage.jsonl"
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "gate_bypassed",
            "gate": gate,
            "env_var": env_var,
        }
        if spec_ref:
            entry["spec_ref"] = spec_ref
        with open(log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


def read_spec_ref(project_dir) -> str:
    """Best-effort read of the ``spec=`` line in
    ``<project_dir>/.jig/spec-ref`` (the slice 056-03 attribution marker).

    Returns ``""`` on any miss (file absent, unreadable, no ``spec=``
    line) — attribution is best-effort and must never block the emit.
    """
    try:
        marker = Path(project_dir) / ".jig" / "spec-ref"
        if not marker.is_file():
            return ""
        for line in marker.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line.startswith("spec="):
                return line[len("spec="):].strip()
    except Exception:
        pass
    return ""
