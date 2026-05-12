# Tasks: Slice 001-04 — deferred-decisions

## Ordered tasks (TDD)

- [ ] **T1** — Extend `test_scaffold.py` with `FormatComplianceTests` + `StocktakeTests`
- [ ] **T2** — Implement `skills/scaffold-init/stocktake.py` (count_reconciled_slices, parse_deferred_items, render_report, main)
- [ ] **T3** — Add a Stocktake section to `templates/docs/workflow.md.template`
- [ ] **T4** — Run tests, fix issues
- [ ] **T5** — Spawn reviewer subagent
- [ ] **T6** — Reconcile, second reviewer pass, commit

## AC → test mapping

| AC | Test |
|---|---|
| #1 entry format consistent | `test_refinement_todo_format_compliance` |
| #2 3 categories | `test_refinement_todo_has_three_categories` |
| #3 stocktake suggests at ≥3 | `test_stocktake_suggests_at_threshold` + `test_stocktake_silent_below_threshold` |
| #3 stocktake works on fresh scaffold | `test_stocktake_runs_on_fresh_scaffold` |

## Deliverable paths

```
skills/scaffold-init/stocktake.py
skills/scaffold-init/test_scaffold.py
templates/docs/workflow.md.template
docs/specs/001-scaffold-init/spec.md
docs/specs/001-scaffold-init/plan.md
docs/specs/001-scaffold-init/tasks.md
docs/specs/README.md
```
