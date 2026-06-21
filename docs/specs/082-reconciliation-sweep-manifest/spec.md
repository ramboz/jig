---
status: IN_PROGRESS
skill: spec-workflow
use_cases: []
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 082: Reconciliation-sweep manifest

> Reserved on 2026-06-21 via `workflow.py new`.

## Overview

Reconciliation is the moment when jig knows what actually changed, what the
reviewer accepted, and which documentation surfaces need to catch up. The
current reconciliation checklist already assigns cleanup work to that phase,
but only part of it is mechanically visible: `workflow.py transition` gates on
review evidence plus the presence of a deviation log, while the rest of the
cleanup checklist relies on agent memory.

That leaves a recurring drift vector:

- live front-door summaries (`README.md`, `docs/product-vision.md`,
  `docs/architecture.md`) fall behind the state expressed in specs, ADRs, or
  helpers;
- hot primers (`CLAUDE.md`, and `AGENTS.md` on the v2 branch) retain historical
  implementation detail that should have been compressed into the status
  board, memory, or the completed spec;
- `docs/inbox.md` and `docs/refinement-todo.md` keep items that landed work has
  already resolved, or keep stale triggers after the cleanup happened elsewhere;
- reconciliation reviewers verify the deviation-log claims they can see, but
  do not have a structured way to ask "what did the implementer forget to
  sweep?"

This spec implements [ADR-0029](../../decisions/adr-0029-reconciliation-sweep-manifest.md):
every reconciled slice must include a compact **reconciliation sweep manifest**
that records the disposition of the drift-prone surfaces. The helper enforces
the presence of the manifest; the reviewer judges whether the artifact coverage
and `updated` / `no-op` / `deferred` rationales are honest.

## Goals

1. **Make cleanup inspectable.** A reconciled slice names which core docs,
   primers, queues, memory files, and ADR indexes were updated, checked as
   no-op, or deliberately deferred.
2. **Catch omissions without noisy churn.** The transition gate should not
   require every artifact to be edited. It should require the sweep section so
   omissions become reviewable.
3. **Broaden primer hygiene.** Replace the Claude-only cleanup framing with
   host-portable primer hygiene that covers `CLAUDE.md`, `AGENTS.md`, and the
   scaffold templates when present.
4. **Give queues a real close-out pass.** `docs/inbox.md` and
   `docs/refinement-todo.md` must be explicitly triaged during reconciliation,
   especially for items resolved by the current spec or by earlier cleanup.
5. **Preserve jig's gate boundary.** Deterministic code checks shape and
   presence; reviewer judgment checks semantic honesty.

## Non-goals

- **No semantic doc-freshness oracle.** This spec does not try to prove that
  product vision, architecture, README, or primers are fully current.
- **No requirement to touch every file.** `no-op` is a valid disposition when
  the slice does not affect an artifact.
- **No queue-format redesign.** Existing strike-through, memory promotion, and
  deferred-trigger styles remain valid.
- **No implementation of the cleanup itself in this planning slice.** The
  slices below define the work; later implementation will mutate the helper,
  prompts, templates, and docs.

## Assumptions

- `workflow.py transition` currently gates `RECONCILED` on recorded
  reconciliation evidence and deviation-log presence, not on each checklist
  item. Verified by reading `skills/spec-workflow/workflow.py` on
  2026-06-21.
- `review.py build_reconciliation_prompt` currently asks the reviewer to
  verify deviation-log claims and scope, but it does not enumerate the
  front-door docs, primers, queues, or memory surfaces as a required omission
  check. Verified by reading `skills/independent-review/review.py` on
  2026-06-21.

## Decomposition

SPIDR split: **Rules**, then **Interface**.

1. The lifecycle rule changes first: define the manifest body shape and teach
   the transition gate/template to require it.
2. The reviewer interface changes next: reconciliation review must inspect the
   manifest for omissions and weak rationales.
3. The surrounding docs and queues change last: rename `CLAUDE.md hygiene` to
   primer hygiene, document the sweep, and clean up any already-resolved queue
   items exposed by this spec.

## Slices

- [082-01 — manifest shape and transition gate](slice-01-manifest-shape-and-transition-gate.md)
- [082-02 — reconciliation reviewer omission check](slice-02-reviewer-omission-check.md)
- [082-03 — primer and queue cleanup integration](slice-03-primer-and-queue-cleanup-integration.md)

## References

- [ADR-0029: Reconciliation sweep manifest](../../decisions/adr-0029-reconciliation-sweep-manifest.md)
- [ADR-0014: Review-evidence model](../../decisions/adr-0014-review-evidence-model.md)
- [ADR-0010: Amendment scope — records vs. live prose](../../decisions/adr-0010-amendment-scope-records-vs-live-prose.md)
- [Spec 025: CLAUDE.md hygiene](../025-claude-md-hygiene/spec.md)
