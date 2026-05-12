# Tasks: Slice 002-02 — lookup-pattern

## Ordered tasks (TDD)

- [ ] **T1** — Extend `test_memory.py` with failing `LookupTests`
- [ ] **T2** — Implement `lookup` subcommand in `memory.py`
- [ ] **T3** — Update SKILL.md with the lookup-pattern flow section
- [ ] **T4** — Run tests
- [ ] **T5** — Spawn reviewer subagent
- [ ] **T6** — Reconcile, commit

## AC → test mapping

| AC | Test |
|---|---|
| #1 hot cache checked first | `test_lookup_hot_cache_wins_when_both` |
| #2 glossary fallback | `test_lookup_finds_glossary_term` |
| #3 ask once on miss | SKILL.md flow (no test — Claude behavior) |
| #4 promote on ≥3 | already exists from 002-01; SKILL.md guidance |
| #5 subsequent encounters resolve | `test_lookup_after_add_term_round_trip` |
| #6 decision logged | accepted-as-deviation: stdout = log (see plan.md) |

## Deliverable paths

```
skills/memory-sync/memory.py
skills/memory-sync/test_memory.py
skills/memory-sync/SKILL.md
docs/specs/002-memory-layer/{spec,plan,tasks}.md
docs/specs/README.md
```
