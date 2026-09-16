---
slice: 113-04 — advisory-hooks
pass: craft
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-09-16T06:14:31Z
prompt_source: review.py craft 113-04 (R2)
substrate: shown
applied_skill: none
shown_candidates: [arch-review:high-confidence, independent-review:high-confidence, pr-review:high-confidence, scout-pr-review:high-confidence, servo:agent-loop:high-confidence, servo:autonomy-readiness:high-confidence, servo:quality-gate:high-confidence, access:speculative, adobe-security-antipatterns:speculative, adobe-security-audit:speculative, adobe-security-client:speculative, adobe-security-cloud:speculative, adobe-security-foundations:speculative, adobe-security-lang:speculative, adobe-security-services:speculative, adr-workflow:speculative, agent-development:speculative, analyze:speculative, audit-migrator:speculative, block-kit:speculative, bug-fix:speculative, build-mcp-app:speculative, build-mcp-server:speculative, build-mcpb:speculative, cardputer-buddy:speculative, clarify:speculative, claude-automation-recommender:speculative, claude-md-improver:speculative, claude-security:speculative, code-health:speculative, command-development:speculative, configure:speculative, content-fidelity:speculative, contracts:speculative, create-slack-app:speculative, cutline:speculative, debug-workflow:speculative, design-eval:speculative, eval-authoring:speculative, example-command:speculative, example-skill:speculative, explain:speculative, frontend-design:speculative, get-content-scrape:speculative, hook-development:speculative, investigate-alert:speculative, local-dev:speculative, m5-onboard:speculative, math-olympiad:speculative, mcp-integration:speculative, memory-sync:speculative, migrate:speculative, morning-ai-radar:speculative, morning-assistant:speculative, morning-confluence:speculative, morning-github:speculative, morning-jira:speculative, morning-outlook:speculative, morning-slack:speculative, morning-spike:speculative, mysticat-debug:speculative, orient:speculative, playground:speculative, plugin-settings:speculative, plugin-structure:speculative, project-artifact:speculative, query-audits:speculative, query-opportunities:speculative, query-scrapes:speculative, query-sites:speculative, receipts:speculative, reframe:speculative, release-check:speculative, release-slate:speculative, run-preflight:speculative, scaffold-init:speculative, scope-audit:speculative, scout-autotune:speculative, scout-bench-create:speculative, scout-memory-init:speculative, scout-scrum-master:speculative, security-review:speculative, servo:edd-suitability:speculative, servo:execution-planner:speculative, servo:heartbeat:speculative, servo:oracle-hook:speculative, servo:scaffold-init:speculative, servo:spec-oracle:speculative, session-report:speculative, shape-release:speculative, silence-alert:speculative, skill-creator:speculative, skill-development:speculative, slack-api:speculative, slack-cli:speculative, slack-docs:speculative, slack-messaging:speculative, slack-search:speculative, slice-land:speculative, spacecat-configuration:speculative, spec-workflow:speculative, steward:speculative, tdd-loop:speculative, test-pr-in-dev:speculative, vision-elicitation:speculative, webpage-replica:speculative, writing-hookify-rules:speculative]
---

Craft pass (pr-review baseline, `--richer-skill none`) on slice 113-04 (advisory-hooks).
Reviewer: read-only jig:reviewer. VERDICT: pass.

Production code correct + complete for the advisory scope; strong non-vacuous
end-to-end firing tests (real build → rendered command string → adapter path
resolution → payload translation → script fires) with negative controls.

Nits (all fixed post-review): test hermeticity — the adapter-fronted E2E tests now
set `CLAUDE_PROJECT_DIR` to the temp project dir (closes a genuine local-red /
CI-green fragility where entry-gate would evaluate the real repo under Claude Code);
git-freshness E2E strengthened to assert the `additionalContext` nudge via a
hermetic behind-`origin/main` fixture (not just `returncode == 0`); the adapter
`main()` `CLAUDE_PROJECT_DIR` derivation/guard branch now has a focused unit test.

Strengths: `ReverseToolMapConsistencyTests` drift-guards the deliberately-duplicated
tool map against 113-03's forward map; byte-identical copy of the canonical
`.sh`/`lib/*.py` keeps Claude/Codex output unaffected (validated by a test).

Leanness note (logged, grounded not speculative): `block_reason→deny` + the full
`CLAUDE_TO_COPILOT_EVENTS` enum are single-source lookup data vs the shipped
`HookType` enum, not dead logic. Post-review fixes were re-covered by the compliance
re-review (pass) + the green suite (4701).
