# Bug Status Board

> Related: [Spec Status Board](../specs/README.md). Check both boards before
> folding reported defects into spec acceptance criteria.

| ID | slug | severity | tier | status | reproduces? | regression test | claimed_by | escalated_to | Notes |
|----|------|----------|------|--------|-------------|-----------------|------------|--------------|-------|
| 001 | branch-freshness-preflight | medium | standard | DONE | yes | skills/slice-land/test_land.py::PrepareBranchFreshnessWarningTests::test_prepare_warns_when_branch_behind_origin_main | main |  |  |
| 002 | bug-registry-invisible | medium | standard | DONE | yes | targeted unittest command in bug record | detached |  |  |
| 003 | node-test-runner-detection | medium | standard | DONE | yes | skills/tdd-loop/test_tdd.py::DetectTests::test_node_via_package_json_test_script | codex/work-on-issue-64 |  |  |
| 004 | terminal-status-legibility | low | standard | DONE | yes | skills/bug-fix/test_bug.py::TerminalSegregationTests::test_escalated_bug_rendered_under_terminal_section | claude/fervent-shannon-da9219 |  |  |
| 005 | diagnose-gate-list-shape | medium | standard | DONE | yes | skills/bug-fix/test_bug.py::DiagnoseGateListShapeTests | claude/jig-issue-80-review-dd7b12 |  |  |
| 006 | slice-path-status-rollup | medium | standard | DONE | yes | skills/spec-workflow/test_workflow.py::TransitionTests::test_slice_path_transition_is_not_overwritten_by_spec_rollup | codex/issue-86-status-rollup |  |  |
| 007 | unregistered-plugin-skill-contract | low | standard | DONE | yes | scripts/test_verify_install.py::PluginModeSkillContractTests::test_unregistered_public_skill_fails_and_is_named | codex/issue-89-skill-contract |  |  |
| 008 | flaky-host-package-drift-guard |  |  | REPORTED | no |  | detached |  |  |
| 009 | codex-skill-description-limit | medium | standard | DONE | yes | python3 -m unittest scripts.test_install_contract.PresenceHelperTests scripts.test_install_contract.RealRepoContractTests | detached |  |  |
| 010 | node-default-discovery | medium | standard | DONE | yes | skills/tdd-loop/test_tdd.py::TargetedRunTests::test_node_default_run_uses_builtin_discovery | codex/issue-100-node-default-discovery |  |  |
| 011 | decision-dedup-suppresses-reversals | medium | gnarly | DONE | yes | hooks/scripts/lib/test_decision_scan.py::TestFlagDuplicates::test_recorded_decision_reversal_is_flagged_not_dropped |  |  |  |
| 012 | decisions-no-template-backfill | medium | standard | DONE | yes | skills/memory-sync/test_decisions.py::SeedFromTemplateTests::test_missing_file_is_seeded_and_entry_appended | claude/session-a2-decisions-template-7c3341 |  |  |
| 013 | adr-accept-strict-prose-gate | low | standard | DONE | yes | skills/adr-workflow/test_adr.py::NonCanonicalProseStatusTests | claude/issue-123-comment-9ba699 |  |  |
| 014 | slice-claim-covers-only-in-progress | medium | gnarly | DONE | yes | skills/spec-workflow/test_workflow.py::Bug014WidenedClaimTests | claude/issue-130-jig-bugfix-57198e |  |  |
| 015 | codex-brief-seed-claude-md-leak | medium | standard | DONE | yes | skills/scaffold-init/test_scaffold_mode.py::CodexScaffoldAdapterTests::test_codex_brief_and_seed_name_agents_md_plugin_mode | claude/bug-codex-brief-claude-md |  |  |
| 016 | codex-host-rewrite-mangles-project-name | low |  | REPORTED | yes |  |  |  |  |
| 017 | record-review-blocks-on-stdin | high | standard | DONE | yes | skills/independent-review/test_review.py::Bug017RecordReviewStdinTests | claude/bug-017-stdin-fix |  |  |
| 018 | copy-machinery-leaves-mode-inconsistent | medium | standard | DONE | yes | skills/migrate/test_migrate.py::PluginModeConversionTests | claude/bug-018-close-out |  |  |
| 019 | review-prompt-hardcodes-spec-md | medium | standard | DONE | yes | skills/independent-review/test_review.py::FilePerSliceReviewTargetTests | claude/github-issue-134-0c6fb4 |  |  |
| 020 | adr-index-summary-degradation | low | standard | DONE | yes | skills/adr-workflow/test_adr.py::IndexNoSummaryTests | claude/github-issue-140-63ae37 |  |  |
| 021 | custom-test-command-drops-selector | medium | standard | REPORTED | no |  | claude/bug-021-tdd-selector-gate |  |  |
| 022 | copy-machinery-ignores-docs-root | medium | standard | DONE | yes | skills/migrate/test_migrate.py::CopyMachineryTrackLocalDocsRootTests | claude/bug-copy-machinery-docs-root |  |  |
| 023 | copy-machinery-advisory-host-from-invocation | medium | standard | DONE | yes | skills/migrate/test_migrate.py::CrossHostAdvisoryTests | claude/bug-023-advisory-host |  |  |
| 024 | slice-land-tests-inert-vendored | medium | standard | DONE | yes | skills/slice-land/test_land.py::CheckTestsHelperResolutionTests | claude/issue-129-bug-review-jsr2cp |  |  |
| 025 | packaged-plugin-omits-runtime-scripts | high | gnarly | DONE | yes | scripts/test_build_claude_plugin.py::RuntimeScriptsShippedTests | claude/github-issue-167-bug-0078l0 |  |  |
| 026 | grounding-rule-misses-reconciliation | low | standard | DONE | yes | skills/spec-workflow/test_workflow.py::ReconciliationGroundingRequirementTests | claude/jig-131-ceremony-review-6v7g4l |  |  |
| 027 | slice-authoring-unanchored-template-path | low | standard | DONE | yes | skills/spec-workflow/test_spec_workflow_skill_surface.py::SliceAuthoringReferenceAnchorTests | claude/bug-027-slice-template-anchor |  |  |
| 028 | scaffold-gitignore-runtime-state | medium | standard | DONE | yes | skills/scaffold-init/test_scaffold.py::Bug028RuntimeStateGitignoreTests::test_fresh_scaffold_ignores_runtime_state_paths | claude/bug-028-gitignore-runtime-state |  |  |
| 030 | usage-report-misses-agent-subagents | high | standard | DONE | yes | scripts/test_usage.py::Bug030UndercountDetectionTests::test_report_flags_undercounted_background_delegation | claude/pr-186-review-fix-1bc497 |  |  |
| 031 | orient-skips-origin-freshness | medium | standard | DONE | yes | skills/spec-workflow/test_workflow.py::OrientOriginFreshnessTests::test_fetch_reports_commits_behind_origin | claude/jig-orient-origin-check-1ccf06 |  |  |
| 032 | review-recovery-no-retraction-sweep | low | standard | DONE | yes | skills/spec-workflow/test_spec_workflow_skill_surface.py::FailedReviewRetractionSweepTests | claude/issue-133-0edb78 |  |  |
| 033 | frame-critique-false-positive-grounded | medium | standard | DONE | yes | skills/independent-review/test_review.py::Bug033FrameCritiqueGroundingAwareTests | claude/adversarial-review-leak-64bb2d |  |  |

## Terminal — closed (not fixed as bugs)

> Bugs in a terminal non-DONE state: **ESCALATED** (reclassified to a spec — see `escalated_to`) or **RESOLVED_ON_MAIN** (fixed by another session on trunk). These are closed, not unfinished — blank `reproduces?` / `regression test` columns are expected. Don't flag them stale or advance them to DONE.

| ID | slug | severity | tier | status | reproduces? | regression test | claimed_by | escalated_to | Notes |
|----|------|----------|------|--------|-------------|-----------------|------------|--------------|-------|
| 029 | slice-path-transition-silent-noop | medium | standard | RESOLVED_ON_MAIN | no | skills/spec-workflow/test_workflow.py::TransitionTests::test_slice_path_transition_is_not_overwritten_by_spec_rollup | claude/github-issue-187-fix-6836d0 |  |  |
