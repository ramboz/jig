# Spec Status Board

> Current state of all specs. Maintained by `workflow.py status-board` — re-run
> any time to sync with `docs/specs/*/spec.md`. The Notes column is preserved
> across regen, so curate it freely.
>
> A leading 🔬 in the Slice column flags slices marked `kind: spike` in their
> frontmatter — timeboxed investigation, not feature work (see [SPIDR
> primer](../spec-workflow/spidr-primer.md) and `skills/spec-workflow/SKILL.md`
> for the body shape). The marker is recomputed from each slice's `kind:` field
> on every regen — it is never stored separately in this file.

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
| [003-spec-workflow-promotion](003-spec-workflow-promotion/spec.md) | 003-02 — anti-horizontal-phasing-check | DEFERRED |  |
| [003-spec-workflow-promotion](003-spec-workflow-promotion/spec.md) | 003-03 — reserve-spec-on-main | **DONE** | Revived from "new-spec-scaffolding"; reserve next free spec number on origin/main with PR fallback |
| [003-spec-workflow-promotion](003-spec-workflow-promotion/spec.md) | 003-04 — auto-tick-review-passed-on-transition | **DONE** | 9 new tests (371 total); transition auto-ticks review-passed boxes — pre-tick anti-pattern fixed structurally |
| [004-independent-review-promotion](004-independent-review-promotion/spec.md) | 004-01 — review-helper | **DONE** |  |
| [005-adr-workflow](005-adr-workflow/spec.md) | 005-01 — adr-helper | **DONE** | 46 tests green; first Tier 1 skill — adr-workflow active |
| [005-adr-workflow](005-adr-workflow/spec.md) | 005-02 — supersede | **DONE** | +29 tests (1240 → 1269 green); `adr.py supersede <old> <new>` appends `Superseded by [ADR-NNNN](./adr-NNNN-<slug>.md) (date)` to old + `Supersedes ADR-NNNN` (plain text) to new. Both `Accepted (date)` lines preserved (the one edit allowed on an immutable ADR per Nygard). Refuses self-supersession, Proposed/already-Superseded sides, missing-files, malformed NNNN — all preconditions validated BEFORE any file mutation (pinned by `test_supersede_refusal_does_not_mutate_either_file`). `_extract_status_and_date` extended to return `("Superseded", date)` with most-recent-state-wins semantics (closes slice 005-01 dev-log #6 latent bug). Resolution trigger fired 2026-05-15 (ADR-0005 superseded ADR-0002); dogfood test reproduces that pair byte-for-byte modulo today's date. Two-phase commit across both ADR writes deliberately NOT added — parked in `docs/inbox.md` as a watch-item (real-world partial-write incident is the trigger). |
| [005-adr-workflow](005-adr-workflow/spec.md) | 005-03 — boundary-change-detection | **DONE** | +34 tests (1206 → 1240 green); `hooks/scripts/jig-boundary-change-warn.sh` fires on PostToolUse `Edit&#124;Write&#124;MultiEdit` and emits a soft `additionalContext` nudge when the touched basename matches a canonical external-interface contract artifact (OpenAPI ×3 / AsyncAPI ×3 / `*.proto` / `*.graphql`/`*.graphqls` / `*.schema.json`). Nudge points at `/jig:adr-workflow new` + the surface-appropriate breaking-change tool from the contracts skill's per-surface table (`buf breaking` / `graphql-inspector diff` / `redocly` / `ajv`). Opt-out via `JIG_BOUNDARY_CHECK=0`; silent `except Exception: pass` mirrors slice 027-01. Co-located in the existing PostToolUse matcher; scaffold-mode parity wired through `_EXPECTED_HOOK_SCRIPTS`. Seven hooks now ("six → seven" sweep at six sites including a forward-leaning `scaffold.py:660` count-free rewrite). Dogfood deferred — jig has no contract artifacts of its own; first real-world fire happens in downstream projects. |
| [006-tdd-loop](006-tdd-loop/spec.md) | 006-01 — tdd-helper | **DONE** | 25 tests (23 pass + 2 pytest-skipped); detect + run with normalized exit codes |
| [006-tdd-loop](006-tdd-loop/spec.md) | 006-02 — ac-coverage | DEFERRED |  |
| [006-tdd-loop](006-tdd-loop/spec.md) | 006-03 — pre-commit-gate | DEFERRED | Deferred; no missing-coverage incident yet |
| [006-tdd-loop](006-tdd-loop/spec.md) | 006-04 — missing-module-exit-code | **DONE** | 5 new tests (44 tdd-loop total); `No module named pytest` → exit 2 via `_is_module_importable` preflight |
| [006-tdd-loop](006-tdd-loop/spec.md) | 006-05 — custom-test-command | **DONE** | 14 new tests (44 tdd-loop total); `.jig/test-command` override + `scripts/run_tests.py`; `tdd.py run .` now runs jig's full 461-test suite |
| [007-slice-land](007-slice-land/spec.md) | 007-01 — land-prepare | **DONE** | 31 tests (30 pass + 1 pytest-skipped); landing-readiness report + direct/pr next-steps |
| [007-slice-land](007-slice-land/spec.md) | 007-02 — direct-mode-execute | **DONE** | Deferred; destructive git ops need safety review |
| [007-slice-land](007-slice-land/spec.md) | 007-03 — pr-mode-execute | **DONE** | 24 new tests (485 total, 3 skipped); `execute --mode pr` runs `git push -u origin <branch>` + `gh pr create`; gh-binary + github-remote + branch guards; `--dry-run` preview |
| [007-slice-land](007-slice-land/spec.md) | 007-04 — scaffold-json-integration-flag | DEFERRED |  |
| [008-migrate-existing-project](008-migrate-existing-project/spec.md) | 008-01 — migrate-report | **DONE** |  |
| [008-migrate-existing-project](008-migrate-existing-project/spec.md) | 008-02 — rename-decisions | **DONE** |  |
| [008-migrate-existing-project](008-migrate-existing-project/spec.md) | 008-03 — jig-self-migration | **DONE** |  |
| [008-migrate-existing-project](008-migrate-existing-project/spec.md) | 008-04 — slice-to-spec-mapping | DEFERRED |  |
| [008-migrate-existing-project](008-migrate-existing-project/spec.md) | 008-05 — scaffold-init --migrate suggestion | **DONE** |  |
| [009-dod-close-out-separation](009-dod-close-out-separation/spec.md) | 009-01 — close-out-section-recognition | **DONE** | `check_dod` recognizes `### Close-out (post-DONE)` subsection and excludes its checkboxes from the count; consumed by template + spec 025-01 |
| [011-plugin-self-install](011-plugin-self-install/spec.md) | 011-01 — local-plugin-install | **DONE** | 20 new tests (351 total); first real reviewer dogfood — reviewer + architect refused write, implementer wrote |
| [011-plugin-self-install](011-plugin-self-install/spec.md) | 011-02 — subagent-type-fallback-upgrade | **DONE** | 11 new tests (362 total); real `jig:reviewer` dogfood clean; install-snapshot lag flagged for follow-up |
| [011-plugin-self-install](011-plugin-self-install/spec.md) | 011-03 — scaffold-json-self-install-marker | DEFERRED |  |
| [011-plugin-self-install](011-plugin-self-install/spec.md) | 011-04 — subagentstart-reachability | DEFERRED | Deferred; gated on a real subagent-event use case |
| [012-pr-review](012-pr-review/spec.md) | 012-01 — pr-review-skill | **DONE** | 23 new tests (394 total); lightweight baseline; defers to richer user skill via description hint; first non-stub active jig skill without a `.py` helper; routing-dogfood + own-slice dogfood deferred to user-driven Close-out |
| [012-pr-review](012-pr-review/spec.md) | 012-02 — pr-review-gather-helper | DEFERRED |  |
| [012-pr-review](012-pr-review/spec.md) | 012-03 — security-lens-integration | DEFERRED |  |
| [012-pr-review](012-pr-review/spec.md) | 012-04 — language-specific-references | DEFERRED |  |
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
| [016-scaffold-mode](016-scaffold-mode/spec.md) | 016-04 — update-skill (DEFERRED) | DEFERRED | Deferred; promotion gated on real friction or security-shaped fix |
| [017-vision-elicitation](017-vision-elicitation/spec.md) | 017-01 — vision-template-and-architecture-slots | **DONE** |  |
| [017-vision-elicitation](017-vision-elicitation/spec.md) | 017-02 — vision-elicitation-skill-core | **DONE** |  |
| [017-vision-elicitation](017-vision-elicitation/spec.md) | 017-03 — re-runnable-with-edit-detection | **DONE** |  |
| [017-vision-elicitation](017-vision-elicitation/spec.md) | 017-04 — seed-ADR-pass | DEFERRED |  |
| [018-slice-per-file](018-slice-per-file/spec.md) | 018-01 — parser-foundation-and-dual-read | **DONE** |  |
| [018-slice-per-file](018-slice-per-file/spec.md) | 018-02 — caller-recognition-and-fixtures | **DONE** |  |
| [018-slice-per-file](018-slice-per-file/spec.md) | 018-03 — scaffold-new-specs-as-file-per-slice | **DONE** |  |
| [018-slice-per-file](018-slice-per-file/spec.md) | 018-04 — migrate-split-slices | **DONE** |  |
| [019-land-deviation-log-tolerance](019-land-deviation-log-tolerance/spec.md) | 019-01 — no-deviation-log-flag | **DONE** |  |
| [020-migrate-slice-to-spec](020-migrate-slice-to-spec/spec.md) | 020-01 — slice-to-spec-skill-md | **DONE** |  |
| [021-migrate-copy-machinery](021-migrate-copy-machinery/spec.md) | 021-01 — copy-machinery-subcommand | **DONE** |  |
| [022-contracts](022-contracts/spec.md) | 022-01 — contracts-skill-md | **DONE** |  |
| [022-contracts](022-contracts/spec.md) | 022-02 — integration-touchpoints | **DONE** |  |
| [023-clarify](023-clarify/spec.md) | 023-01 — clarify-skill-md | **DONE** | 30 tests; lightweight ambiguity scan; six-category taxonomy; no `.py` helper; ships without spec-kit deferral hint (per user direction) |
| [024-analyze](024-analyze/spec.md) | 024-01 — analyze-skill-md | **DONE** | 38 surface + 7 PrinciplesCheckBlock tests; non-destructive consistency report; bundles constitution-gate (unconditional `_principles_check_block()` in `review.py`) |
| [025-claude-md-hygiene](025-claude-md-hygiene/spec.md) | 025-01 — cleanup-and-close-out-rule | **DONE** | Slice close-out rule reframed: compress (not add) on spec completion. Codified in `templates/docs/specs/slice-template.md` Close-out section + `skills/spec-workflow/SKILL.md` "CLAUDE.md hygiene" reconciliation gate. CLAUDE.md compressed 111 → 86 lines (~22%); Active-specs 25 → 1. |
| [026-context-fill-telemetry](026-context-fill-telemetry/spec.md) | 026-01 — estimator-and-soft-warn-hook | **DONE** | Context-fill warning extended beyond MCP-server count: byte-based estimator at `hooks/scripts/lib/context_fill.py` measures CLAUDE.md + `docs/memory/*.md`; soft-warn at 30% of an Opus 4.7-sized window (overridable via `JIG_CONTEXT_WINDOW_BYTES` / `JIG_CONTEXT_SOFT_WARN_PCT`). Hook stays non-blocking (`exit 0`); estimator is importable in isolation so servo can subprocess-invoke it. |
| [027-post-tool-edit-verification](027-post-tool-edit-verification/spec.md) | 027-01 — post-edit-verify-hook | **DONE** | +21 tests (1131 green); `hooks/scripts/jig-post-edit-verify.sh` fires on PostToolUse `Edit&#124;Write&#124;MultiEdit` and emits a soft `additionalContext` warning when the claimed write isn't in the file. Bounded 64KB head read (best-effort silent on larger files); opt-out via `JIG_POST_EDIT_VERIFY=0`; never blocks. AC #7's "byte range surrounding the edit" narrowed to head-only (no offset in tool payload) — pinned by `test_10mb_file_with_edit_beyond_64kb_exits_silently`. |
| [028-parallel-session-locks](028-parallel-session-locks/spec.md) | 028-01 — adr-numbering-on-main | **DONE** | +22 tests (1110 → 1132 green); `adr.py new` reserves on origin/main w/ PR-fallback + race-on-push (drops stranded commit AND file) + `--no-push`/`--pr` flags; inline-mirror of workflow.py 003-03 per ADR-0002 (two callers now); shared `_validate_slug` / `_render_adr_content` / `_check_slug_collision` with `cmd_new`; live-remote dogfood against file:// bare repo (real-GitHub origin/main exercise deferred to next real ADR, same shape as 003-03 close-out). |
| [028-parallel-session-locks](028-parallel-session-locks/spec.md) | 028-02 — inbox-and-refinement-todo-append-lock | **DONE** | +15 tests (1182 → 1197 green); `memory.py add-inbox` + new `add-refinement-todo` lock-protected via `fcntl.flock` on `<git-common-dir>/jig-locks/<artifact>.lock` (kernel-managed release, no PID-reuse window). Self-heal moved inside the lock to close a TOCTOU on first-write against a non-existent file. CLI default timeout 5s via `CLI_DEFAULT_LOCK_TIMEOUT`; Python API takes a kwarg. |
| [028-parallel-session-locks](028-parallel-session-locks/spec.md) | 028-03 — status-board-regen-race-check | **DONE** | +9 tests (1197 → 1206 green); `workflow.py status-board` gains a SHA256 checksum-based race-detection guard. Pre-regen + pre-write checksums; `StatusBoardRaceError` → exit code 4 (caught before parent `WorkflowError` in `main()` so subclass exit-code wins). `--force` bypasses both checksum reads + still respects the idempotent fast-path. Identical-content rewrites correctly do NOT trigger a race. |
| [029-spike-slices](029-spike-slices/spec.md) | 029-01 — kind-frontmatter-and-body-shape | **DONE** | Adds `kind` enum to slice frontmatter; `kind: spike` is the first non-default value. `spec_lint.py` hard-errors on unknown enum + soft-warns on missing spike body labels (Question/Time-box/Findings/Outcome); standalone SPIDR primer landed at `docs/spec-workflow/spidr-primer.md`. +34 tests; 988 → 1022 green. |
| [029-spike-slices](029-spike-slices/spec.md) | 029-02 — status-board-spike-marker | **DONE** | Spike slices render with a leading 🔬 prefix in their row (`SPIKE_MARKER` constant in `workflow.py`, derived from `kind:` at render time). Both active + deferred tables; scaffold template carries the same preamble. +17 tests; 1022 → 1039 green. |
| [030-spec-status-rollup](030-spec-status-rollup/spec.md) | 030-01 — rollup-on-transition-and-regen | **DONE** | +25 tests; spec.md `status:` is derived from non-DEFERRED slice states (DONE / IN_PROGRESS / DRAFT). Writes from `transition` + `status-board`; idempotent; defensive on no-frontmatter. Backfill flipped 23 stale DRAFTs to DONE. |
| [031-multi-perspective-review](031-multi-perspective-review/spec.md) | 031-01 — pr-review-pass | **DONE** | +19 tests (1064 → 1083 green); `review.py pr-review` mode + `subagent-type pr-review`; three-pass flow (compliance → craft → optional arch) documented in `spec-workflow/SKILL.md`; routing-via-prose dispatch (Open question #1 lean-(a)); craft-pass output buckets scope/blockers/nits/strengths with `[blocker]`/`[nit]`/`[strength]` tags; first-ever post-impl craft-pass dogfood — verdict pass + 2 nits addressed inline; `_principles_check_block()` deliberately NOT on craft pass (documented in `build_pr_review_prompt` docstring) |
| [031-multi-perspective-review](031-multi-perspective-review/spec.md) | 031-02 — arch-review-trigger | **DONE** | +27 tests (1083 → 1110 green); `review.py arch-review` mode + `subagent-type arch-review`; `workflow.py arch-review-needed` CLI + `slice_needs_arch_review` helper (layout-aware via `_slice_frontmatter`; truthy tokens `true`/`yes`/`on`/`1`); slice template ships commented `arch_review:` hint; spec-workflow SKILL.md three-pass flow extended with conditional arch pass; first-ever post-impl arch-pass dogfood (verdict pass) — slice declared `arch_review: true` on itself; bash recipe wraps `arch-review-needed` in `if ! NEED_ARCH=$(...); then exit 2; fi` so slice-lookup failures surface; `_principles_check_block()` deliberately NOT on arch pass (documented in `build_arch_review_prompt` docstring) |
| [032-atomic-writes](032-atomic-writes/spec.md) | 032-01 — atomic-write-helper | **DONE** |  |
| [032-atomic-writes](032-atomic-writes/spec.md) | 032-02 — scaffold-completion-marker | **DONE** |  |
| [033-host-adapter-portability](033-host-adapter-portability/spec.md) | 033-01 - support-matrix-and-adapter-contract | DRAFT |  |
| [033-host-adapter-portability](033-host-adapter-portability/spec.md) | 033-02 - agents-md-canonical-primer | DRAFT |  |
| [033-host-adapter-portability](033-host-adapter-portability/spec.md) | 033-03 - scaffold-host-renderer-boundary | DRAFT |  |
| [033-host-adapter-portability](033-host-adapter-portability/spec.md) | 033-04 - generated-file-metadata | DRAFT |  |
| [033-host-adapter-portability](033-host-adapter-portability/spec.md) | 033-05 - codex-scaffold-adapter | DEFERRED |  |
| [033-host-adapter-portability](033-host-adapter-portability/spec.md) | 033-06 - codex-plugin-packaging | DEFERRED |  |
| [034-federation-tier](034-federation-tier/spec.md) | 034-01 — registry-schema-and-host-adapter | DRAFT |  |
| [034-federation-tier](034-federation-tier/spec.md) | 034-02 — repo-registry-add-and-list | DRAFT |  |
| [034-federation-tier](034-federation-tier/spec.md) | 034-03 — scaffold-init-role-member | DRAFT |  |
| [034-federation-tier](034-federation-tier/spec.md) | 034-04 — cross-repo-spec-skill | DRAFT |  |
| [034-federation-tier](034-federation-tier/spec.md) | 034-05 — federated-status-aggregator | DRAFT |  |
| [034-federation-tier](034-federation-tier/spec.md) | 034-06 — context-pull-skill | DRAFT |  |
| [034-federation-tier](034-federation-tier/spec.md) | 034-07 — tier0-1-federation-aware-tweaks | DRAFT |  |
| [034-federation-tier](034-federation-tier/spec.md) | 034-08 — repo-registry-remove-update-audit | DRAFT |  |
| [034-federation-tier](034-federation-tier/spec.md) | 034-09 — repo-sync-and-drift-hook | DRAFT |  |
| [034-federation-tier](034-federation-tier/spec.md) | 034-10 — migrate-to-federation | DRAFT |  |
| [034-federation-tier](034-federation-tier/spec.md) | 034-11 — cross-repo-impact-hook | DRAFT |  |
| [035-fixture-exclusion](035-fixture-exclusion/spec.md) | 035-01 — exclude-fixtures-from-installs | **DONE** | `fixtures/` reserved as test-data: excluded at any depth from both scaffold copy + release zip. Runtime sample data must use a different name (`samples/` / `examples/` / `data/`). Fix-forward, no cleanup of stale installs. |
| [036-closed-spec-drift](036-closed-spec-drift/spec.md) | 036-01 — policy-adr | **DONE** | [ADR-0008](../decisions/adr-0008-closed-spec-drift-policy.md) Accepted 2026-05-27. Picks Option C (`## Amendments` default + new-ADR carve-out for decision content). Scope: DONE + SUPERSEDED specs + load-bearing skill/router prose. Tightened from AC #4(a)'s "RECONCILED" wording (RECONCILED is transient). Blocks 038/039/040. arch+pr+compliance all PASS. |
| [036-closed-spec-drift](036-closed-spec-drift/spec.md) | 036-02 — sweep-and-reconciliation-hook | DRAFT | Sweep 4 drifts (drift #5 deferred to 038). One-line reconciliation-checklist hook → ADR-0008 in `spec-workflow/SKILL.md`. Depends on 036-01 (DONE). |
| [037-git-origin-safety](037-git-origin-safety/spec.md) | 037-01 — tbd | DRAFT | External-review brief 03. Four bugs: `_check_ff_viable`/`_execute_direct` (land.py), `_next_spec_number`/preflight (workflow.py). Coupling w/ DEFERRED 007-02. |
| [038-tier-reconciliation](038-tier-reconciliation/spec.md) | 038-01 — tbd | DRAFT | External-review brief 01. ADR-first (real tier vs informational). `_copy_skills_and_agents` tier-blind. README ↔ vision ↔ `_TIER_SKILLS` mismatched. Serialize w/ 040 (both touch README). |
| [039-review-queue-cleanup](039-review-queue-cleanup/spec.md) | 039-01 — tbd | DRAFT | External-review brief 07. Drop instruction, `git rm` tracked stale file, add to .gitignore. Decision (drop vs keep) already made 2026-05-26 session. |
| [040-isolation-honesty](040-isolation-honesty/spec.md) | 040-01 — tbd | DRAFT | External-review brief 06. Doc sweep: README + workflow.md + product-vision.md. Align with SKILL.md caveat (GH #20304). Serialize w/ 038. |
| [041-routing-observability](041-routing-observability/spec.md) | 041-01 — tbd | DRAFT | External-review brief 05. Extend `jig-telemetry.sh` to UserPromptSubmit + `workflow.py routing-stats`. Closes 2 refinement-todo entries. |
| [042-spec-gate-model](042-spec-gate-model/spec.md) | 042-01 — tbd | DRAFT | External-review brief 08. ADR-first (speed-bump vs file-marker vs two-step). Env-var gate verified bypassable via Bash. |
| [043-test-quality-wiring](043-test-quality-wiring/spec.md) | 043-01 — quality-test-coverage | **DONE** |  |
| [043-test-quality-wiring](043-test-quality-wiring/spec.md) | 🔬 043-02 — threshold-calibration (spike) | **DONE** |  |
| [043-test-quality-wiring](043-test-quality-wiring/spec.md) | 043-03 — polyglot-extension | **DONE** |  |
| [043-test-quality-wiring](043-test-quality-wiring/spec.md) | 043-04 — review-prompt-injection | **DONE** | `build_implementation_prompt` embeds quality.py's deterministic YAML snapshot between Evaluate and `## Cross-cutting checks`; degrades to `_Test-quality snapshot unavailable: <reason>._` on any of four failure modes. scaffold-mode copies `quality.py` + `test_quality.py` via `_RETAINED_TEST_FILES` allow-list. |
| [044-rtk-integration-spike](044-rtk-integration-spike/spec.md) | 🔬 044-01 - rtk-e2e-measurement-spike | READY_FOR_IMPLEMENTATION |  |

## Deferred slices

> Slices parked with a stated resolution trigger. Re-open by transitioning to DRAFT.

| Spec | Slice | Resolution trigger |
|------|-------|--------------------|
| [003-spec-workflow-promotion](003-spec-workflow-promotion/spec.md) | 003-02 — anti-horizontal-phasing-check | First slice that ships pure backend changes and slips past review with no UI-layer flag — i.e. when horizontal-phasing risk becomes observed, not theoretical. |
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
| [016-scaffold-mode](016-scaffold-mode/spec.md) | 016-04 — update-skill (DEFERRED) | ≥1 reported issue along the lines of "I scaffolded jig N versions ago and want to update cleanly without overwriting my edits", OR a security-grade fix to a copied artifact (hook script, SKILL.md bash), OR jig adopts per-file metadata headers (audit's Option C) for another reason that makes a SHA-compare cheaper. |
| [017-vision-elicitation](017-vision-elicitation/spec.md) | 017-04 — seed-ADR-pass | First 5 real `/jig:vision-elicit` runs after 017-02 lands. If >25% of those runs name an explicit locked-in decision during Section 6 (Stack) elicitation that the user would have wanted auto-scaffolded as an ADR, promote 017-04 to DRAFT. If <25%, deferral becomes permanent — the elicitation output already names decisions inline and ADR seeding can stay manual. |
| [033-host-adapter-portability](033-host-adapter-portability/spec.md) | 033-05 - codex-scaffold-adapter | A real user asks to use jig from Codex, or a dogfood comparison shows Codex support is needed for an active project. |
| [033-host-adapter-portability](033-host-adapter-portability/spec.md) | 033-06 - codex-plugin-packaging | Codex scaffold mode has at least one successful real-project use, and a user asks for install-and-forget Codex plugin distribution. |
