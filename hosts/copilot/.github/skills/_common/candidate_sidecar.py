"""Candidate-channel sidecar — spec 096-03 (ADR-0040 D3 / OQ2).

The zero-config selection channel needs a small piece of durable state that
carries the **shown candidate set** from the `candidates` step, through the
reviewer spawn, to `record-review` — so `record-review` can derive its
`substrate:` from what was *actually shown and declined* (096-05), rather than
trusting the orchestrator to re-state it. This module owns that sidecar.

**Keyed to `(spec, slice, pass)`** and co-located with the review evidence at
`<spec_dir>/reviews/.candidates/slice-NN-<pass>.json`.

**Lifetime / absence / staleness (AC9 — a correctness requirement, not an
implementation detail).** The sidecar is designed so that *staleness becomes
impossible* once the consume step is wired, which is what makes 096-05's
`not-shown` signal honest:

  1. `write_shown` (the `candidates` step) CREATES it — the sole writer of the
     candidate set, with a fresh `run_id` + `created_at`. Re-running `candidates`
     overwrites atomically (fresh set, pick reset).
  2. `record_pick` (the pass call) sets the orchestrator's pick.
  3. `consume` (`record-review`, **wired in 096-05**) reads it into the evidence
     artifact and then DELETES it.

**Note on sequencing:** steps 1–2 ship in 096-03; the *consume* of step 3 is
wired by 096-05 (it must delete + record together, so the shown set is captured
before removal). Until then, staleness is prevented by the always-run-`candidates`
recipe discipline + the atomic fresh-overwrite of step 1 (a re-review re-runs
`candidates`, replacing any leftover) rather than by construction. Once 096-05
lands, the sidecar never survives a cycle, and on a re-review:
  - if `candidates` is re-run → a fresh sidecar exists (`shown`);
  - if `candidates` is skipped → NO sidecar exists (`not-shown`).
There is no third "stale leftover" state to misread as a fresh `shown`. Absence
unambiguously means "the selection step did not run this cycle."

**Concurrency.** Writes are atomic (`atomic_io.atomic_write_text`). Distinct
passes are distinct keys, so `craft` and `arch` never collide. Two concurrent
runs of the *same* `(slice, pass)` is pathological (you do not review one slice's
craft twice at once); last-atomic-writer-wins, documented as acceptable.

`_common` is a LEAF: stdlib + the sibling `atomic_io` only.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from _common.atomic_io import atomic_write_text


class SidecarError(RuntimeError):
    """The sidecar is required for an operation but is absent / unreadable."""


def _slice_number(slice_fragment: str) -> str:
    """Extract the `NN` slice number from a fragment like `096-03` / `096-03 —
    enumerate` for the filename. Falls back to a sanitized fragment."""
    frag = slice_fragment.strip()
    # Prefer the trailing `-NN` of a `MMM-NN` id.
    head = frag.split()[0] if frag.split() else frag
    if "-" in head:
        tail = head.rsplit("-", 1)[1]
        if tail.isdigit():
            return tail
    return "".join(c for c in head if c.isalnum()) or "xx"


def sidecar_path(spec_path: Path, slice_fragment: str,
                 pass_name: str) -> Path:
    """`<spec_dir>/reviews/.candidates/slice-NN-<pass>.json`."""
    spec_dir = Path(spec_path).parent
    return (spec_dir / "reviews" / ".candidates"
            / f"slice-{_slice_number(slice_fragment)}-{pass_name}.json")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_shown(spec_path: Path, slice_fragment: str, pass_name: str,
                category: str, candidates: "list[dict]") -> Path:
    """CREATE (or overwrite) the sidecar with the shown, tiered candidate set.
    The sole writer of the set (ADR-0040 D3 — one enumeration code path). Fresh
    `run_id` + `created_at`; `pick` reset to None. Returns the path."""
    path = sidecar_path(spec_path, slice_fragment, pass_name)
    payload = {
        "spec": str(Path(spec_path).parent.name),
        "slice": slice_fragment,
        "pass": pass_name,
        "category": category,
        "run_id": uuid.uuid4().hex,
        "created_at": _now(),
        "candidates": candidates,
        "pick": None,
        "picked_at": None,
        "applied_path": None,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, json.dumps(payload, indent=2) + "\n")
    return path


def read_sidecar(spec_path: Path, slice_fragment: str,
                 pass_name: str) -> "dict | None":
    """Read the sidecar, or `None` when absent / unreadable / malformed
    (absence is a first-class state — `not-shown`; never raises)."""
    path = sidecar_path(spec_path, slice_fragment, pass_name)
    try:
        if not path.is_file():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def record_pick(spec_path: Path, slice_fragment: str, pass_name: str,
                pick: str, applied_path: "str | None") -> dict:
    """Set the orchestrator's `pick` (a candidate name or the literal `none`)
    into the EXISTING sidecar. Raises `SidecarError` when no sidecar exists —
    the pass must not record a pick against a set that was never shown (the
    fail-fast the orchestrated path relies on). Returns the updated payload."""
    data = read_sidecar(spec_path, slice_fragment, pass_name)
    if data is None:
        raise SidecarError(
            f"no candidate sidecar for ({slice_fragment}, {pass_name}) — the "
            f"`candidates` step must run before a pick is recorded"
        )
    data["pick"] = pick
    data["picked_at"] = _now()
    data["applied_path"] = applied_path
    atomic_write_text(sidecar_path(spec_path, slice_fragment, pass_name),
                      json.dumps(data, indent=2) + "\n")
    return data


def consume(spec_path: Path, slice_fragment: str,
            pass_name: str) -> "dict | None":
    """Read the sidecar AND delete it (the end-of-cycle consume that makes
    staleness impossible — 096-05's `record-review` calls this). Returns the
    payload, or `None` when absent. Deletion errors are swallowed (best-effort;
    a leftover empty dir is harmless)."""
    data = read_sidecar(spec_path, slice_fragment, pass_name)
    path = sidecar_path(spec_path, slice_fragment, pass_name)
    try:
        if path.is_file():
            path.unlink()
    except OSError:
        pass
    return data


def has_shown(spec_path: Path, slice_fragment: str, pass_name: str) -> bool:
    """True iff a sidecar exists for `(slice, pass)` — i.e. the `candidates`
    step ran this cycle. Used by the pass fail-fast (AC6)."""
    return read_sidecar(spec_path, slice_fragment, pass_name) is not None
