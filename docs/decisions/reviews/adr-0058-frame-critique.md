---
adr: 0058
pass: frame-critique
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-08-28T01:06:43Z
prompt_source: review.py frame-critique docs/decisions/adr-0058-cross-ref-lifecycle-state-check.md
---

Frame-critique of ADR-0058 (ref-aware lifecycle checks + claim-based work
reservation), run adversarially by isolated `jig:reviewer` subagents.

**Final verdict: pass.** The frame — "the current checkout is one witness, not the
truth; duplication has four distinct shapes caught by different mechanisms" —
survives, and is internally consistent across wiring items, assumptions, kill
criteria, and viability tiers.

**Gate-path disclosure:** ADR-0058 was briefly Accepted then reverted to Proposed
the same session, by explicit owner grant, to revise the decision before any
implementation — the un-integrated case moved from "advisory-only" to a
four-case model with claim reservation. Nothing was built against the accepted
version. This pass is on the revised text.

Four classes (final):
- A — already-integrated (origin/main DONE): hard gate. False-positive-free bar
  sanctioned re-open.
- B — concurrent in-flight race (both-ends-IN_PROGRESS): extend ADR-0045's block
  cross-ref via a claim reservation (ref-CAS lock); never re-blocks ADR-0045's
  sanctioned handoff.
- C — sequential re-do of work FINISHED on a sibling (THE REPORTED INCIDENT):
  sibling-DONE read, halt-and-reconcile with bypass; defensible because jig's
  DONE is evidence-gated (ADR-0014) hence expensive to fake.
- D — uncommitted/offline residual: fail-open advisory.

Viability tiers: incident-minimum = items 1+2 (both read-side, no reserve/release,
no unverified-capability gate); full coverage = +3 (Class-B reservation, gated on
a host-capability spike).

Iteration history (each round a real catch, each fixed):
- Rounds on the original design: raw sibling STATUS untrustworthy → provenance;
  incident is un-merged → not origin-visible; push-gating blind spot → scan local
  refs; committed-ref-reachability axis; converged to a passing three-class frame.
- After owner pushback (reservation can coordinate un-integrated work):
  - r1: "halt on any active claim" would re-block ADR-0045's sanctioned
    implementer→reviewer handoff → scope halt to both-ends-IN_PROGRESS.
  - r2: that re-scoping left the *reported* incident (sequential, DONE-on-sibling,
    claim cleared) uncaught by A or B → added Class C (sibling-DONE read).
  - r3: item-renumbering left the A1 spike gate pointing at the wrong wiring item;
    ref-vs-working-tree evidence bridge unstated → fixed both.
  - r4: pass; one note-only A1-vs-A2 tightening applied.

Disclosed spike-gated residuals (notes, carried into spec 112):
- A1 host capability (custom refs/claims/* CAS push) — spike-gated; fallback =
  ADR-0053 reservation branch.
- A2 worktree ref sharing; A3 claim liveness (stale-claim detection).
- Class-C spike exposure (abandoned-but-evidence-complete branch) — bypass, not
  silence.
- Class-D offline cross-machine — fail-open advisory only.

Reviewer: jig:reviewer (isolated, read-only, blind per round).
Prompt source: review.py frame-critique docs/decisions/adr-0058-cross-ref-lifecycle-state-check.md
