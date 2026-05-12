# Tasks: Slice 002-01 — explicit-sync

## Ordered tasks (TDD)

- [ ] **T1** — Create `skills/memory-sync/test_memory.py` with failing tests
- [ ] **T2** — Implement `skills/memory-sync/memory.py` (CLI + helpers)
- [ ] **T3** — Self-healing for missing memory dirs
- [ ] **T4** — Update `skills/memory-sync/SKILL.md` with invocation flow
- [ ] **T5** — Run tests, fix issues
- [ ] **T6** — Spawn reviewer subagent
- [ ] **T7** — Reconcile, second reviewer pass, commit

## AC → test mapping

| AC | Test |
|---|---|
| #1 summary of changes | `test_summary_lists_counts` |
| #2 new glossary terms | `test_add_term_appends_to_glossary` |
| #3 new learnings | `test_add_learning_*` |
| #4 high-freq terms promoted | `test_promote_writes_to_hot_cache` |
| #5 unresolved → inbox | `test_add_inbox_dates_entry` |
| #6 self-heal missing memory dir | `test_creates_memory_dir_if_missing`, `test_creates_inbox_md_if_missing` |

## Deliverable paths

```
skills/memory-sync/memory.py
skills/memory-sync/test_memory.py
skills/memory-sync/SKILL.md
docs/specs/002-memory-layer/{spec,plan,tasks}.md
docs/specs/README.md
```
