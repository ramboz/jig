#!/usr/bin/env python3
"""ADR-0058 Class B — claim reservation via a CAS ref (spec 112-05).

Primary claim surface: `refs/claims/<N>` — an atomic compare-and-swap lock.
Created LOCAL-FIRST (`git update-ref refs/claims/<N> HEAD ""`, empty
old-value = create-if-absent — spike 112-04's verified local CAS, which is
visible to every linked worktree sharing this repo's ref store, spike
finding A2 — "no lock needed for detection" there, but the CAS still closes
the SIMULTANEOUS-create race window, AC5). Cross-machine visibility is a
BEST-EFFORT push (`git push --force-with-lease=refs/claims/<N>: origin
HEAD:refs/claims/<N>` — the lease expects the ref ABSENT, so a concurrent
creator on another machine is rejected — spike 112-04's verified A1, probed
against GitHub personal). A host that rejects the custom `refs/claims/*`
namespace (untested EMU/org policy — spike 112-04's caveat) falls back to
an ADR-0053-shaped `reserve/<N>` branch (`refs/heads/*`, which every probed
host allows).

`claimed_by:` (slice frontmatter, ADR-0045) remains the human-readable
OWNER; this ref is the ATOMIC MECHANISM behind it. The ref carries NO
payload — its mere existence is the whole signal — because identity lives
in `claimed_by:`, not here (ADR-0058's Recommended Decision: "`claimed_by:`
is the human-readable *who*; the CAS ref is the atomic *mechanism*").

Liveness policy (ADR-0058 Assumption A3, resolved by this slice): MANUAL
`--release` only — no TTL / heartbeat. A CAS-ref collision can mean either
a live concurrent racer (AC5) or a stale ref left by a crashed session
(AC4), and this module makes NO ATTEMPT to tell them apart (a raw ref has
no timestamp or owner to read). That is a deliberate leanness choice, not
an oversight: distinguishing the two cheaply is exactly what ADR-0058
flagged as unverified (A3), and the identity-based hard block (ADR-0045's
both-ends-`IN_PROGRESS` check, extended cross-ref by
`find_sibling_in_progress_claim`) already carries the load-bearing halt —
this module's job is the RACE-WINDOW tie-break (AC5) and the reservation
record (AC1), surfaced as a non-blocking signal, never a second gate. A
stale ref is cleared by the same `--release` that already clears
`claimed_by:` (spec 049 AC5) — one release action for both.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from .reservation import classify_push_failure

# Network-call timeout (AC6) — a push must never hang the `transition`
# command; matches `_common.cross_ref_state._timeout_git`'s per-call bound.
_PUSH_TIMEOUT = 10


def claim_ref_name(identifier: str) -> str:
    """`refs/claims/<identifier>` — the CAS ref name for a slice id
    (`NNN-MM`)."""
    return f"refs/claims/{identifier}"


def reservation_branch_name(identifier: str) -> str:
    """ADR-0053-shaped fallback branch name (`reserve/claim-<N>`) for a host
    that rejects the custom `refs/claims/*` namespace."""
    return f"reserve/claim-{identifier}"


def _git(argv: list, cwd: Path) -> tuple:
    """Private, module-local git runner — same shape as
    `_common.reservation._git` / `_common.cross_ref_state._git` (not
    imported cross-module; each module keeps its own per the established
    convention). Never raises: an OSError becomes a non-zero rc."""
    try:
        result = subprocess.run(
            argv, cwd=str(cwd), capture_output=True, text=True, check=False,
        )
    except OSError as exc:
        return 1, "", str(exc)
    return result.returncode, result.stdout or "", result.stderr or ""


def _timeout_git(argv: list, cwd: Path) -> tuple:
    """Same shape as `_git`, but timeout-guarded (AC6) — the default `run`
    for `push_claim`, which touches the network."""
    try:
        result = subprocess.run(
            argv, cwd=str(cwd), capture_output=True, text=True, check=False,
            timeout=_PUSH_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, "", str(exc)
    return result.returncode, result.stdout or "", result.stderr or ""


def create_local_claim(identifier: str, project_dir, *, run=None) -> tuple:
    """Atomic local CAS create: `git update-ref refs/claims/<N> HEAD ""`
    (empty old-value = create-if-absent). Returns `(won, detail)`:

      - `(True, "")`   — this call created the ref; the caller holds it.
      - `(False, err)` — the ref already existed (AC5: a genuine
        simultaneous racer, or AC4: a stale ref left by a crashed session —
        this module cannot tell which; see the module docstring).
      - `(None, err)`  — git itself could not run the command (not a repo,
        `HEAD` unresolved, git missing) — an unknown, not a collision.

    Never raises."""
    git = run if run is not None else _git
    rc, _out, err = git(
        ["git", "update-ref", claim_ref_name(identifier), "HEAD", ""],
        project_dir,
    )
    if rc == 0:
        return True, ""
    if "already exists" in err.lower():
        return False, err
    return None, err


def release_local_claim(identifier: str, project_dir, *, run=None) -> None:
    """Best-effort local delete (`git update-ref -d refs/claims/<N>`).
    Idempotent — deleting an absent ref is a routine no-op, not an error.
    Never raises."""
    git = run if run is not None else _git
    git(["git", "update-ref", "-d", claim_ref_name(identifier)], project_dir)


def release_remote_claim(identifier: str, project_dir, *, run=None) -> None:
    """Best-effort remote delete (`git push origin :refs/claims/<N>`).
    Never raises — an unreachable/offline origin is exactly the case this
    degrades over (AC6); the local release above is what actually matters
    for AC4."""
    git = run if run is not None else _timeout_git
    git(
        ["git", "push", "origin", f":{claim_ref_name(identifier)}"],
        project_dir,
    )


def push_claim(identifier: str, project_dir, *, run=None) -> tuple:
    """Best-effort cross-machine CAS push:
    `git push --force-with-lease=refs/claims/<N>: origin HEAD:refs/claims/<N>`
    (spike 112-04's verified A1). Falls back to the `reserve/<N>`-shaped
    branch (`reservation_branch_name`) when the refusal classifies as
    "protection" (`_common.reservation.classify_push_failure`) — the
    signature of a host policy rejecting the custom ref namespace (spike
    112-04's untested-EMU caveat); every host probed allows a plain
    `refs/heads/*` push. Timeout-guarded (AC6): never hangs.

    Returns `(status, detail)`:
      - `("pushed", "")`             — created refs/claims/<N> on origin.
      - `("race", err)`              — the ref exists remotely already
                                        (AC5: "the loser is told").
      - `("fallback-pushed", branch)` — the custom ref was rejected;
                                        pushed `reserve/<N>` instead.
      - `("fallback-failed", err)`   — the namespace push AND the fallback
                                        both failed.
      - `("offline", err)`           — the push could not complete at all
                                        (no network, no origin, timeout) —
                                        AC6: degrades gracefully, no hang.

    Never raises."""
    git = run if run is not None else _timeout_git
    ref = claim_ref_name(identifier)
    rc, _out, err = git(
        ["git", "push", f"--force-with-lease={ref}:", "origin", f"HEAD:{ref}"],
        project_dir,
    )
    if rc == 0:
        return "pushed", ""

    kind = classify_push_failure(err)
    if kind == "race":
        return "race", err
    if kind == "protection":
        branch = reservation_branch_name(identifier)
        rc2, _out2, err2 = git(
            ["git", "push", "origin", f"HEAD:refs/heads/{branch}"],
            project_dir,
        )
        if rc2 == 0:
            return "fallback-pushed", branch
        return "fallback-failed", err2
    return "offline", err
