---
adr: 0057
pass: frame-critique
verdict: pass
reviewer: jig:reviewer (independent adversarial frame-critique)
reviewed_at: 2026-08-15T17:39:20Z
prompt_source: review.py frame-critique adr-0057
---

## Frame-critique verdict — ADR-0057 (first-class blockers are annotations)

**Verdict: pass** (after one NEEDS-CHANGES round). Independent read-only
`jig:reviewer` adversarial frame-critique.

**Round 1 (NEEDS-CHANGES)** found a real framing hole: the original scope
restricted `blocked_by:` to *working* states only, which excluded a
`READY_FOR_IMPLEMENTATION` slice that is ready to start but stuck on an owner
decision — a genuine blocker from the portfolio-count view that fit none of the
ADR's three buckets and would have been spec_lint-flagged, over-claiming the
"retire the four proxies" consequence. Fixed by widening the scope to
**actionable** states (`READY_FOR_IMPLEMENTATION` + the working states), adding
the "why actionable, not started" rationale and its DRAFT/DONE/DEFERRED/ABANDONED
exclusions, and recording the un-probed consumer semantics as assumption A2 with
a kill condition.

**Round 2 (PASS)** verified all grounding against `workflow.py`:
`_CLAIM_WORKING_STATUSES` / `_CLAIM_RELEASE_STATUSES` (confirming a
`READY_FOR_IMPLEMENTATION` blocker is legitimately unclaimed), `collect_slices`
7-tuple + `CLAIM_FIELD`, the `render_deferred_table` pattern, and the A1
frontmatter-key enumeration (`blocked_by` genuinely absent). The annotation-vs-state
fork is a real, non-strawmanned choice; no conflict with ADR-0045 / ADR-0011 /
ADR-0014 / ADR-0025.

**Non-blocking (recorded):**
- The DRAFT exclusion is the premise most likely to be re-litigated by a real
  consumer (a DRAFT stuck on a scoping decision is arguably actionable-but-
  prevented); consciously drawn with A2's kill condition as the escape hatch.
- The stale "working-state" wording in Option B's pro was reconciled to
  "actionable-state" (the count definition every consumer implements).
