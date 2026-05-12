# Tasks: Slice 002-04 — reconciliation-integration

## Ordered tasks

- [ ] **T1** — Add `IntegrationTests` class to `skills/memory-sync/test_memory.py` (failing tests)
- [ ] **T2** — Edit `agents/reviewer.md` — add "do not write to docs/memory/" prohibition
- [ ] **T3** — Edit `skills/spec-workflow/SKILL.md` — embed reconciliation checklist with memory-sync step
- [ ] **T4** — Run tests
- [ ] **T5** — Reviewer subagent
- [ ] **T6** — Reconcile + commit

## AC → test mapping

| AC | Test |
|---|---|
| #1 spec-workflow has memory-sync in reconciliation | `test_spec_workflow_includes_memory_sync_in_reconciliation` |
| #2 reviewer forbids memory writes | `test_reviewer_agent_forbids_writing_to_memory` |
| #3 new terms surfaced during reconciliation | covered by SKILL.md content + #1's test |

## Deliverable paths

```
agents/reviewer.md
skills/spec-workflow/SKILL.md
skills/memory-sync/test_memory.py
docs/specs/002-memory-layer/{spec,plan,tasks}.md
docs/specs/README.md
CLAUDE.md
```
