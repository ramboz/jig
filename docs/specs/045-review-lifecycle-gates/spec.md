---
status: DONE
skill: spec-workflow, independent-review
tier: dev infrastructure
adr_required: true
---

# Spec 045: Review lifecycle evidence and gates

## Overview

jig's workflow documentation presents post-implementation review and
reconciliation as load-bearing gates. The current implementation does
not make those gates machine-checkable. `review.py` builds prompts but
does not create durable verdict evidence; `workflow.py transition`
mostly accepts requested status changes; the Stop hook named in
`docs/workflow.md` is actually a TODO/task-capture hook; and the
implementer agent instructions still say to move work to `REVIEWED`.

That gap matters because jig is a workflow product. If the lifecycle
claims are stronger than the lifecycle mechanics, users learn to trust
ritual text instead of evidence. This spec turns review and
reconciliation into explicit artifacts that `workflow.py` can validate,
while keeping the reviewer judgment human/agent-authored rather than
pretending a Python helper can perform the review.

## Goals

1. **Decide the evidence model via ADR.** Define what counts as review
   evidence, where it lives, how verdicts are represented, which passes
   are required, and which lifecycle transitions are blocked without
   evidence.
2. **Add a durable review-artifact path.** Provide a small helper flow
   for recording and validating implementation, craft, optional arch,
   and reconciliation review verdicts for a slice. The artifact should
   be readable in code review and stable enough for future automation.
3. **Gate lifecycle transitions.** `workflow.py transition` should
   refuse status moves that claim review or reconciliation completion
   unless the required evidence exists and passes schema checks.
4. **Align the agent and docs contract.** Update implementer guidance,
   workflow docs, and any hook claims so the user-facing process matches
   what the code can actually enforce.
5. **Preserve manual judgment.** The helper validates evidence shape and
   declared verdicts. It does not try to decide whether the review was
   good.

## Non-goals

- **No automatic subagent spawning.** The current host does not expose a
  portable, scriptable subagent API. The implementation records results
  produced by the reviewer flow; it does not replace the reviewer.
- **No human-authentication claim.** This spec may block inconsistent
  lifecycle transitions, but it cannot prove that a human personally
  approved a verdict.
- **No CI-only enforcement.** Local workflow helpers stay the source of
  truth. CI can call them later, but this spec does not require a CI
  redesign.
- **No rewrite of the entire spec lifecycle.** The scope is the review
  and reconciliation evidence around existing statuses.

## Current state verified 2026-05-27

- `docs/workflow.md` says the Stop hook blocks completion when
  reconciliation has not happened.
- `hooks/scripts/jig-task-capture.sh` is a task-capture hook, not a
  reconciliation gate.
- `skills/independent-review/review.py` constructs standardized prompts
  and explicitly does not spawn subagents.
- `skills/spec-workflow/workflow.py transition` validates only a small
  subset of lifecycle rules and does not check review artifacts.
- `agents/implementer.md` still instructs the implementer to write a
  review queue entry and update status to `REVIEWED`.

## Decomposition

**Suggested SPIDR axis: Rules.** The main design question is "what
counts as completed review?" Once that rule is settled, the code changes
are straightforward validator and transition work.

### Slices

1. **`045-01 review-evidence-adr`** - ADR for the evidence contract,
   storage path, verdict schema, required passes, transition map, and
   hook/docs stance.
2. **`045-02 review-artifact-recorder`** - Add schema validation and a
   helper command for recording/checking review evidence for one slice.
3. **`045-03 lifecycle-transition-gates`** - Make `workflow.py
   transition` enforce evidence before `REVIEWED`, `RECONCILED`, and
   `DONE`.
4. **`045-04 workflow-contract-alignment`** - Align docs, implementer
   instructions, hook wording, tests, and status-board notes with the
   enforced lifecycle.

## Open questions for implementation

> **Resolved** by [ADR-0014](../../decisions/adr-0014-review-evidence-model.md)
> (slice 045-01) — see its Recommended Decision §1–§6. Retained below for
> provenance: per-spec `reviews/` dir; `REVIEWED` = compliance + craft
> (+ arch if flagged); reconciliation verdict is separate from the
> deviation log; a failed verdict blocks (latest-pass supersedes).

- Should review evidence live beside the slice as
  `reviews/<pass>.md`, in a single `review.md`, or in a generated
  `.jig/reviews/` ledger?
- Does `REVIEWED` require only the compliance pass, or compliance plus
  craft pass because spec 031 made craft review unconditional?
- Should reconciliation evidence be separate from the deviation log, or
  can the deviation log contain the final reconciliation verdict?
- Should a failed review verdict block transition outright, or should
  the failure be recorded and require a later pass artifact?

## References

- [docs/workflow.md](../../workflow.md)
- [agents/implementer.md](../../../agents/implementer.md)
- [skills/independent-review/review.py](../../../skills/independent-review/review.py)
- [skills/spec-workflow/workflow.py](../../../skills/spec-workflow/workflow.py)
- [hooks/scripts/jig-task-capture.sh](../../../hooks/scripts/jig-task-capture.sh)
