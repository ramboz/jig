---
status: Proposed
dependencies: [adr-0022, adr-0037]
last_verified: 2026-08-04
frame_review: true
---

# ADR-0050: Durable failure-quarantine and attest-only handshake

## Status

Proposed (2026-08-04)

> **Recorded, not yet built.** This ADR captures the jig-side decision for the
> long-horizon-autonomy bridge (the `oh-my-cli` follow-on). It is paired with the
> DRAFT [spec 105](../specs/105-durable-failure-quarantine/spec.md) and the
> servo-side [servo ADR-0030]. No `bug.py` code changes ship with this record.

## Context

For a jig/servo pair to run unattended for long horizons (the `oh-my-cli`
target), the single hardest failure mode is **thrash**: an agent re-attempting
the same doomed fix indefinitely, burning budget without new information.
`oh-my-cli` bounds this with a "third identical failure → quarantine; retry
requires new diagnostic evidence" rule.

Today neither side has a durable anti-thrash boundary:

- jig's bug record (`skills/bug-fix/bug.py`) has **no attempt counter**. The
  lifecycle re-enters `REVIEWED → DIAGNOSING` on a failed fix with no memory of
  how many times that has happened, and no terminal state for "we have tried
  this enough — stop and escalate."
- servo's `loop.py` persists an `oracle_score_history` plateau signal, but only
  **per run-id** (`<target>/.servo/runs/<run-id>/state.json`). Every fresh tick
  starts a new run-id and happily re-attempts the same plateaued finding.

The two are the *same phenomenon at two altitudes* (a bug-fix that won't
converge; an oracle that won't cross threshold). This ADR decides the **jig
side**: a terminal quarantine state on the bug record, an attempt counter, and a
release rule that requires new diagnostic evidence — plus the attest-only
handshake by which servo's plateau can drive a jig bug to quarantine without jig
ever re-running a score.

This extends the ADR-0022 pluggable-oracle boundary (jig reads servo evidence via
the filesystem, subprocess-only, never importing servo) and sits alongside
ADR-0037's bug-closure-evidence model (quarantine is a *non-DONE terminal* that,
like closure, is gated on recorded evidence).

## Decision Options Considered

### Option A: Ephemeral, per-run anti-thrash only (status quo, do nothing durable)
- **Pros:** No new state; simplest.
- **Cons:** Thrash survives across runs/ticks — the exact unattended-horizon
  failure. A per-run plateau is invisible to the next tick and to jig's record.
  Rejected: does not meet the autonomy target.

### Option B: Attempt counter + `QUARANTINED` terminal on the jig bug record; release-requires-new-evidence; servo attests via the boundary (recommended)
- **Pros:** Durable across sessions (lives in the committed bug record). Reuses
  the existing terminal-state machinery (board segregation, claim-release) rather
  than inventing a parallel store. The release rule reuses the existing
  `_diagnosis_gaps` evidence-pointer check. jig stays **attest-only** — it records
  that servo's loop plateaued; it never re-derives a score, preserving the
  ADR-0022 boundary. Anti-thrash works immediately for supervised bug-fix runs,
  before any loop is wired.
- **Cons:** Adds a state + a frontmatter field to `bug.py`; a quarantined item
  needs a human (or new evidence) to reopen — a deliberate cost.

### Option C: A separate cross-cutting quarantine store owned by neither lifecycle
- **Pros:** One home for all quarantine across bug/spec/oracle.
- **Cons:** New artifact + ownership question; duplicates the bug record's role;
  breaks the "writer owns its record" convention. Rejected as premature — revisit
  only if a third consumer appears (the ADR-0023 "extract at the third caller"
  discipline).

## Recommended Decision

Adopt **Option B**.

1. **New terminal state `QUARANTINED`** added to `VALID_BUG_STATUSES` and
   `TERMINAL_NON_DONE_STATUSES` in `bug.py`, so it inherits board segregation and
   marker-clear (`_BUG_TERMINAL_STATUSES`) for free. `QUARANTINED` is *terminal
   but not DONE* — the defect is unresolved; the loop has stopped attempting it.
2. **`attempts:` frontmatter field** on the bug record (`_record_text`),
   incremented at each failure re-entry (`REVIEWED → DIAGNOSING`) and the
   red-gate `→ FIXING`. Default threshold **N = 3** (matching `oh-my-cli`'s third
   identical failure), overridable.
3. On `attempts ≥ N`, `transition` routes the bug to `QUARANTINED`, **freezes**
   the `## Already tried` / `## Evidence` / `## Proof` sections (a snapshot), and
   releases the slice claim (pickup-queue release, per spec 049).
4. **Release requires new diagnostic evidence.** Reopening a `QUARANTINED` bug
   (→ `DIAGNOSING`) is refused unless the `## Evidence` pointer differs from the
   frozen snapshot — reusing the `_diagnosis_gaps` mechanism. This is `oh-my-cli`'s
   "retry requires new diagnostic evidence," landed on jig's evidence model.
5. **Attest-only handshake.** When servo quarantines a finding that maps to a jig
   bug (finding_id ↔ bug record), jig's `bug-fix` reads the servo evidence
   pointer and advances the bug to `QUARANTINED` **attest-only** — it records
   *that* servo's loop plateaued and *where* the evidence lives; it never re-runs
   or re-derives the oracle score. This is a concrete new use of the ADR-0022
   boundary (filesystem + subprocess, no shared imports).

## Consequences

**Becomes easier:**
- Unattended and supervised runs both stop thrashing after N attempts, with a
  durable, greppable record of why.
- The human's review surface shrinks to a **quarantine queue** instead of every
  commit.
- servo and jig share an anti-thrash boundary without coupling their code.

**Becomes harder:**
- A quarantined bug needs new evidence (or a human) to reopen — intentional
  friction that must not be bypassable by a bare status flip.
- `bug.py`'s state table and frontmatter grow; tests and the status board must
  learn the new terminal state.

## Assumptions

- `bug.py` exposes `VALID_BUG_STATUSES`, `TERMINAL_NON_DONE_STATUSES`,
  `_BUG_TERMINAL_STATUSES`, `_record_text`, and `_diagnosis_gaps` as the design
  references them. _Probe before building: re-read `skills/bug-fix/bug.py` — these
  names are cited from a prior exploration pass, not re-verified at authoring
  time, so slice 105-01's DoR must confirm them against the live source._
- servo writes a stable per-finding failure fingerprint jig can read (defined on
  the servo side in servo ADR-0030); jig only consumes it.

## Kill criteria

- If, in practice, N=3 quarantines healthy work more often than it stops thrash
  (false-positive quarantines dominate), the counter/threshold model is wrong —
  reconsider a signal richer than a raw attempt count.
- If a durable quarantine is never read by any consumer (no loop, no human queue
  ever consults it), the state is ceremony — shelve it.

## Open questions

- Exact fingerprint fields for the finding↔bug mapping (owned by servo ADR-0030;
  jig only needs the pointer).
- Whether `attempts` should also increment on `ESCALATED` paths or only on the
  fix-failure re-entry. Resolve in slice 105-01.
- **Keeping the recovery path exercised.** Quarantine is a *recovery* mechanism,
  not a prevention gate (EngTip #31, "Optimizing for Recovery, Not Prevention"),
  and a recovery path that is never used atrophies. The kill criterion above ("a
  durable quarantine never read by any consumer → shelve it") is the standing
  guard, but 105-01 should also ensure the *release* path (new-evidence accepted /
  stale-evidence refused), not just entry to `QUARANTINED`, is covered by the
  witnessed tests — an untested reopen path is the most likely thing to rot.
