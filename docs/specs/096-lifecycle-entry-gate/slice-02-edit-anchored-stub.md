---
status: DEFERRED
dependencies: [adr-0039]
last_verified: 2026-07-24
---

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about runnable
     surfaces by probe first (run it / read source) or a citation, else mark them
     as assumptions — never assert an unverified claim as fact. -->

## Slice 096-02 — edit-anchored capture stub (DEFERRED)

**Goal:** The same out-of-lifecycle edit that triggers slice 096-01's nudge also
leaves a durable capture stub, so the omission survives until something records
it — one mechanism, two payoffs ([#108](https://github.com/ramboz/jig/issues/108)
direction #2). The stub feeds spec 083-07's re-surfacing loop rather than a new
store.

**Status: DEFERRED — resolution trigger:** the capture-rewrite decision (fix-plan
Track B1 / the spec 083 successor) is Accepted. That decision fixes the shape of
the stub record and whether the conversation scan survives, and this slice writes
into that shape. Building it first would couple the entry gate to machinery the
maintainer has not settled; #111 constraint and the fix plan both say not to
implement capture ahead of that choice.

**Why it is a separate slice, not part of 096-01:** 096-01 is correct and
shippable on its own — the nudge closes the "edited with nothing in flight" hole.
The stub adds *durability* on top and inherits the capture rewrite's dependencies
and risks (dedup fate, host parity). Keeping them separate keeps 096-01
revertable and unblocked.

**When un-deferred, acceptance will cover (sketch, not binding):**
- The 096-01 trigger additionally writes one stub in the format the capture-rewrite
  decision defines, anchored to the edited file + edit.
- The stub is picked up by the existing 083-07 durability / re-surfacing loop and
  cleared when the edit is routed or recorded.
- Additive and fail-open: a stub-write failure never affects the 096-01 nudge or
  the session.
