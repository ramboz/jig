---
status: DONE
skill: spec-workflow
use_cases: [UC-4, UC-5, UC-7]
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 118: Behavioral verification pilot

> Locally reserved on 2026-10-05 with `workflow.py new --no-push`.
> The number is provisional until integration; no remote reservation is claimed.

## Overview

The owner requested a bounded adoption of two practices from the supplied SDD
(spec-driven development) article: explicit state/role/operation rules and
reproducible acceptance scenarios with observed runtime evidence. A passing
suite and a favorable review can still miss an unstated interaction or break an
existing user journey.

Jig already asks for observable acceptance criteria (ACs), AC-covering fixtures,
independent review, and reconciliation
([slice template](../../../templates/docs/specs/slice-template.md)).
Its compliance prompt evaluates tests and ACs
([review.py](../../../skills/independent-review/review.py)), and its
`design_review` pass already attests external design-evaluation evidence.
This pilot strengthens authoring and compliance review on those existing rails.

## Scope

- Optional behavioral rules and verification scenario sections in the existing
  slice template, with proportional applicability guidance.
- Authoring guidance in `spec-workflow`, ambiguity checks in `clarify`, and a
  bounded conditional-content nudge in the compliance prompt.
- One runnable jig-native worked example, source tests, live documentation, and
  regenerated Claude, Codex, and Copilot packages.

**Non-goals:** no new skill, lifecycle state, gate, frontmatter field, parser,
runner, wiki sync, authentication system, or universal end-to-end test mandate.
No changes to accepted ADRs, closed specs, or `docs/conventions.md`. A demo
scenario does not supersede the ACs; rule numbering does not resolve conflicts.
The existing optional design-evaluation rail remains unchanged.

## Approach

Keep behavioral rules adjacent to their owning ACs or link an existing contract
rather than duplicating requirements. Stable rule IDs provide traceability,
never precedence. Runtime scenarios name setup, steps, expected outcomes,
preserved behavior, and the invocation; evidence records actual observations,
outcomes, and the exercised code revision (including dirty changes when present).
Missing environment access is not a pass. A required AC remains unmet without
its necessary verification, but omission of these optional sections alone does
not create a blocker.

Use the existing project test command and host-specific tools where appropriate.
Jig describes the evidence; the project owns execution and credentials.
External references, when present, name authority and revision; contradictions
are surfaced rather than resolved by recency or document order.

## Assumptions

None.

## Decomposition

**SPIDR (Spike / Paths / Interfaces / Data / Rules): Rules.** One bounded vertical
slice follows the author's behavioral contract through clarification, scenario
execution, and compliance review. Separating templates from their consuming
prompts would leave an incomplete author-to-review path; no Spike is needed.

## Evaluation

Dogfood the optional sections in this slice and run the worked example against
the real helper in an isolated local fixture. Record pass/fail per step and a
preservation observation. This establishes that the guidance is usable, not a
population-level reduction in defects. A later real-project review can evaluate
omitted state rules caught, broken journeys caught, and authoring/execution cost
before considering stronger enforcement.

## Slices

- [118-01 — author-to-review](slice-01-author-to-review.md)
