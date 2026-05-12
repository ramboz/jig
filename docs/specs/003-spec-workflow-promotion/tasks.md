# Tasks: Slice 003-01 — lifecycle-helper

## Ordered tasks (TDD)

- [ ] **T1** — Create `skills/spec-workflow/test_workflow.py` with failing tests
- [ ] **T2** — Implement `skills/spec-workflow/workflow.py` (transition + status-board)
- [ ] **T3** — Rewrite `skills/spec-workflow/SKILL.md` — flip stub → active, preserve memory-sync integration
- [ ] **T4** — Run tests; dogfood `transition` against jig's own spec.md files
- [ ] **T5** — Reviewer subagent
- [ ] **T6** — Reconcile, second reviewer pass, commit

## AC → test mapping

| AC | Test |
|---|---|
| #1 transition mutates spec.md correctly | `test_transition_updates_status`, `test_transition_refuses_invalid_status`, `test_transition_refuses_unknown_slice` |
| #2 status-board regenerates README.md table | `test_status_board_regenerates_table`, `test_status_board_idempotent` |
| #3 SKILL.md frontmatter promoted | `test_skill_frontmatter_no_disable_invocation` |
| #4 SKILL.md body active | `test_skill_body_no_stub_banner` |
| #5 memory-sync integration intact | existing `IntegrationTests` in `test_memory.py` (no regression) |
| #6 slash command still works | covered by frontmatter test (`user-invocable: true`) |

## Deliverable paths

```
skills/spec-workflow/workflow.py
skills/spec-workflow/test_workflow.py
skills/spec-workflow/SKILL.md
docs/specs/003-spec-workflow-promotion/{spec,plan,tasks}.md
docs/specs/README.md
```
