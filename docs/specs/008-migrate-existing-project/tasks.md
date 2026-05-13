# Tasks: Slice 008-01 — migrate-report

> Tasks are DRAFT alongside the spec. Refresh when slice 008-01
> transitions to IN_PROGRESS.

## Ordered tasks (TDD)

- [ ] **T1** — Write `skills/migrate/test_migrate.py` with failing tests
      for all eight AC test classes (`InventoryTests`, `VerdictTests`,
      `MappingTests`, `ConflictTests`, `AmbiguityTests`, `SafetyTests`,
      `SkillSurfaceTests`, `DogfoodTests`).
- [ ] **T2** — Create fixture trees under `skills/migrate/fixtures/`:
      `tiny-validator`, `greenfield`, `partial`, `conflict`. Each is a
      minimal tree exercising one verdict path.
- [ ] **T3** — Implement `skills/migrate/migrate.py` (single `report`
      subcommand via argparse). Read-only filesystem walk; structured
      report writer; verdict logic.
- [ ] **T4** — Write `skills/migrate/SKILL.md` (active frontmatter; five
      trigger phrases per AC #5; references `migrate.py report`).
- [ ] **T5** — Run full suite (`python3 -m unittest discover skills/`).
      Confirm zero regressions across existing tests + new tests.
- [ ] **T6** — Validator dogfood: run `python3 skills/migrate/migrate.py
      report /Users/ramboz/Projects/misc/aso-shallow-validator/`.
      Capture the report's verdict + each section's row count + any
      surprises. Will inform sizing for 008-04.
- [ ] **T7** — Transition status DRAFT → IN_PROGRESS via
      `workflow.py transition`.
- [ ] **T8** — Build implementation-review prompt via `review.py`;
      spawn reviewer.
- [ ] **T9** — Address reviewer findings; add regression tests for any
      real bugs.
- [ ] **T10** — Write deviation log under slice 008-01. MUST include
      the validator-dogfood transcript from T6.
- [ ] **T11** — Transition REVIEWED → RECONCILED via `workflow.py`.
- [ ] **T12** — Build reconciliation-review prompt; spawn reviewer.
- [ ] **T13** — Transition RECONCILED → DONE.
- [ ] **T14** — Regen status board AFTER the DONE transition (006-01
      lesson).
- [ ] **T15** — Update `CLAUDE.md`: hot cache "Active specs" + Skills
      table (add `migrate` row, tier 0) + sprint focus.
- [ ] **T16** — Commit: `feat(migrate): introduce skill with report
      subcommand (slice 008-01)`.
- [ ] **T17** — Self-dogfood the produced validator report by sizing
      slice 008-04 from its Ambiguities section. File any new
      refinement-todo entries discovered during dogfood.
