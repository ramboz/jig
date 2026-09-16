---
slice: 113-03 — agents
pass: craft
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-09-16T04:22:02Z
prompt_source: review.py pr-review 113-03 --richer-skill none
substrate: shown
applied_skill: none
shown_candidates: [arch-review:high-confidence, independent-review:high-confidence, pr-review:high-confidence, scout-pr-review:high-confidence, servo:agent-loop:high-confidence, servo:autonomy-readiness:high-confidence, servo:quality-gate:high-confidence, access:speculative, adobe-security-antipatterns:speculative, adobe-security-audit:speculative, adobe-security-client:speculative, adobe-security-cloud:speculative, adobe-security-foundations:speculative, adobe-security-lang:speculative, adobe-security-services:speculative, adr-workflow:speculative, agent-development:speculative, analyze:speculative, audit-migrator:speculative, block-kit:speculative, bug-fix:speculative, build-mcp-app:speculative, build-mcp-server:speculative, build-mcpb:speculative, cardputer-buddy:speculative, clarify:speculative, claude-automation-recommender:speculative, claude-md-improver:speculative, claude-security:speculative, code-health:speculative, command-development:speculative, configure:speculative, content-fidelity:speculative, contracts:speculative, create-slack-app:speculative, cutline:speculative, debug-workflow:speculative, design-eval:speculative, eval-authoring:speculative, example-command:speculative, example-skill:speculative, explain:speculative, frontend-design:speculative, get-content-scrape:speculative, hook-development:speculative, investigate-alert:speculative, local-dev:speculative, m5-onboard:speculative, math-olympiad:speculative, mcp-integration:speculative, memory-sync:speculative, migrate:speculative, morning-ai-radar:speculative, morning-assistant:speculative, morning-confluence:speculative, morning-github:speculative, morning-jira:speculative, morning-outlook:speculative, morning-slack:speculative, morning-spike:speculative, mysticat-debug:speculative, orient:speculative, playground:speculative, plugin-settings:speculative, plugin-structure:speculative, project-artifact:speculative, query-audits:speculative, query-opportunities:speculative, query-scrapes:speculative, query-sites:speculative, receipts:speculative, reframe:speculative, release-check:speculative, release-slate:speculative, run-preflight:speculative, scaffold-init:speculative, scope-audit:speculative, scout-autotune:speculative, scout-bench-create:speculative, scout-memory-init:speculative, scout-scrum-master:speculative, security-review:speculative, servo:edd-suitability:speculative, servo:execution-planner:speculative, servo:heartbeat:speculative, servo:oracle-hook:speculative, servo:scaffold-init:speculative, servo:spec-oracle:speculative, session-report:speculative, shape-release:speculative, silence-alert:speculative, skill-creator:speculative, skill-development:speculative, slack-api:speculative, slack-cli:speculative, slack-docs:speculative, slack-messaging:speculative, slack-search:speculative, slice-land:speculative, spacecat-configuration:speculative, spec-workflow:speculative, steward:speculative, tdd-loop:speculative, test-pr-in-dev:speculative, vision-elicitation:speculative, webpage-replica:speculative, writing-hookify-rules:speculative]
---

Craft pass (pr-review baseline, `--richer-skill none`) on slice 113-03 (agents).
Reviewer: read-only jig:reviewer.

VERDICT: pass. No blockers.

Strengths: the Bash→`bash` (not `shell`) decision is evidence-grounded (shipped-CLI)
and pinned by a dedicated regression test; the fail-closed unmapped-tool guard
(`CopilotAgentToolError`) is tested at both the unit (`copilot_tool_names`) and
render levels (a source-side unmapped tool is a loud defect, never dropped);
reviewer read-only pinned exactly to [glob, grep, view] + prompt-text assertion;
robust frontmatter fallbacks via reused `parse_frontmatter` (missing name→stem,
missing description→name, scalar tools→list).

Nits (all [impl], logged, non-blocking — not fixed to avoid cosmetic churn on the
controlled 3-agent roster): (1) `name` emitted unquoted while `description` is
json.dumps-quoted — asymmetric YAML-safety, harmless for the current names;
(2) a source agent with no `tools:` would render an empty `tools:` block —
degenerate, unexercised; (3) the agent render path does not call
`assert_namespace_safe_name` on the agent name (agent-name constraint differs from
skills' — Copilot requires ≥1 ASCII letter/digit, not `:`-free) — follow-up if agent
names ever get non-trivial; (4) the reviewer read-only test also asserts absence of
`shell`/`write` tokens the mapping can never emit — partly redundant. No vacuous tests.
