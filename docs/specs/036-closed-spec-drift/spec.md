---
status: DONE
skill: spec-workflow
tier: (none — dev infrastructure)
adr_required: true
---

# Spec 036: Closed-spec drift policy + one-time sweep

## Overview

jig's process treats ADRs as immutable but says nothing about closed
specs. In practice, closed specs drift as the implementation evolves
around them. Five concrete instances exist today (verified 2026-05-26).
The meta-problem: there is no rule for what happens when reality
diverges from a closed spec. ADRs are immutable; deviation logs annotate
slices at close-out only. Between RECONCILED and "the world changed
again," the spec just becomes stale.

This spec lands the **policy** as an ADR, then applies it retroactively
to the five known drifts and wires the rule into reconciliation.

## Why now

- **It's the foundation for the rest of the external-review cluster.**
  Specs 038 (tier reconciliation), 040 (isolation honesty), and 039
  (review-queue cleanup) all need to edit closed specs or load-bearing
  prose. Without a rule for *how* to do that, each cluster reinvents
  the convention.
- **The five drifts are stable and small.** A one-time sweep clears
  them; the cost of leaving them is misleading SKILL descriptions
  (which influence routing) and load-bearing spec prose that no longer
  matches code.
- **Dogfooding moment.** Slice 005-03's close-out swept the six → seven
  hook count in code, but *did not* sweep spec 016's "five jig hooks"
  prose. That's the exact pattern this spec is trying to prevent.

## Goals

1. **Decide the policy via ADR.** Closed specs are either (a)
   immutable like ADRs, with deltas landing as new ADRs or inbox
   entries; or (b) formally mutable with a documented amendment
   convention (e.g., an `## Amendments` section appended at the end,
   never in-body edits). Pick one. Hard-to-reverse decision.
2. **Apply the policy retroactively** to the five known-drifted
   artifacts listed below. One-time sweep, not an ongoing program.
3. **Wire the policy into reconciliation.** When a slice's
   reconciliation discovers that a prior closed spec is now wrong,
   the convention names the action. Adds one line to
   `skills/spec-workflow/SKILL.md`'s reconciliation checklist.

## Non-goals

- **No retroactive audit of every closed spec.** This sweep covers
  the five concrete drifts named below. A broader audit is separate
  effort if signal warrants.
- **No new tooling.** No `workflow.py audit-closed-specs` helper. The
  rule is for humans; helpers come if it turns out to need enforcement.
- **No changes to ADR immutability.** ADRs stay immutable per
  ADR-0006 / Nygard. This spec is about the gap *between* ADR-style
  immutability and the prose-edit free-for-all closed specs currently
  enjoy.

## Current state (verified 2026-05-26)

Five concrete drift instances, all live:

| # | Artifact | Claim | Reality |
|---|---|---|---|
| 1 | `docs/specs/016-scaffold-mode/spec.md:72, 412, 445, 471` | "the same five jig hooks" / "all five hook scripts" | 7 hooks today (six → seven sweep in slice 005-03) |
| 2 | `skills/pr-review/SKILL.md:14` | "jig does not ship an arch-review skill today" | Shipped in spec 014. **Influences router behavior** (SKILL description string). |
| 3 | `skills/memory-sync/SKILL.md:13–14` | "Slices 002-03 (auto-detect-hooks) and 002-04 (reconciliation-integration) are pending" | Both DONE per status board |
| 4 | `docs/workflow.md:114` | spec-workflow, independent-review, contracts are stubs with `disable-model-invocation: true` | None of the three carry that flag today; all auto-trigger |
| 5 | `README.md:35, 38` | "5 Tier 0 skills (not 100+)" / "8-12 skills total when complete" | 7 Tier 0 in `_TIER_SKILLS`; 14 skills total on disk |

Drift #5 also belongs to spec 038's scope — coordinate (see Dependencies
below).

## Decomposition

**Suggested SPIDR axis: R (Rules)** — policy is one rule; application
is another.

### Slices (TBD until clarify runs)

1. **`036-01 policy-adr`** — ADR with two options spelled out (immutable
   vs. amendment-section), recommendation, consequences. **Accept the
   ADR before slice 2 runs.**
2. **`036-02 sweep-and-reconciliation-hook`** — single slice applying
   the chosen policy to the five drifted artifacts (drift #5 deferred
   to 038 to avoid double-edit), plus a one-line reconciliation-checklist
   entry in `spec-workflow/SKILL.md` ("if reconciliation surfaces a
   prior closed-spec inaccuracy, follow the policy in ADR-NNNN").

If the sweep slice feels too wide, split per artifact (R-axis again),
but each is small — resist over-splitting.

## Open questions for `/jig:clarify`

- **Q1.** What's the cost difference between (a) immutable + new
  ADR/inbox for deltas vs. (b) `## Amendments` section?
  (a) means deltas have ADR overhead; (b) means specs become
  mutable history.
- **Q2.** Does the policy apply to RECONCILED specs only, or also
  IN_PROGRESS ones whose ACs change? Lean: RECONCILED only —
  IN_PROGRESS specs are still being shaped.
- **Q3.** Does drift #2 (pr-review SKILL "doesn't ship arch-review")
  count as closed-spec drift or skill-prose drift? Lean: the rule
  covers both — any artifact whose accuracy is load-bearing for
  router/process behavior.

## Dependencies / coordination

- **Upstream of 038, 039, 040.** All three edit closed-spec or
  load-bearing prose; they operate under whatever convention this
  spec establishes.
- **Drift #5 belongs to spec 038's scope.** Defer it from 036's
  sweep to avoid double-editing the README's Tier-0 line.
- **Light coupling with 042 (spec-gate model).** If the ADR picks
  "immutable," `docs/conventions.md` becomes one specific case
  of the broader rule. Flag in the ADR so the two policies
  don't conflict.

## References

- External review brief: [`brief-04-closed-spec-drift.md`](../../external-review/brief-04-closed-spec-drift.md)
- Verification 2026-05-26: all five drifts confirmed live.
- Related: ADR-0006 (accept-then-index ordering — ADR-style immutability
  baseline).

## Clarifications

### Q1: Does the closed-spec drift policy apply to RECONCILED specs only, or also to IN_PROGRESS specs whose ACs change mid-flight?
_(category: Edge Cases & Failure Modes)_

RECONCILED only. IN_PROGRESS specs are still being shaped — in-body edits are normal. The policy only kicks in once a slice has crossed RECONCILED → DONE.

### Q2: Does the policy cover load-bearing skill prose (e.g., drift #2 — pr-review SKILL.md saying "jig does not ship an arch-review skill"), or strictly closed-spec body prose?
_(category: Scope & Boundaries)_

Both — any load-bearing artifact. The rule covers any artifact whose accuracy is load-bearing for router/process behavior — SKILL.md descriptions, workflow.md routing prose, README claims that drive decisions. Aligned with the drift list as-is.

### Q3: What about specs in non-active terminal states — SUPERSEDED specs, DEFERRED slices, or specs whose entire scope was abandoned? Are they in scope for the drift policy?
_(category: Edge Cases & Failure Modes)_

In scope for SUPERSEDED, out for DEFERRED. Superseded specs may still be cited; keeping them accurate has value. DEFERRED slices are by definition not-yet-shipped, so there's no behavior to drift from.

### Q4: The decomposition section proposes 036-02 as one slice applying the policy to all four sweep-able drifts + adding the reconciliation-checklist line. Keep as one slice, or split per-artifact along R-axis?
_(category: Scope & Boundaries)_

One slice. The four sweep edits are mechanically small once the ADR is accepted; the reconciliation-checklist line is a one-liner. Splitting would add review overhead with no clarity benefit.

### Q5: If the ADR picks the `## Amendments` section route, what's the required shape of each amendment entry?
_(category: Edge Cases & Failure Modes)_

Dated entry + reason + link. Each amendment: `### YYYY-MM-DD — <one-line summary>` heading, body explains what changed and why, links to the slice/ADR/PR that caused the drift. Mirrors deviation-log discipline. Auditable.

### Coverage summary

| Category | Status |
|---|---|
| Scope & Boundaries | Resolved |
| Acceptance Criteria Testability | Partial (slice-level scaffolding still TBD) |
| Dependencies & Blockers | Clear |
| Non-functional Requirements | Clear |
| Edge Cases & Failure Modes | Resolved |
| Terminology Consistency | Clear |
