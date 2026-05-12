# Plan: Slice 002-04 — reconciliation-integration

## Approach

The cheapest, most honest slice in spec 002. Two file edits and a verification test:

1. **`agents/reviewer.md`** — add an explicit prohibition on writing to `docs/memory/` so the reviewer subagent doesn't try to define the glossary. This is a one-line addition to the system-prompt "What you must NOT do" section.

2. **`skills/spec-workflow/SKILL.md`** — currently a stub with `disable-model-invocation: true`. We embed the reconciliation-checklist content (including the memory-sync prompt) **now** so that when spec-workflow is promoted to a real skill (future spec 003+), the integration is already specified. This is "encode in stub form, activate later" — matches how slice 001-04 closed the loop with stocktake while spec-workflow remained a stub.

3. **Tests** — static-content assertions in `test_memory.py` confirming:
   - `agents/reviewer.md` contains an explicit "do not write to docs/memory/" line
   - `skills/spec-workflow/SKILL.md` contains a reconciliation-checklist that mentions memory-sync

## "Encode now, activate later" rationale

AC #1 literally says "spec-workflow includes a memory-sync prompt in reconciliation checklist." If we wait until spec-workflow is promoted to ship 002-04, this slice blocks indefinitely. The honest path: write the content into the stub SKILL.md so when spec-workflow becomes real, the integration is part of its first turn. The stub still shows a DRAFT warning when invoked; the content waits for promotion.

This is consistent with how scaffolded docs work (Draft → Stable). The integration's *behavior* is gated on spec-workflow becoming user-invocable, but its *content* is in place.

## Files to modify

| Path | Change |
|---|---|
| `agents/reviewer.md` | Add a one-line "do not write to docs/memory/" prohibition |
| `skills/spec-workflow/SKILL.md` | Embed reconciliation-checklist content with memory-sync step |
| `skills/memory-sync/test_memory.py` | NEW `IntegrationTests` class — static-content checks |
| `docs/specs/002-memory-layer/spec.md` | Status: DRAFT → IN_PROGRESS → DONE |
| `docs/specs/README.md` | Status update |
| `CLAUDE.md` | Reflect spec 002 complete |

## Test strategy

`IntegrationTests`:
- `test_reviewer_agent_forbids_writing_to_memory` — grep `agents/reviewer.md` for the prohibition
- `test_spec_workflow_includes_memory_sync_in_reconciliation` — grep `skills/spec-workflow/SKILL.md` for the integration

These are static-content tests, the cheapest form. They guard against future edits silently removing the integration.

## Out of scope

- Promoting spec-workflow from stub to real skill → future spec (003+ recommended).
- Mechanism that automatically surfaces new domain terms during reconciliation — Claude judgment, per the broader memory-sync pattern.
