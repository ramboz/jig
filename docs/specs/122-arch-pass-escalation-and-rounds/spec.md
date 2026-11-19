---
status: DONE
skill: independent-review
use_cases: [UC-4, UC-7]
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 122: Arch-pass escalation and rounds

> Reserved on 2026-11-17 via `workflow.py new --no-push` (local provisional — the
> number is not yet on `origin/main`).

## Overview

The arch pass (`review.py arch-review`, run when a slice declares
`arch_review: true`) hands a read-only `reviewer` subagent the slice and its
deliverables, and the reviewer answers in jig's `VERDICT / REASONING / SPECIFIC
ISSUES / RECONCILIATION NOTES` envelope. A richer, user-installed `arch-review`
skill is being redesigned to map its findings onto that envelope by a fixed
rule. Two parts of that rule need jig to act, and a third exposes a
contradiction inside jig:

1. **Decisions only a person can make have nowhere to go.** A duplicated
   path, effort past what the plan states, a slice tied to no goal line, or a
   hard-to-reverse choice is not something the implementer should "fix". The
   redesigned skill reports it as `VERDICT: fail` with a `[blocker]` entry whose
   description starts with `ESCALATE:`. Today jig's recovery text says to
   address every finding and re-run the pass, so an autonomous orchestrator
   makes the person's decision itself.
2. **Rounds don't carry over.** The verdict record for each `(slice, pass)` is
   overwritten in place (ADR-0014 §4), and the reviewer prompt says it is
   "seeing this work for the first time" and must "not refer to any prior
   reasoning". A later round cannot say which earlier findings were fixed, so
   repeated rounds keep finding a new blocker. That ban was written to keep the
   implementer's conversation out of the review; the previous record on disk is
   evidence, not conversation.
3. **The two blocking rules disagree.** The gate (`_common/review_evidence.py`,
   `verdict_clears`) clears only `verdict: pass`, as ADR-0014 §3 decides. The
   live prose in `spec-workflow/SKILL.md`, `independent-review/SKILL.md` and
   `docs/workflow.md` says a craft/arch `needs-changes` with no `[blocker]` does
   not block. ADR-0014 §3 already resolves this with an *authoring* rule: a
   craft/arch review whose findings are only `[nit]`/`[strength]` is recorded as
   `pass`. The prose and the reviewer prompt drifted from it.

## Decisions

- **D1 — One blocking rule: only `pass` clears (owner's choice, 2026-11-17).**
  Keep the gate. Make the docs and the reviewer prompt state ADR-0014 §3's
  authoring rule. No ADR change: this restores conformance with an accepted
  ADR.
- **D2 — Escalation reuses existing surfaces.** The orchestrator parks each
  escalated decision with the existing `memory.py add-inbox` and marks the slice
  with the existing `blocked_by:` annotation (ADR-0057). jig's code adds one
  shared parser and uses it at the two points an orchestrator passes through:
  `record-review` (a stop notice) and the evidence gate (a diagnostic that says
  "a person decides" instead of "re-run the review"). No new lifecycle state, no
  new command.
- **D3 — Round carry-over is arch-only and on disk only.** Only the arch pass
  gets the carve-out, and only for its own previous record
  (`reviews/slice-NN-arch.md`), read after the reviewer has reviewed the current
  deliverables. The ban on conversation context and the implementer's reasoning
  stays for every pass.

## Assumptions

- **A1 — a verdict record always has a body (grounded).** `record-review`
  refuses a verdict without `--summary-file` (`review.py`, bug 017), so the
  `SPECIFIC ISSUES` section of a recorded envelope is readable from disk.
- **A2 — nothing consumes `blocked_by:` except the status board (grounded).**
  `grep -rn blocked_by skills/*/*.py` → only `workflow.py` reads it, to render
  `## Blocked slices`. Setting it does not change any transition.
- **A3 — the redesigned skill's line formats (external, not grounded here).**
  The `ESCALATE: <decision> (options A, B)` entry and the
  `round: N · open: <ids> · searched: <anchors>` line come from the
  arch-review redesign (the owner's dotfiles repo, branch
  `claude/arch-review-redesign-bc9ca8`, `docs/arch-review-redesign/proposal.md`
  §9.5). jig parses the `ESCALATE:` prefix leniently and does not parse the
  round line (the reviewer reads it), so a wording change there does not break
  jig.

## Decomposition

Three independent vertical slices, each usable on its own:

- **122-01 (Rules):** an arch verdict carrying `[blocker] ESCALATE:` entries
  stops the slice for a person and parks the decision in `docs/inbox.md`.
- **122-02 (Interfaces):** the arch-pass prompt lets the reviewer read the
  slice's previous arch record from disk and carry its findings forward.
- **122-03 (Rules):** the docs and the reviewer prompt state the single
  blocking rule the gate enforces.

## Slices

- [122-01 — escalate-stops-the-slice](slice-01-escalate-stops-the-slice.md)
- [122-02 — arch-round-carry-over](slice-02-arch-round-carry-over.md)
- [122-03 — one-blocking-rule](slice-03-one-blocking-rule.md)
