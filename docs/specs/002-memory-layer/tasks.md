# Tasks: Slice 002-03 — auto-detect-hooks

## Ordered tasks (TDD)

- [ ] **T1** — Create `skills/memory-sync/test_hooks.py` with failing tests
- [ ] **T2** — Tighten `jig-memory-scan.sh` heuristic (strip code blocks, URLs, paths)
- [ ] **T3** — Verify `jig-task-capture.sh` regex covers the common patterns
- [ ] **T4** — Add post-2-week firing-rate measurement to `docs/refinement-todo.md`
- [ ] **T5** — Run tests, fix issues
- [ ] **T6** — Reviewer subagent
- [ ] **T7** — Reconcile, second reviewer pass, commit

## AC → test mapping

| AC | Test |
|---|---|
| #1 jig-memory-scan catches unknowns | `test_flags_unknown_acronym`, `test_flags_unknown_camelcase` |
| #1 + #4 well-formed additionalContext | `test_output_is_well_formed_json` |
| #2 jig-task-capture catches task-language | `test_flags_we_should_also`, `test_flags_todo_marker`, etc. |
| #3 both non-blocking | `test_exits_0_always` (both hooks) |
| #5 firing-rate health | deferred — see refinement-todo (no telemetry yet) |

## Deliverable paths

```
hooks/scripts/jig-memory-scan.sh
hooks/scripts/jig-task-capture.sh
skills/memory-sync/test_hooks.py
docs/refinement-todo.md
docs/specs/002-memory-layer/{spec,plan,tasks}.md
docs/specs/README.md
```
