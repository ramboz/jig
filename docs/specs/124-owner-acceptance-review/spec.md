---
status: DONE
skill: spec-workflow
use_cases: [UC-4, UC-7]
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 124: Owner-acceptance review

> Reserved on 2026-11-20 via `workflow.py new --no-push` (local provisional — the
> number is not yet on `origin/main`; 123 is held by another open branch).

## Overview

GitHub issue 254 (`ramboz/jig`): the owner's hands-on check of a UI slice has
no slot in the lifecycle, so projects put it in the Definition of Done (DoD),
which is enforced only at `DONE`, after `RECONCILED`. When the first device
check rejected three UX decisions taken on paper, every review verdict, the
deviation log and the reconciliation documents had to be redone.

This spec adds an optional **owner-review** pass to the batch of reviews that
gate `REVIEWED`. The automated reviewers run, the owner tries the slice at the
same time, and `REVIEWED` waits for all of them. A rejection keeps the slice
`IN_PROGRESS`, before any reconciliation document is written. The pass is
required only when the slice sets `owner_review: true`, and jig asks the owner
for that answer when a slice looks UI-related.

The design is decided in
[ADR-0069](../../decisions/adr-0069-owner-review-human-attested-evidence.md),
including why the issue's `ACCEPTED` state and derived flag were not adopted
and why the existing `design-review` pass (spec 071) is not stretched to cover
this.

## Decisions

- **D1 — a pass, not a state.** `owner-review` joins the `REVIEWED` evidence
  set next to `arch`, `code-health` and `design-review` (ADR-0069 decision 1).
- **D2 — the owner's words.** The record carries what was tried, on what
  surface, and the owner's quoted answer. The agent asks and quotes; it never
  infers a verdict (ADR-0069 decisions 2 and 4).
- **D3 — deliberateness, not proof.** An agent can write the file; the gate
  makes skipping the check a recorded, reviewable act
  ([ADR-0011](../../decisions/adr-0011-spec-gate-model.md), ADR-0069
  decision 3).
- **D4 — explicit flag, asked for.** `owner_review` is `true`, `false` or
  absent. Absent on a UI-related slice triggers the question (ADR-0069
  decisions 7 and 8).
- **D5 — one rejection reopens the batch.** On a flagged slice any
  non-`pass` verdict makes the verdicts recorded so far stale, so an owner
  `pass` cannot outlive a fix it never saw (ADR-0069 decision 6).

The two unverified premises behind this design (an agent-writable record is
a usable deliberateness signal; a word list catches most UI slices) are
tracked in ADR-0069 with their kill criteria, and that ADR gets the
frame-critique pass.

## Non-goals

- No new lifecycle state and no standalone gate.
- No change to the `design-review` pass.
- No owner pass for the bug-fix lifecycle (ADR-0069 open question).
- No detection of "decisions not yet tried" from the files.
- `spec_lint.py` is unchanged: it does not validate the other review flags
  either.

## Assumptions

None.

## Decomposition

SPIDR (Spike / Paths / Interfaces / Data / Rules) analysis:

- **Spike:** none. The flag, gate, verdict file and `session-plan` machinery
  exist and were read before drafting.
- **Paths:** two user paths. (1) A flagged slice is dispatched, the owner is
  asked, the answer is recorded and the gate enforces it. (2) An author
  writes a UI slice and is asked whether the owner wants the check. Each is
  one slice.
- **Interfaces:** the first path touches `review.py`, `workflow.py` and the
  shared evidence module together; splitting it by file would leave a gate
  with no way to satisfy it.
- **Data / Rules:** the UI word list is a rule of the second path only.

## Slices

- [124-01 — owner-review pass](slice-01-owner-review-pass.md)
- [124-02 — authoring question](slice-02-authoring-question.md)
