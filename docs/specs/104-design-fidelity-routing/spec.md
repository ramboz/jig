---
status: IN_PROGRESS
skill: spec-workflow
use_cases: []
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 104: Design-fidelity routing

> Implements [ADR-0049](../../decisions/adr-0049-design-fidelity-routing-to-originating-spec.md)
> for [issue #179](https://github.com/ramboz/jig/issues/179). The routing
> **decision** lives in the ADR (with its rejected alternatives + frame-critique);
> this spec is the **implementation** on the two read-surfaces that drive agent
> behavior: `bug-fix`'s triage tiers and `spec-workflow`'s authoring flow.

## Overview

Design feedback — "the built screen doesn't match the mockup" — had no clean
lifecycle home; triage stalled on "bug or spec?" and neither fit (issue #179).
ADR-0049 rules that this middle-row work is **spec-shaped work carried on the
spec spine** (the originating spec when one exists, a new spec when none does) —
an unmet, non-deterministic acceptance criterion (mockup fidelity), not a defect.
It rejects a new
lifecycle vehicle (issue option 3) as duplicating the spec spine for zero new
capability, and it names the existing rails for the non-deterministic
done-condition: spec 071's attest-only `design_review` pass + servo's
`design-eval` threshold.

This spec makes that ruling operative where agents actually read it:

1. **Triage disambiguation** (`bug-fix`) — `bug-fix`'s gnarly tier currently
   lists "design-gap" as a bug tier that "may escalate to a spec"
   (`skills/bug-fix/SKILL.md:71`). That is the reported mis-routing surface.
   Slice 104-01 disambiguates it: a design **malfunction** is a bug; a pure
   visual **fidelity gap** against an agreed mockup routes to the spec spine —
   the originating spec when one exists, a **new** spec when none does (the
   mockup-first / cross-platform rebuild that provoked #179) — never `bug-fix`.
   It also states the operative fidelity-vs-refinement test (does the visual
   *target* change?).
2. **Authoring nudge** (`spec-workflow`) — when a slice has visual design,
   authors should extract the design values (colours, spacing, sizes, layout
   rules) into checkable ACs and, when fidelity must gate, flag `design_review`
   and wire a servo `design-eval`. Slice 104-02 adds that nudge to the
   spec-authoring flow + the slice template, so the gap is prevented at
   authoring time rather than discovered post-`DONE`.

**Non-goals (from ADR-0049):**
- No new "design-fidelity" lifecycle vehicle / CLI verb (Option A, rejected).
- No mechanical auto-detector of "this slice has visual design" — over-firing a
  keyword detector is worse than prose guidance (see Assumptions + ADR-0049 Kill
  criteria). The nudge raises the question on the authoring hot-path and anchors
  teeth to the *existing* `design_review` flag; a harder detector is a future
  slice only if the nudge proves unreachable.
- No tight machine binding to servo's exit code — that stays PARKED under
  ADR-0022. jig attests, never re-derives.

## Assumptions

None.

_All load-bearing claims are probe-verified this session and cited inline in the slice DoRs (spec 071 DONE; servo `design-eval` present; `bug-fix` design-gap tier at `skills/bug-fix/SKILL.md:71`; slice template `design_review:` comment) — so both slices implement a settled decision (ADR-0049) with no unverified load-bearing assumptions, and `frame_review` derives off for them; the decision's adversarial pass rides ADR-0049's always-on `frame_review`._

## Decomposition

**SPIDR — Rules then Interface (no Spike — the decision is settled in
ADR-0049).**

- **R — Rules (104-01):** the simplest, highest-value rule first — the triage
  test that routes a design complaint. Delivered on the surface where triage
  happens (`bug-fix` SKILL.md). Vertical: it changes the triage decision an
  agent makes, end-to-end.
- **I — Interface (104-02):** split by authoring surface — the spec-authoring
  flow + slice template that authors read when writing a slice with visual
  design. Vertical: it changes what design-bearing slices get written to carry.

Neither slice is horizontal phasing: each changes a read-surface that directly
drives agent behavior (triage routing; slice authoring). No slice touches only
an internal layer.

## Slices

- [104-01 — triage-disambiguation](slice-01-triage-disambiguation.md) — a design
  malfunction is a bug; a pure visual fidelity gap routes to the spec spine
  (originating or new), never `bug-fix`.
- [104-02 — authoring-nudge](slice-02-authoring-nudge.md) — spec-authoring flow +
  slice template nudge visual-design slices toward checkable design-value ACs and
  the `design_review` / servo `design-eval` rail.
