"""Shared team-signal detection — the single home for spec 050's
"has this project grown past solo?" logic.

Extracted per ADR-0002's rule-of-three (slice 050-02): the team-context
detection acquired its third caller — `workflow.py stale` — alongside
`scaffold-init` (the original owner) and `memory-sync`'s team-check. Rather
than a third cross-skill import of `scaffold.py`, the logic moves here so
there is one source of truth for:

  - `count_team_contributors(target) -> int` — distinct mailmap-normalized
    git author emails, fail-soft to 0, monorepo-parent-guarded.
  - `TEAM_THRESHOLD` / `team_signal_fires(target) -> bool` — the >= 2
    threshold, in exactly one place.
  - the `.jig/no-people-md` opt-out marker contract
    (`NO_PEOPLE_MD_RELPATH`, `no_people_md_marker_path`,
    `write_no_people_md_marker`).
  - `people_md_path(target) -> Path`.
  - `team_context_drift(target) -> int | None` — the composite "should we
    surface/nudge?" decision shared by memory team-check and stale: the
    contributor count N when (signal fires AND `docs/memory/people.md`
    absent AND `.jig/no-people-md` absent), else None.

`scaffold.py` and `memory.py` re-export / import from here so their existing
public names keep working; `workflow.py stale` imports `team_context_drift`
directly.
"""

import subprocess
from pathlib import Path

from _common.atomic_io import atomic_write_text

# The team signal fires at >= 2 distinct contributors. Lives here only; both
# `team_signal_fires` and (via re-export) scaffold-init's `detect_team`
# read it, so the threshold can never drift between callers (spec 050
# Implementation note: structural parity, not asserted-by-coincidence).
TEAM_THRESHOLD = 2


def count_team_contributors(target: Path) -> int:
    """Return the number of DISTINCT mailmap-normalized git author emails in
    `target`'s history. Fail-soft to 0 on a non-git dir, missing binary, any
    git failure, or when `target` is inside a PARENT repo (avoids monorepo
    misdetection: scaffolding a fresh subdir of a multi-author repo would
    otherwise count the parent's authors).

    This is the single source of truth for the team signal (spec 050,
    Implementation note): `team_signal_fires` is `count >= TEAM_THRESHOLD`,
    and both `memory.py team-check` and `workflow.py stale` reach the count
    through this module so the threshold lives in exactly one place (parity
    is structural, not asserted-by-coincidence).

    Uses `--use-mailmap` so one person with multiple emails counts once."""
    try:
        # Refuse to climb to a parent repo: target itself must be the repo root.
        toplevel = subprocess.run(
            ["git", "-C", str(target), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
        if toplevel.returncode != 0:
            return 0
        if Path(toplevel.stdout.strip()).resolve() != Path(target).resolve():
            return 0

        out = subprocess.run(
            ["git", "-C", str(target), "log", "--use-mailmap", "--format=%aE"],
            capture_output=True, text=True, timeout=5,
        )
    except Exception:
        return 0
    if out.returncode != 0:
        return 0
    authors = {line.strip().lower() for line in out.stdout.splitlines() if line.strip()}
    return len(authors)


def team_signal_fires(target: Path) -> bool:
    """True iff `target`'s git history shows >= TEAM_THRESHOLD distinct
    mailmap-normalized author emails. Solo is the safe default (see
    `count_team_contributors` for the fail-soft + monorepo-guard behavior).
    The threshold lives here only."""
    return count_team_contributors(target) >= TEAM_THRESHOLD


# ---------- the .jig/no-people-md opt-out marker contract ----------
# A TRACKED project-level opt-out file (like `.jig/test-command`): its
# presence suppresses memory-sync's team-recheck nudge AND the stale
# team-context finding forever. Written by `scaffold-init --solo`
# (explicit-only) and by `memory.py team-check --never`. NOT gitignored: a
# deliberate solo choice should survive clone, and an auto-detected solo
# project that later grows must still be nudgeable (so auto-solo never
# writes it).
NO_PEOPLE_MD_RELPATH = (".jig", "no-people-md")
_NO_PEOPLE_MD_BODY = (
    "# jig: suppress people.md team-context nudge (spec 050).\n"
    "# Presence of this file is the signal — delete it to re-enable the\n"
    "# memory-sync team-recheck nudge.\n"
)


def no_people_md_marker_path(target: Path) -> Path:
    """Path to the `.jig/no-people-md` opt-out marker under `target`."""
    return target.joinpath(*NO_PEOPLE_MD_RELPATH)


def write_no_people_md_marker(target: Path) -> Path:
    """Atomically write the `.jig/no-people-md` opt-out marker. Idempotent —
    re-writing is a no-op in effect (presence is the only signal). Returns
    the marker path. Shared by `scaffold-init --solo` and `memory.py
    team-check --never` so the marker format lives in one place."""
    marker = no_people_md_marker_path(target)
    marker.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(marker, _NO_PEOPLE_MD_BODY)
    return marker


def people_md_path(target: Path) -> Path:
    """Path to `docs/memory/people.md` under `target`. The per-person
    context file the team signal nudges toward bootstrapping."""
    return target / "docs" / "memory" / "people.md"


def team_context_drift(target: Path) -> "int | None":
    """The shared "should we surface the team-context drift?" decision.

    Returns the contributor count N when ALL of:
      - the team signal fires (>= TEAM_THRESHOLD contributors), AND
      - `docs/memory/people.md` is absent, AND
      - the `.jig/no-people-md` opt-out marker is absent.
    Returns None otherwise (no drift to surface).

    Reused by `memory.py team-check` (the nudge) and `workflow.py stale`
    (the freshness-audit finding) so both apply the identical predicate.
    Reads git once via `count_team_contributors`, so a single call performs
    at most one git walk (spec 050-02 AC6 — no double-walk)."""
    if people_md_path(target).exists():
        return None
    if no_people_md_marker_path(target).exists():
        return None
    count = count_team_contributors(target)
    if count < TEAM_THRESHOLD:
        return None
    return count
