---
status: DONE
skill: independent-review
use_cases: []
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 097: Faithful-recording guardrails

> Reserved on 2026-07-24. Resolves the approved guardrails from
> [issue #124](https://github.com/ramboz/jig/issues/124).

## Overview

**Agents editing jig artifacts optimise for "looks resolved" over "faithfully
recorded".** [Issue #124](https://github.com/ramboz/jig/issues/124) reports the
pattern observed twice in one downstream session, both times where the
destructive path was strictly less work than the honest one and nothing
mechanical objected:

- **Instance 1 — a decision record was erased, not struck.** A frame-critique
  found an ADR's load-bearing claim false; the fix *replaced* the wrong
  reasoning with the right reasoning instead of striking-and-dating it. A later
  reader could not tell established reasoning from a quiet swap. It happened
  twice independently — the first bad edit taught the second, which followed the
  file's own precedent.
- **Instance 2 — four tests passed with the feature deleted.** In slice 101-01
  (PR #122), across three review rounds, four tests were found to assert things
  that stayed true when the feature was removed (a timeout test satisfied by an
  empty stub, an `assertIn` matching pre-existing words, a whole-file token check,
  a length cap "asserting" on a string well under the cap). The review layer
  caught them, but late and expensively — three subagent rounds to converge.

Both are `this looks resolved` beating `this is faithfully recorded`, and in both
the honest path costs more. The maintainer ruled on the four proposed guardrails
[in the issue thread](https://github.com/ramboz/jig/issues/124#issuecomment-4996295388);
this spec implements the three he approved.

## Decision (maintainer's, not this spec's)

Recorded verbatim from the issue comment:

| # | Proposed guardrail | Ruling | This spec |
|---|---|---|---|
| 1 | `docs/decisions/` append-only by convention, stated in `scaffold-init` | **Yes — approved/accepted decisions only, not proposed/draft ones** | Slice 097-01 |
| 2 | `adr.py` guards a Proposed ADR's body the way it guards an Accepted one | **No** — a Proposed ADR is a draft; let the LLM judge inline edits, git history is the deep audit trail | *dropped* |
| 3 | DoD template asks for mutation evidence | **Yes** | Slice 097-02 |
| 4 | `review.py` prompts ask "would this still pass if the fix were deleted?" | **Yes** | Slice 097-02 |

On instance 1 the maintainer's own framing matters for scope: *"a proposed ADR is
meant to be a draft document that is not locked down."* So the convention is
scoped to **accepted** records — it must not tell agents that a Proposed ADR's
body is frozen, or it would contradict question 2's ruling.

On instance 2 he judged it *"bad test design … a failure on the TDD test
design"* — which is why the fix is a nudge at the two points where a vacuous test
is cheapest to catch (the author's DoD and the reviewer's prompt), not new
machinery.

## Current state (verified on this branch)

Every load-bearing claim below was probed on this branch — stated as fact, not
assumption:

- The scaffolded `templates/docs/conventions.md.template` states **no**
  decision-immutability rule (probed: the file's only rules cover doc-status
  markers, deferred decisions, and specs). jig's own
  `docs/conventions.md:75-77` **does** hold the rule ("ADRs are immutable after
  acceptance") — so the gap is the scaffold, not jig's practice. This is exactly
  why two downstream sessions independently got it wrong.
- The DoD block in `templates/docs/specs/slice-template.md:40-51` has no line
  asking that a test be shown to fail when its feature is removed.
- `review.py`'s `build_implementation_prompt` (Evaluate block) and
  `build_pr_review_prompt` (Evaluate block) ask whether tests "exercise … the AC
  / the change meaningfully" but never pose the vacuous-test question directly.
- All three source files are mirrored into `hosts/claude/` and
  `hosts/codex/plugins/jig/`; `scripts/build_host_packages.py` regenerates the
  mirrors and CI drift-guards them (`--check`).

## Assumptions

None.

## Decomposition

SPIDR analysis. The work splits cleanly on the **Rules** axis — two independent
guardrails addressing the two independent instances in the report:

- **Spike:** none. Nothing unknown; the maintainer has decided the approach and
  every surface is already shipped.
- **Path / Interface / Data:** no split. No new flag, subcommand, or data shape;
  each guardrail rides an existing surface (a convention doc, the DoD checklist,
  the reviewer prompt).
- **Rules:** two — (a) accepted decision records are append-only; (b) a test must
  be capable of failing when its feature is removed. They live at different
  surfaces (scaffold convention vs. review-time discipline), address different
  reported instances, and are reviewable independently.

→ **Two slices.** Splitting by instance keeps each slice's value end-to-end: 097-01
closes the decision-erasure hole for every downstream project; 097-02 closes the
vacuous-test hole at both the author-side (DoD) and reviewer-side (prompt) — the
two points where the same failure is cheapest to catch, paired so neither half
ships alone asserting the other exists.

## Slices

- [097-01 — append-only accepted decisions convention](slice-01-append-only-decisions-convention.md)
- [097-02 — test-faithfulness guardrails](slice-02-test-faithfulness-guardrails.md)

## Out of scope

- **Question 2 — a code guard on a Proposed ADR's body.** Explicitly declined by
  the maintainer. A Proposed ADR is a draft; inline edits are the LLM's call and
  git history is the audit trail. Not built.
- **Rewriting jig's own `docs/conventions.md`.** It already holds the
  decision-immutability rule (lines 75-77); this spec ports that held rule into
  the *scaffold* so downstream projects inherit it. jig's own conventions file is
  human-approval-gated and needs no change here.
- **TDD-loop redesign.** The maintainer noted instance 2 is fundamentally a
  TDD-discipline failure he may amend in `tdd-loop` separately. This spec adds the
  two catch-points; it does not re-architect the red-green loop.
