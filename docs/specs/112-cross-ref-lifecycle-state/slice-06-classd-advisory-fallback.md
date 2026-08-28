---
status: DEFERRED
dependencies: [112-01, adr-0048, adr-0058]
last_verified:
---

## Slice 112-06 — classd-advisory-fallback

**Goal:** ADR-0058 Class D / wiring item 4 — the fail-open advisory for the cases
the hard mechanisms can't reach: un-claimed sibling divergence, and the
offline / no-reachable-ref residual. Extend git-freshness (ADR-0048) to surface,
at SessionStart and create-time, "N looks more advanced on `<ref>` than here —
reconcile," never blocking.

**Resolution trigger:** Pick up once the incident-minimum (112-01..03) and Class-B
(112-05) have landed and real usage shows a residual gap — divergence that none of
the gates caught but a heads-up would have surfaced. Until then the hard
mechanisms cover the tractable classes; this is the low-confidence safety net.

**Acceptance Criteria (sketch, to be firmed on re-open):**

1. SessionStart + create-time nudge on a sibling ref more advanced than the
   checkout, fail-open and explicitly low-confidence; own-branch-ahead-of-base is
   not flagged.
2. Never changes an exit code; timeout-guarded / silent on error.
3. Scoping knob (same-spec-dir refs, or opt-in) if noisy on a high-branch trunk
   (ADR-0058 Kill criteria / Open-question).

**DoD:** _Standard slice DoD applies once re-opened (DEFERRED → DRAFT)._

### Deviation log (after reconciliation)

_N/A — deferred._

### Reconciliation sweep

_N/A — deferred._
