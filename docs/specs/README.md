# Spec Status Board

> Current state of all specs. Maintained by `workflow.py status-board` — re-run
> any time to sync with `docs/specs/*/spec.md`. The Notes column is preserved
> across regen, so curate it freely.

| Spec | Slice | Status | Notes |
|------|-------|--------|-------|
| [001-scaffold-init](001-scaffold-init/spec.md) | 001-01 — greenfield-scaffold | **DONE** | 14 tests green; reviewed + reconciled |
| [001-scaffold-init](001-scaffold-init/spec.md) | 001-02 — doc-content | **DONE** | 22 tests green; reviewed + reconciled |
| [001-scaffold-init](001-scaffold-init/spec.md) | 001-03 — signal-detection | **DONE** | 39 tests green; reviewed + reconciled |
| [001-scaffold-init](001-scaffold-init/spec.md) | 001-04 — deferred-decisions | **DONE** | 47 tests green; stocktake helper |
| [001-scaffold-init](001-scaffold-init/spec.md) | 001-05 — wizard-qa | **DONE** | 62 tests green; spec 001 complete |
| [002-memory-layer](002-memory-layer/spec.md) | 002-01 — explicit-sync | **DONE** | memory.py helper; 14 tests |
| [002-memory-layer](002-memory-layer/spec.md) | 002-02 — lookup-pattern | **DONE** | lookup subcommand; 21 tests |
| [002-memory-layer](002-memory-layer/spec.md) | 002-03 — auto-detect-hooks | **DONE** | 19 hook tests; firing-rate measurement deferred |
| [002-memory-layer](002-memory-layer/spec.md) | 002-04 — reconciliation-integration | **DONE** | spec 002 complete |
| [003-spec-workflow-promotion](003-spec-workflow-promotion/spec.md) | 003-01 — lifecycle-helper | **DONE** | 16 workflow tests green; spec-workflow promoted |
| [003-spec-workflow-promotion](003-spec-workflow-promotion/spec.md) | 003-02 — anti-horizontal-phasing-check | DRAFT | Deferred this session |
| [003-spec-workflow-promotion](003-spec-workflow-promotion/spec.md) | 003-03 — new-spec-scaffolding | DRAFT | Deferred this session |
| [004-independent-review-promotion](004-independent-review-promotion/spec.md) | 004-01 — review-helper | **DONE** |  |
| [005-adr-workflow](005-adr-workflow/spec.md) | 005-01 — adr-helper | **DONE** | 46 tests green; first Tier 1 skill — adr-workflow active |
| [005-adr-workflow](005-adr-workflow/spec.md) | 005-02 — supersede | DRAFT | Deferred; no real supersede yet |
| [005-adr-workflow](005-adr-workflow/spec.md) | 005-03 — boundary-change-detection | DRAFT | Deferred; blocked on contracts |
| [006-tdd-loop](006-tdd-loop/spec.md) | 006-01 — tdd-helper | **DONE** | 25 tests (23 pass + 2 pytest-skipped); detect + run with normalized exit codes |
| [006-tdd-loop](006-tdd-loop/spec.md) | 006-02 — ac-coverage | DRAFT | Deferred; needs test-tagging convention |
| [006-tdd-loop](006-tdd-loop/spec.md) | 006-03 — pre-commit-gate | DRAFT | Deferred; no missing-coverage incident yet |
| [007-slice-land](007-slice-land/spec.md) | 007-01 — land-prepare | **DONE** | 31 tests (30 pass + 1 pytest-skipped); landing-readiness report + direct/pr next-steps |
| [007-slice-land](007-slice-land/spec.md) | 007-02 — direct-mode-execute | DRAFT | Deferred; destructive git ops need safety review |
| [007-slice-land](007-slice-land/spec.md) | 007-03 — pr-mode-execute | DRAFT | Deferred; gated on pr-review design |
| [007-slice-land](007-slice-land/spec.md) | 007-04 — scaffold-json-integration-flag | DRAFT | Deferred; --mode flag is sufficient for now |
| [008-migrate-existing-project](008-migrate-existing-project/spec.md) | 008-01 — migrate-report | **DONE** |  |
| [008-migrate-existing-project](008-migrate-existing-project/spec.md) | 008-02 — rename-decisions | **DONE** |  |
| [008-migrate-existing-project](008-migrate-existing-project/spec.md) | 008-03 — jig-self-migration | **DONE** |  |
| [008-migrate-existing-project](008-migrate-existing-project/spec.md) | 008-04 — slice-to-spec-mapping | DRAFT |  |
| [008-migrate-existing-project](008-migrate-existing-project/spec.md) | 008-05 — scaffold-init --migrate suggestion | DRAFT |  |
| [009-dod-close-out-separation](009-dod-close-out-separation/spec.md) | 009-01 — close-out-section-recognition | **DONE** |  |
