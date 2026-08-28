---
status: Proposed
dependencies: []
last_verified: 2026-08-27
frame_review: true
---

# ADR-0059: Servo-delivered work earns a light jig design-review before DONE — an oracle pass is not "done"

## Status

Proposed (2026-08-27)

> Filed from a dogfood run against the **airlock** project (spec 008, GA4
> purchase-conversion), where jig and servo are used together. Evidence is
> external to this repo; the owner should run the frame-critique + accept flow
> before adopting. Complements a servo-side handoff ADR (servo ADR-0033's
> sibling line — servo declares *delivered*, not *done*).

## Context

The servo↔jig routing principle (servo drives unattended loops where the oracle
is strong; jig stays supervised where it is weak) is sound, but it has an
under-specified seam: **what happens when a strong-oracle servo loop reports
`oracle_passed`?** In practice that has been treated as "done." It is not.

A servo loop proves exactly one thing: **the code conforms to the eval that was
written.** It cannot judge whether that eval / contract is *complete or correct*,
and it cannot see beyond the file it changed. Those are precisely the
design-and-reconciliation questions jig's supervised passes exist for — and they
are the oracle's structural blind spot, not a servo defect.

Worked example (airlock spec 008 — GA4 `purchase` conversion, servo-delivered):
the oracle passed green (`oracle.sh` composite 1.0, 127/127 tests, and the diff
review confirmed no test-gaming). A **light** jig design pass on the *result*
then found two **load-bearing** gaps the oracle was blind to:

1. the connector's mapper now *throws* on a malformed purchase, but its worker
   caller has **no per-event try/catch** — an uncaught throw silently drops the
   whole cycle's batch, *worse* than the bug it fixed; and
2. the pinned schema cannot even represent the event's payload shape, so the
   "conformance oracle" never actually validated it —

plus a spec Non-goal that was **factually false** ("already conforms"). None of
these could move the oracle, because the eval never asserted them.

## Decision Options Considered

### Option A: Require a *light* jig design/reconciliation review before a servo-delivered spec reaches DONE (chosen)
- **Pros:** closes the oracle's blind spot (design/contract correctness,
  cross-file reconciliation) with a bounded, cheap pass; keeps the servo speed
  win (the loop still owns the implementation gate); makes the handoff explicit
  instead of implicit-"done".
- **Cons:** re-introduces a human/jig step into the servo-unattended path (kept
  small — a design-look + reconciliation-sweep, *not* the full ceremony).

### Option B: Trust the oracle — `oracle_passed` ⇒ DONE (status quo)
- **Cons:** ships design/contract gaps unreviewed (the 008 evidence:
  silent-batch-loss + un-representable schema would have landed on a green
  oracle). Rejected.

### Option C: Run the *full* jig ceremony (frame-critique + compliance + craft + arch + reconciliation) on servo output
- **Cons:** over-process and largely redundant — the oracle *is* the compliance
  gate (it passed), and re-running frame-critique/craft on already-oracle-gated
  implementation duplicates the loop. Rejected in favour of the light pass.

## Recommended Decision

Adopt **Option A**. jig recognizes servo-delivered work (e.g. a
`servo_driven: true` spec marker) and **refuses the `DONE` transition without a
recorded design-review verdict** — a *light* pass covering (a) a human diff
review for reward-hacking, (b) a design-review of the eval/contract itself (is it
complete? edge cases? failure mode?), and (c) a reconciliation micro-sweep for
doc/ADR drift the change introduced. Not the full multi-pass ceremony: the
oracle already discharged compliance, so this is only the parts the oracle
*cannot* do.

The division of labour: **servo owns the implementation gate** (fast, cheap,
fail-safe, deterministic-oracle); **jig owns the design gate** (the oracle's
blind spot). "Servo delivers; jig disposes."

## Consequences

**Becomes easier:**
- A servo-unattended win can no longer silently ship a design/contract gap; the
  routing has an explicit `delivered → design-review → done` handoff instead of
  an implicit trust jump.

**Becomes harder:**
- The servo-unattended path is no longer end-to-end unattended for a spec that
  must reach DONE — a bounded human/jig step remains. (Acceptable: the light
  pass is minutes, not the full ceremony; and the loop's implementation work
  stays autonomous.)

## Assumptions

- A *light* design pass reliably catches what the oracle cannot — evidenced by
  008, where it surfaced two load-bearing gaps and a false spec claim the green
  oracle missed. If light passes rarely find anything the oracle didn't, the
  gate is overhead.

## Kill criteria

- If evals become expressive enough to encode the full design contract (so that
  `oracle_passed` ⇒ design-correct, not merely conformant-to-a-partial-eval),
  this gate is redundant and should be retired. Today they are not:
  the eval is authored by a human and only ever asserts a subset.

## Open questions

- The trigger marker: is `servo_driven: true` frontmatter the right signal, or
  should jig infer it from the presence of a servo run artifact
  (`.servo/runs/*`) touching the spec's files?
- Where the design-review verdict is recorded (a new `design` pass alongside the
  existing review-evidence set, vs. reusing `arch`/`reconciliation`).
