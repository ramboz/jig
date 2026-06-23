---
status: DONE
skill: (none — doc sweep)
tier: (none — dev infrastructure)
---

# Spec 040: Align README isolation claims with SKILL.md caveat

## Overview

`README.md:14` sells a guarantee the implementation can't deliver:

> Implementers grade their own homework. Sessions routinely end with
> "done" claims over partial work. A fresh subagent with only the spec
> and the diff — no chat history — catches the gaps.

`skills/independent-review/SKILL.md:165–171` is honest about the same
mechanism:

> Implementer writes deliverable to disk → review.py builds a
> self-contained prompt → Claude spawns the reviewer Task with that
> prompt → reviewer reads only what the prompt points at. **This is
> imperfect (parent context is technically accessible to subagents —
> see GitHub issue #20304), but works reliably when the prompt is
> sharp.**

The SKILL.md is honest. The README is overclaiming. The README is the
first thing readers encounter; it sets expectations the implementation
doesn't meet. `docs/workflow.md` does the same when it describes
"three passes via `jig:independent-review`" without the caveat.

## Why now

- **Trust-leverage.** The "independent reviewer catches implementer
  self-grading" framing is one of jig's flagship benefits (per
  `product-vision.md` §The core problem). Anyone evaluating jig
  against alternatives reads that promise. Discovering the caveat
  only after digging into the SKILL.md costs more trust than
  disclosing it up front.
- **Doc-only.** Three files, narrow edits, no code touched, no new
  tests. Single PR.
- **Adjacent to spec 042** (spec-gate model — same theme of
  "framing claims vs. enforcement reality"). Landing both compounds
  the honesty improvement.

## Goals

1. **README.** Rewrite the "Implementers grade their own homework"
   bullet to match the SKILL.md's framing. Keep the practical benefit
   ("fewer self-graded 'done' claims") without overpromising strict
   isolation.
2. **`docs/workflow.md`.** Same alignment in the "Post-implementation
   review" section: fresh-prompt + read-only-tools shape, with the
   parent-context caveat acknowledged briefly.
3. **`docs/product-vision.md`.** The reviewer-isolation wording lives
   in **Design principle #3** (and the Tier-0 skills list) — corrected
   during 040-01 reconciliation; the original draft mis-pointed this at
   "§ The core problem," which carries no isolation framing. The
   *solution* wording is tightened to match the SKILL.md while the
   "defined by isolation" organizing principle is retained.

## Non-goals

- **No re-engineering of the isolation mechanism.** GitHub issue
  #20304 is upstream. jig cannot fix the leak; it can be honest
  about it.
- **No changes to the reviewer agent's tool set.**
  `agents/reviewer.md` already restricts to Read / Glob / Grep —
  that part of the isolation story is real. Leave it.
- **No removal of the multi-perspective review claim.** Spec 031
  shipped; the multi-perspective design is correct and valuable.
  Only the isolation framing is being aligned.
- **No new tests.** Doc work.

## Current state (verified 2026-05-26)

- `README.md:14` — claims "fresh subagent with only the spec and
  the diff — no chat history."
- `docs/workflow.md` — § Post-implementation review describes three
  passes with no caveat.
- `skills/independent-review/SKILL.md:165–171` — has the honest
  caveat naming GitHub issue #20304.
- `agents/reviewer.md` — tools = `Read, Glob, Grep` (read-only;
  enforcement that's real).
- `docs/product-vision.md` — **Design principle #3** (`reviewer
  (read-only, fresh context)`) and the Tier-0 skills list both carry
  an implicit isolation promise. _(Draft originally attributed this to
  "§ The core problem"; corrected during 040-01 reconciliation — that
  section has no isolation framing.)_

## Decomposition

**Suggested SPIDR axis: I (Interface)** primary — three documents to
align. Small enough that one slice covering all three is the natural
shape (matching spec 025-01's precedent for doc sweeps).

### Slices (TBD until clarify runs)

- **Option A (preferred)** — `040-01 isolation-honesty-doc-sweep`:
  README + workflow.md + product-vision.md aligned in one slice.
  Single PR; single review pass.
- **Option B** — split by audience:
  - `040-01 readme-isolation-honesty` (README only — highest reader
    visibility).
  - `040-02 workflow-and-vision-isolation-honesty` (the two `docs/`
    files).

Lean A. Doc sweeps benefit from being a single coherent edit.

## Open questions for `/jig:clarify`

- **Q1.** Is this tone adjustment, or does the framing need
  restructuring? Lean tone. The claim "fresh subagent catches gaps"
  is *true* in practice — the caveat is just that the mechanism is
  "narrow prompt + restrictive tools + behavioral convention,"
  not strict isolation. That story is honest and still compelling.
- **Q2.** Should the README link to GitHub issue #20304? Lean no
  — README stays high-level; SKILL.md carries the technical
  reference. Forward-reference from README → SKILL.md if needed.
- **Q3.** Does the slice need to wait for spec 036's amendment
  convention? `product-vision.md` is a living document, not a
  closed spec, so probably not — but worth confirming the policy
  scope.

## Dependencies / coordination

- **Run after spec 036** (closed-spec drift policy) — the amendment
  convention may apply to `product-vision.md` edits.
- **Coordinate with spec 038** (tier reconciliation) — both edit
  the README. Land in series, not parallel, to avoid adjacent-line
  conflicts.
- **Theme-cluster with spec 042** (spec-gate model). Both align
  framing claims with enforcement reality.

## References

- Historical external review input was folded into this spec; the standalone
  source brief was retired.
- Upstream: [GitHub issue #20304](https://github.com/anthropics/claude-code/issues/20304)
  (parent context reachable to subagents).
- Verification 2026-05-26: README claim and SKILL.md caveat both
  confirmed live as quoted.
