"""Lifecycle entry gate — spec 098-01 / ADR-0044.

Decide whether an ``Edit``/``Write``/``MultiEdit`` to *project source* happened
while the session is **outside** the jig lifecycle, and if so return one
agent-facing nudge: "this edit is outside jig — route it (claim a slice / open a
bug) or record it." No block, no owner prompt, no failure mode for the session.

`evaluate()` is the tested surface; the thin `jig-entry-gate.sh` wrapper handles
stdin, `additionalContext` printing, and the auditable trace. Everything is
fail-open: any error leaves the session untouched.

"Inside the lifecycle" is a live *working-lifecycle claim held by this checkout*
(ADR-0044 resolved question #5), read from the one working-tree marker both
lifecycles now stamp — `.jig/spec-ref`:

- **Slice arm** — a ``spec=``/``slice=`` marker whose named slice is
  ``claimed_by`` this checkout AND is in one of #138's working statuses
  (``READY_FOR_REVIEW`` / ``IN_PROGRESS`` / ``REVIEWED`` / ``RECONCILED``).
- **Bug arm** — a ``bug=`` marker (slice 098-04) whose named bug record is
  ``claimed_by`` this checkout AND is in an open (non-terminal) status.

The status cross-check makes a stale marker harmless: nothing clears
``.jig/spec-ref`` when a *slice* leaves a working state (``workflow.py`` writes it
only at ``IN_PROGRESS``), so the marker alone would assert a finished slice
forever.

The source boundary (settled call #3) is two-part: a path is source unless
**(a)** ``git check-ignore`` reports it ignored, **or (b)** it is under a *named*
lifecycle-artifact subtree (``specs`` / ``bugs`` / ``decisions`` / ``memory``
resolved against the docs base) or under ``.jig`` / ``.claude`` / ``.git``.
Part (b) never uses ``docs_base`` wholesale — under ``docs_root="."`` that IS the
project root, which would switch the gate off for a track-local adopter.

`_common` (``project_layout``, ``parsing``) is on ``sys.path`` via the ``.sh``
wrapper. Python 3.9 compatible.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Optional

try:  # hook runtime: skills/ on sys.path (added by jig-entry-gate.sh)
    from _common import project_layout
    from _common.parsing import parse_frontmatter
except Exception:  # pragma: no cover - exercised only in a broken install
    project_layout = None  # type: ignore
    parse_frontmatter = None  # type: ignore

# Opt-out token set — mirrors _common/parsing.ENV_FALSEY and jig-boundary-change
# -warn (kept inline so the gate gains no cross-import failure mode).
_DISABLE_VALUES = {"0", "false", "off", "no"}

# #138's working-lifecycle claim span (slice arm). Mirrors
# workflow.py._CLAIM_WORKING_STATUSES; a source-inspection test pins them in sync.
_SLICE_WORKING_STATUSES = {"READY_FOR_REVIEW", "IN_PROGRESS", "REVIEWED", "RECONCILED"}

# Open (non-terminal) bug statuses — a present bug marker (stamped by 098-04's
# pickup/transition in THIS tree) plus one of these means the fix is in flight.
# Mirrors bug.py.OPEN_STATUSES; a source-inspection test pins them in sync.
# Includes REPORTED because `pickup` stamps the marker before the first
# transition — the just-picked-up bug is already inside (098-01 anti-false-fire).
# ACCEPTED LIMIT (frame review): the bug arm deliberately uses the full
# OPEN_STATUSES span, broader than the slice arm's curated
# _SLICE_WORKING_STATUSES — a claimed bug that sits open (incl. the near-release
# VERIFIED) keeps the gate silent. This mirrors the slice arm's RECONCILED
# tolerance and is bounded because 098-04 clears the marker at every terminal
# state; 098-02 (Codex parity) must keep the same span.
_BUG_OPEN_STATUSES = {
    "REPORTED", "DIAGNOSING", "ROOT_CAUSED", "FIXING", "REVIEWED", "VERIFIED",
}

# Lifecycle-artifact subtrees resolved against the docs base — part (b) of the
# source boundary. NAMED subtrees only, never docs_base wholesale.
_ARTIFACT_SUBDIRS = ("specs", "bugs", "decisions", "memory")
# Repo-infra directories at the project root that are never project source.
_INFRA_DIRS = (".jig", ".claude", ".git")

_MARKER_REL = Path(".jig") / "spec-ref"
_STATE_PREFIX = "jig-entry-gate-"


# --------------------------------------------------------------------------- #
# Claim identity (mirrors workflow.py / bug.py `_claim_identifier`)
# --------------------------------------------------------------------------- #
def _claim_identifier(project_dir: Path) -> str:
    env = os.environ.get("JIG_CLAIM_ID")
    if env and env.strip():
        return env.strip()
    try:
        # timeout so a hung git (index lock, slow network FS) can never stall
        # the session — this runs on EVERY edit. TimeoutExpired is an Exception,
        # so the surrounding handler catches it (fail-open → "detached").
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=str(project_dir), capture_output=True, text=True,
            check=False, timeout=5,
        )
        branch = (result.stdout or "").strip()
        if branch:
            return branch
    except Exception:
        pass
    return "detached"


# --------------------------------------------------------------------------- #
# In-lifecycle detection
# --------------------------------------------------------------------------- #
def _read_marker(project_dir: Path) -> str:
    try:
        return (Path(project_dir) / _MARKER_REL).read_text(
            encoding="utf-8", errors="replace")
    except Exception:
        return ""


def _marker_field(text: str, key: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line.startswith(key + "="):
            return line[len(key) + 1:].strip()
    return ""


def _frontmatter_status_and_claim(path: Path) -> "tuple[str, str]":
    """(status, claimed_by) from a slice/bug record, or ("","") on any miss."""
    try:
        fields, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
    except Exception:
        return "", ""
    return (str(fields.get("status") or "").strip(),
            str(fields.get("claimed_by") or "").strip())


def _resolve_slice_file(project_dir: Path, spec_num: str, slice_id: str) -> Optional[Path]:
    """Locate the file-per-slice record `specs/<spec_num>-*/slice-<mm>-*.md`.

    Takes the first sorted match; a spurious multi-match would fail toward a
    nudge via the downstream status/claim cross-check, never toward silence."""
    try:
        specs = project_layout.specs_dir(Path(project_dir))
    except Exception:
        return None
    mm = slice_id.split("-", 1)[1] if "-" in slice_id else ""
    for spec_dir in sorted(specs.glob(f"{spec_num}-*")):
        if not spec_dir.is_dir():
            continue
        for f in sorted(spec_dir.glob(f"slice-{mm}-*.md")):
            if f.is_file():
                return f
    return None


def _resolve_bug_file(project_dir: Path, bug_num: str) -> Optional[Path]:
    try:
        bugs = project_layout.docs_base(Path(project_dir)) / "bugs"
    except Exception:
        return None
    for f in sorted(bugs.glob(f"{bug_num}-*.md")):
        if f.is_file():
            return f
    return None


def is_inside_lifecycle(project_dir: Path, claim_id: str,
                        marker: Optional[str] = None) -> bool:
    """True iff this checkout holds a live working-lifecycle claim, read from
    `.jig/spec-ref`. Positive confirmation only — an unresolvable or
    released/terminal marker returns False (so the gate can still fire).

    `marker` may be passed pre-read to avoid a second file read; None reads it."""
    if marker is None:
        marker = _read_marker(project_dir)
    if not marker:
        return False

    bug_num = _marker_field(marker, "bug")
    if bug_num:
        record = _resolve_bug_file(project_dir, bug_num)
        if record is None:
            return False
        status, claimed_by = _frontmatter_status_and_claim(record)
        return claimed_by == claim_id and status in _BUG_OPEN_STATUSES

    spec_num = _marker_field(marker, "spec")
    slice_id = _marker_field(marker, "slice")
    if spec_num and slice_id:
        record = _resolve_slice_file(project_dir, spec_num, slice_id)
        if record is None:
            return False
        status, claimed_by = _frontmatter_status_and_claim(record)
        return claimed_by == claim_id and status in _SLICE_WORKING_STATUSES

    return False


# --------------------------------------------------------------------------- #
# Source boundary
# --------------------------------------------------------------------------- #
def _git_ignores(project_dir: Path, file_path: str) -> bool:
    """True iff `git check-ignore` reports the path ignored. Degrades to False
    (not ignored) on a non-repo, a missing git, or any error (AC3/AC8)."""
    try:
        result = subprocess.run(
            ["git", "check-ignore", "-q", "--", file_path],
            cwd=str(project_dir), capture_output=True, text=True,
            check=False, timeout=5,
        )
        return result.returncode == 0
    except Exception:
        # non-repo, missing git, or timeout → degrade to "not ignored" (AC8).
        return False


def _under(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except Exception:
        return False


def _is_lifecycle_artifact(project_dir: Path, file_path: str) -> bool:
    """Part (b): the path is a lifecycle artifact under a NAMED subtree."""
    root = Path(project_dir)
    target = Path(file_path)
    if not target.is_absolute():
        target = root / target
    for infra in _INFRA_DIRS:
        if _under(target, root / infra):
            return True
    try:
        base = project_layout.docs_base(root)
    except Exception:
        base = root / "docs"
    for sub in _ARTIFACT_SUBDIRS:
        if _under(target, base / sub):
            return True
    return False


def is_source_path(project_dir: Path, file_path: str) -> bool:
    """A path is project source unless (a) git-ignored or (b) a lifecycle
    artifact. `docs_base` is never used wholesale (the `docs_root="."` trap)."""
    if _is_lifecycle_artifact(project_dir, file_path):
        return False
    if _git_ignores(project_dir, file_path):
        return False
    return True


# --------------------------------------------------------------------------- #
# Cadence — once per session, re-arm on lifecycle-state change
# --------------------------------------------------------------------------- #
def _state_path(state_dir: str, session_id: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in session_id)
    return Path(state_dir) / (_STATE_PREFIX + safe + ".json")


def _cadence_allows(state_dir: str, session_id: str, signature: str) -> bool:
    """Fire at most once per session, re-arming when `signature` changes. When
    `session_id` is missing we do NOT dedupe against a shared key (that would
    globally silence the gate) — we always allow the fire (safe over-fire)."""
    if not session_id:
        return True
    try:
        path = _state_path(state_dir, session_id)
        prior = {}
        if path.is_file():
            try:
                prior = json.loads(path.read_text(encoding="utf-8")) or {}
            except Exception:
                prior = {}
        already = bool(prior.get("fired")) and prior.get("sig") == signature
        if already:
            return False
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"fired": True, "sig": signature}),
                        encoding="utf-8")
        return True
    except Exception:
        # State unreadable/unwritable: fire rather than silence (safe direction).
        return True


# --------------------------------------------------------------------------- #
# The nudge
# --------------------------------------------------------------------------- #
def _nudge_text(file_path: str) -> str:
    return (
        f"{file_path} was just edited outside the jig lifecycle — no slice or "
        f"bug is claimed by this checkout. Route it (claim a slice with "
        f"`workflow.py transition <slice> IN_PROGRESS`, or open/pick up a bug "
        f"with `bug.py`) or record it (e.g. `/jig:memory-sync`). This nudge is "
        f"informational, not a gate."
    )


# --------------------------------------------------------------------------- #
# Main entry
# --------------------------------------------------------------------------- #
def evaluate(payload: dict, project_dir, state_dir: str) -> Optional[str]:
    """Return the nudge text for an out-of-lifecycle source edit, or None.

    Fail-open: any error returns None (the caller stays silent). Reads the
    opt-out env internally so the wrapper stays thin.
    """
    try:
        if (os.environ.get("JIG_ENTRY_GATE") or "").strip().lower() in _DISABLE_VALUES:
            return None
        if not isinstance(payload, dict):
            return None
        if payload.get("tool_name") not in ("Edit", "Write", "MultiEdit"):
            return None
        tool_input = payload.get("tool_input") or {}
        if not isinstance(tool_input, dict):
            return None
        file_path = tool_input.get("file_path") or ""
        if not file_path:
            return None
        if project_layout is None:  # broken install — degrade to silent
            return None

        project_dir = Path(project_dir)
        marker = _read_marker(project_dir)  # read once; reused for the signature
        claim_id = _claim_identifier(project_dir)
        if is_inside_lifecycle(project_dir, claim_id, marker):
            return None
        if not is_source_path(project_dir, file_path):
            return None

        # Outside + source: fire, subject to per-session cadence. The signature
        # is the marker content, so claiming/releasing a work item re-arms.
        signature = marker.strip()
        session_id = payload.get("session_id") or ""
        if not _cadence_allows(state_dir, session_id, signature):
            return None
        return _nudge_text(file_path)
    except Exception:
        return None
