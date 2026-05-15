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
| [003-spec-workflow-promotion](003-spec-workflow-promotion/spec.md) | 003-02 — anti-horizontal-phasing-check | DEFERRED | | [003-spec-workflow-promotion](003-spec-workflow-promotion/spec.md) | 003-03 — new-spec-scaffolding | Friction during new-spec authoring becomes a repeatable annoyance — at least three sessions where the boilerplate copy-paste from a prior spec is the visible bottleneck. |
| [003-spec-workflow-promotion](003-spec-workflow-promotion/spec.md) | 003-03 — new-spec-scaffolding | DEFERRED | Deferred this session |
| [003-spec-workflow-promotion](003-spec-workflow-promotion/spec.md) | 003-04 — auto-tick-review-passed-on-transition | **DONE** | 9 new tests (371 total); transition auto-ticks review-passed boxes — pre-tick anti-pattern fixed structurally |
| [004-independent-review-promotion](004-independent-review-promotion/spec.md) | 004-01 — review-helper | **DONE** |  |
| [005-adr-workflow](005-adr-workflow/spec.md) | 005-01 — adr-helper | **DONE** | 46 tests green; first Tier 1 skill — adr-workflow active |
| [005-adr-workflow](005-adr-workflow/spec.md) | 005-02 — supersede | DEFERRED | | [005-adr-workflow](005-adr-workflow/spec.md) | 005-03 — boundary-change-detection | `contracts` skill becomes active. |
| [005-adr-workflow](005-adr-workflow/spec.md) | 005-03 — boundary-change-detection | DEFERRED | Deferred; blocked on contracts |
| [006-tdd-loop](006-tdd-loop/spec.md) | 006-01 — tdd-helper | **DONE** | 25 tests (23 pass + 2 pytest-skipped); detect + run with normalized exit codes |
| [006-tdd-loop](006-tdd-loop/spec.md) | 006-02 — ac-coverage | DEFERRED | | [006-tdd-loop](006-tdd-loop/spec.md) | 006-03 — pre-commit-gate | First production-grade red-tests-committed incident, OR a sustained run of more than 2 commits-with-red-tests within a single spec. |
| [006-tdd-loop](006-tdd-loop/spec.md) | 006-03 — pre-commit-gate | DEFERRED | Deferred; no missing-coverage incident yet |
| [006-tdd-loop](006-tdd-loop/spec.md) | 006-04 — missing-module-exit-code | **DONE** | 5 new tests (44 tdd-loop total); `No module named pytest` → exit 2 via `_is_module_importable` preflight |
| [006-tdd-loop](006-tdd-loop/spec.md) | 006-05 — custom-test-command | **DONE** | 14 new tests (44 tdd-loop total); `.jig/test-command` override + `scripts/run_tests.py`; `tdd.py run .` now runs jig's full 461-test suite |
| [007-slice-land](007-slice-land/spec.md) | 007-01 — land-prepare | **DONE** | 31 tests (30 pass + 1 pytest-skipped); landing-readiness report + direct/pr next-steps |
| [007-slice-land](007-slice-land/spec.md) | 007-02 — direct-mode-execute | **DONE** | Deferred; destructive git ops need safety review |
| [007-slice-land](007-slice-land/spec.md) | 007-03 — pr-mode-execute | **DONE** | 24 new tests (485 total, 3 skipped); `execute --mode pr` runs `git push -u origin <branch>` + `gh pr create`; gh-binary + github-remote + branch guards; `--dry-run` preview |
| [007-slice-land](007-slice-land/spec.md) | 007-04 — scaffold-json-integration-flag | DEFERRED | | [008-migrate-existing-project](008-migrate-existing-project/spec.md) | 008-04 — slice-to-spec-mapping | Either (a) 008-01 + 008-02 + 008-03 all |
| [008-migrate-existing-project](008-migrate-existing-project/spec.md) | 008-01 — migrate-report | **DONE** |  |
| [008-migrate-existing-project](008-migrate-existing-project/spec.md) | 008-02 — rename-decisions | **DONE** |  |
| [008-migrate-existing-project](008-migrate-existing-project/spec.md) | 008-03 — jig-self-migration | **DONE** |  |
| [008-migrate-existing-project](008-migrate-existing-project/spec.md) | 008-04 — slice-to-spec-mapping | DEFERRED |  |
| [008-migrate-existing-project](008-migrate-existing-project/spec.md) | 008-05 — scaffold-init --migrate suggestion | **DONE** |  |
| [009-dod-close-out-separation](009-dod-close-out-separation/spec.md) | 009-01 — close-out-section-recognition | **DONE** |  |
| [011-plugin-self-install](011-plugin-self-install/spec.md) | 011-01 — local-plugin-install | **DONE** | 20 new tests (351 total); first real reviewer dogfood — reviewer + architect refused write, implementer wrote |
| [011-plugin-self-install](011-plugin-self-install/spec.md) | 011-02 — subagent-type-fallback-upgrade | **DONE** | 11 new tests (362 total); real `jig:reviewer` dogfood clean; install-snapshot lag flagged for follow-up |
| [011-plugin-self-install](011-plugin-self-install/spec.md) | 011-03 — scaffold-json-self-install-marker | DEFERRED | | [011-plugin-self-install](011-plugin-self-install/spec.md) | 011-04 — subagentstart-reachability | First skill that needs to react to subagent |
| [011-plugin-self-install](011-plugin-self-install/spec.md) | 011-04 — subagentstart-reachability | DEFERRED | Deferred; gated on a real subagent-event use case |
| [012-pr-review](012-pr-review/spec.md) | 012-01 — pr-review-skill | **DONE** | 23 new tests (394 total); lightweight baseline; defers to richer user skill via description hint; first non-stub active jig skill without a `.py` helper; routing-dogfood + own-slice dogfood deferred to user-driven Close-out |
| [012-pr-review](012-pr-review/spec.md) | 012-02 — pr-review-gather-helper | DEFERRED | | [012-pr-review](012-pr-review/spec.md) | 012-03 — security-lens-integration | Resolution of the `security_lens` parent decision (see [inbox 2026-05-12 entry](../../inbox.md) on graceful-degradation with `adobe-security-suite`). 012-03 plugs into whichever shape that decision takes. |
| [012-pr-review](012-pr-review/spec.md) | 012-03 — security-lens-integration | DEFERRED |  |
| [012-pr-review](012-pr-review/spec.md) | 012-04 — language-specific-references | DEFERRED | | [014-arch-review](014-arch-review/spec.md) | 014-02 — arch-review-gather-helper | Three `arch-review/gather-friction:` inbox entries naming specific sessions where Claude had to re-derive scope inline (parallels 012-02's gather-helper trigger). |
| [013-release-pipeline](013-release-pipeline/spec.md) | 013-01 — ci-baseline | **DONE** |  |
| [013-release-pipeline](013-release-pipeline/spec.md) | 013-02 — release-please-scaffold | **DONE** |  |
| [013-release-pipeline](013-release-pipeline/spec.md) | 013-03 — release-zip-artifact | **DONE** |  |
| [013-release-pipeline](013-release-pipeline/spec.md) | 013-04 — marketplace-rename-and-docs | **DONE** |  |
| [014-arch-review](014-arch-review/spec.md) | 014-01 — arch-review-skill | **DONE** |  |
| [014-arch-review](014-arch-review/spec.md) | 014-02 — arch-review-gather-helper | DEFERRED |  |
| [014-arch-review](014-arch-review/spec.md) | 014-03 — domain-specific-references | DEFERRED |  |
| [014-arch-review](014-arch-review/spec.md) | 014-04 — security-lens-integration | DEFERRED |  |
| [015-structured-lifecycle-metadata](015-structured-lifecycle-metadata/spec.md) | 015-01 — frontmatter-parsing-and-templates | **DONE** | +25 tests (parser + workflow + adr + migrate); slice template at `templates/docs/specs/slice-template.md`; lazy migration; mysticat-architecture comparison adoption #1 |
| [015-structured-lifecycle-metadata](015-structured-lifecycle-metadata/spec.md) | 015-02 — deferred-as-lifecycle-state | **DONE** | +6 tests; `DEFERRED` added to `VALID_STATUSES`; status-board renders separate Deferred section with Resolution trigger; first FROM-state-restricted transition in jig |
| [015-structured-lifecycle-metadata](015-structured-lifecycle-metadata/spec.md) | 015-03 — last-verified-staleness-check | **DONE** | +6 tests; `workflow.py stale [--days N]`; conjunctive criterion (age AND dep-changed); git-log preferred, mtime fallback |
| [016-scaffold-mode](016-scaffold-mode/spec.md) | 016-01 — copy-skills-and-agents | **DONE** | Positioning-recovery (audit-stage): give devs editable in-repo machinery |
| [016-scaffold-mode](016-scaffold-mode/spec.md) | 016-02 — copy-hooks-and-register | **DONE** | Generates `.claude/settings.json` w/ jig hook registration |
| [016-scaffold-mode](016-scaffold-mode/spec.md) | 016-03 — dogfood-and-dual-mode-docs | **DONE** | Flips scaffold-mode to default; rewrites README install paths |
| [016-scaffold-mode](016-scaffold-mode/spec.md) | 016-04 — update-skill (DEFERRED) | DRAFT | Deferred; promotion gated on real friction or security-shaped fix |
| [017-vision-elicitation](017-vision-elicitation/spec.md) | 017-01 — TBD | DRAFT | Stub — closes the wizard gap (audit-stage); slice-level SPIDR pending promotion |

## Deferred slices

> Slices parked with a stated resolution trigger. Re-open by transitioning to DRAFT.

| Spec | Slice | Resolution trigger |
|------|-------|--------------------|
| [003-spec-workflow-promotion](003-spec-workflow-promotion/spec.md) | 003-02 — anti-horizontal-phasing-check | First slice that ships pure backend changes and slips past review with no UI-layer flag — i.e. when horizontal-phasing risk becomes observed, not theoretical. |
| [003-spec-workflow-promotion](003-spec-workflow-promotion/spec.md) | 003-03 — new-spec-scaffolding | Friction during new-spec authoring becomes a repeatable annoyance — at least three sessions where the boilerplate copy-paste from a prior spec is the visible bottleneck. |
| [005-adr-workflow](005-adr-workflow/spec.md) | 005-02 — supersede | First time a real superseding ADR is needed |
| [005-adr-workflow](005-adr-workflow/spec.md) | 005-03 — boundary-change-detection | `contracts` skill becomes active. |
| [006-tdd-loop](006-tdd-loop/spec.md) | 006-02 — ac-coverage | A real spec ships with an AC that doesn't map to any test, AND the gap survives review. Until that happens, the AC↔test mapping discipline is being upheld manually. |
| [006-tdd-loop](006-tdd-loop/spec.md) | 006-03 — pre-commit-gate | First production-grade red-tests-committed incident, OR a sustained run of more than 2 commits-with-red-tests within a single spec. |
| [007-slice-land](007-slice-land/spec.md) | 007-04 — scaffold-json-integration-flag | User reports the `--mode` flag is genuinely annoying in repeated invocations (≥3 instances), OR the first project using jig that has BOTH a direct-merge skill and a PR-merge skill in the same repo. |
| [008-migrate-existing-project](008-migrate-existing-project/spec.md) | 008-04 — slice-to-spec-mapping | Either (a) 008-01 + 008-02 + 008-03 all DONE and the validator migration is actively in progress, OR (b) a second project with similar flat-slice topology surfaces. |
| [011-plugin-self-install](011-plugin-self-install/spec.md) | 011-03 — scaffold-json-self-install-marker | First caller that needs to branch on "jig is installed locally" AND can't get the signal from the runtime directly. |
| [011-plugin-self-install](011-plugin-self-install/spec.md) | 011-04 — subagentstart-reachability | First skill that needs to react to subagent start (e.g. reviewer-pass logging, effort-scaling enforcement, real telemetry to replace the Task-spawn proxy). |
| [012-pr-review](012-pr-review/spec.md) | 012-02 — pr-review-gather-helper | Three `pr-review/gather-friction:` inbox entries naming specific sessions where Claude had to re-derive determinism inline. Count today: 0 (per inbox 2026-05-13 entry). |
| [012-pr-review](012-pr-review/spec.md) | 012-03 — security-lens-integration | Resolution of the `security_lens` parent decision (see [inbox 2026-05-12 entry](../../inbox.md) on graceful-degradation with `adobe-security-suite`). 012-03 plugs into whichever shape that decision takes. |
| [012-pr-review](012-pr-review/spec.md) | 012-04 — language-specific-references | Multi-language-codebase user reports a concrete gap that the lightweight baseline doesn't cover, AND no user-installed `~/.claude/skills/pr-review` deferral target exists for them. |
| [014-arch-review](014-arch-review/spec.md) | 014-02 — arch-review-gather-helper | Three `arch-review/gather-friction:` inbox entries naming specific sessions where Claude had to re-derive scope inline (parallels 012-02's gather-helper trigger). |
| [014-arch-review](014-arch-review/spec.md) | 014-03 — domain-specific-references | Multi-domain-architecture user reports a concrete gap that the lightweight baseline doesn't cover, AND no user-installed `~/.claude/skills/arch-review` deferral target exists for them. |
| [014-arch-review](014-arch-review/spec.md) | 014-04 — security-lens-integration | Resolution of the `security_lens` parent decision (same trigger as 012-03 — both slices plug into whichever shape that decision takes). |
