---
status: DEFERRED
dependencies: [112-03, adr-0058]
last_verified:
---

## Slice 112-07 — durable-landed-anchor

**Goal:** ADR-0058 wiring item 5 (Option C) — at the `DONE`/land transition, record
a structured `landed_commit` + `landed_branch` for the identifier, giving the
Class-C sibling read (112-03) a precise provenance pointer and removing memory as
the single, ephemeral copy of "where it landed."

**Resolution trigger:** Pick up when (a) Class C (112-03) is demoted to advisory
because the raw sibling-`DONE` read proves too spike-exposed and a trustworthy
anchor is needed to keep it a gate (ADR-0058 Kill criteria), or (b) a concrete
consumer needs the landed commit for reconciliation beyond the `DONE` marker.

**Acceptance Criteria (sketch, to be firmed on re-open):**

1. The `DONE`/land transition writes `landed_commit`/`landed_branch` to the chosen
   surface (slice/ADR frontmatter, so it travels on the ref a cross-ref read sees).
2. The Class-C read (112-03) prefers the anchor when present, falling back to the
   `DONE`-marker read.
3. Pre-anchor slices handled gracefully — absence of an anchor is never an error.

**DoD:** _Standard slice DoD applies once re-opened (DEFERRED → DRAFT)._

### Deviation log (after reconciliation)

_N/A — deferred._

### Reconciliation sweep

_N/A — deferred._
