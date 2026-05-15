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
| [003-spec-workflow-promotion](003-spec-workflow-promotion/spec.md) | 003-04 — auto-tick-review-passed-on-transition | **DONE** | 9 new tests (371 total); transition auto-ticks review-passed boxes — pre-tick anti-pattern fixed structurally |
| [004-independent-review-promotion](004-independent-review-promotion/spec.md) | 004-01 — review-helper | **DONE** |  |
| [005-adr-workflow](005-adr-workflow/spec.md) | 005-01 — adr-helper | **DONE** | 46 tests green; first Tier 1 skill — adr-workflow active |
| [005-adr-workflow](005-adr-workflow/spec.md) | 005-02 — supersede | DRAFT | Deferred; no real supersede yet |
| [005-adr-workflow](005-adr-workflow/spec.md) | 005-03 — boundary-change-detection | DRAFT | Deferred; blocked on contracts |
| [006-tdd-loop](006-tdd-loop/spec.md) | 006-01 — tdd-helper | **DONE** | 25 tests (23 pass + 2 pytest-skipped); detect + run with normalized exit codes |
| [006-tdd-loop](006-tdd-loop/spec.md) | 006-02 — ac-coverage | DRAFT | Deferred; needs test-tagging convention |
| [006-tdd-loop](006-tdd-loop/spec.md) | 006-03 — pre-commit-gate | DRAFT | Deferred; no missing-coverage incident yet |
| [006-tdd-loop](006-tdd-loop/spec.md) | 006-04 — missing-module-exit-code | **DONE** | 5 new tests (44 tdd-loop total); `No module named pytest` → exit 2 via `_is_module_importable` preflight |
| [006-tdd-loop](006-tdd-loop/spec.md) | 006-05 — custom-test-command | **DONE** | 14 new tests (44 tdd-loop total); `.jig/test-command` override + `scripts/run_tests.py`; `tdd.py run .` now runs jig's full 461-test suite |
| [007-slice-land](007-slice-land/spec.md) | 007-01 — land-prepare | **DONE** | 31 tests (30 pass + 1 pytest-skipped); landing-readiness report + direct/pr next-steps |
| [007-slice-land](007-slice-land/spec.md) | 007-02 — direct-mode-execute | **DONE** | Deferred; destructive git ops need safety review |
| [007-slice-land](007-slice-land/spec.md) | 007-03 — pr-mode-execute | **DONE** | 24 new tests (485 total, 3 skipped); `execute --mode pr` runs `git push -u origin <branch>` + `gh pr create`; gh-binary + github-remote + branch guards; `--dry-run` preview |
| [007-slice-land](007-slice-land/spec.md) | 007-04 — scaffold-json-integration-flag | DRAFT | Deferred; --mode flag is sufficient for now |
| [008-migrate-existing-project](008-migrate-existing-project/spec.md) | 008-01 — migrate-report | **DONE** |  |
| [008-migrate-existing-project](008-migrate-existing-project/spec.md) | 008-02 — rename-decisions | **DONE** |  |
| [008-migrate-existing-project](008-migrate-existing-project/spec.md) | 008-03 — jig-self-migration | **DONE** |  |
| [008-migrate-existing-project](008-migrate-existing-project/spec.md) | 008-04 — slice-to-spec-mapping | DRAFT |  |
| [008-migrate-existing-project](008-migrate-existing-project/spec.md) | 008-05 — scaffold-init --migrate suggestion | **DONE** |  |
| [009-dod-close-out-separation](009-dod-close-out-separation/spec.md) | 009-01 — close-out-section-recognition | **DONE** |  |
| [011-plugin-self-install](011-plugin-self-install/spec.md) | 011-01 — local-plugin-install | **DONE** | 20 new tests (351 total); first real reviewer dogfood — reviewer + architect refused write, implementer wrote |
| [011-plugin-self-install](011-plugin-self-install/spec.md) | 011-02 — subagent-type-fallback-upgrade | **DONE** | 11 new tests (362 total); real `jig:reviewer` dogfood clean; install-snapshot lag flagged for follow-up |
| [011-plugin-self-install](011-plugin-self-install/spec.md) | 011-03 — scaffold-json-self-install-marker | DRAFT | Deferred; no caller needs the signal yet |
| [011-plugin-self-install](011-plugin-self-install/spec.md) | 011-04 — subagentstart-reachability | DRAFT | Deferred; gated on a real subagent-event use case |
| [012-pr-review](012-pr-review/spec.md) | 012-01 — pr-review-skill | **DONE** | 23 new tests (394 total); lightweight baseline; defers to richer user skill via description hint; first non-stub active jig skill without a `.py` helper; routing-dogfood + own-slice dogfood deferred to user-driven Close-out |
| [012-pr-review](012-pr-review/spec.md) | 012-02 — pr-review-gather-helper | DRAFT |  |
| [012-pr-review](012-pr-review/spec.md) | 012-03 — security-lens-integration | DRAFT |  |
| [012-pr-review](012-pr-review/spec.md) | 012-04 — language-specific-references | DRAFT |  |
| [013-release-pipeline](013-release-pipeline/spec.md) | 013-01 — ci-baseline | **DONE** |  |
| [013-release-pipeline](013-release-pipeline/spec.md) | 013-02 — release-please-scaffold | **DONE** |  |
| [013-release-pipeline](013-release-pipeline/spec.md) | 013-03 — release-zip-artifact | **DONE** |  |
| [013-release-pipeline](013-release-pipeline/spec.md) | 013-04 — marketplace-rename-and-docs | **DONE** |  |
