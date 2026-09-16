---
slice: 113-04 — advisory-hooks
pass: arch
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-09-16T06:14:32Z
prompt_source: review.py arch 113-04 (R2)
substrate: shown
applied_skill: none
shown_candidates: [arch-review:high-confidence, access:speculative, adobe-security-antipatterns:speculative, adobe-security-audit:speculative, adobe-security-client:speculative, adobe-security-cloud:speculative, adobe-security-foundations:speculative, adobe-security-lang:speculative, adobe-security-services:speculative, adr-workflow:speculative, agent-development:speculative, analyze:speculative, audit-migrator:speculative, block-kit:speculative, bug-fix:speculative, build-mcp-app:speculative, build-mcp-server:speculative, build-mcpb:speculative, cardputer-buddy:speculative, clarify:speculative, claude-automation-recommender:speculative, claude-md-improver:speculative, claude-security:speculative, code-health:speculative, command-development:speculative, configure:speculative, content-fidelity:speculative, contracts:speculative, create-slack-app:speculative, cutline:speculative, debug-workflow:speculative, design-eval:speculative, eval-authoring:speculative, example-command:speculative, example-skill:speculative, explain:speculative, frontend-design:speculative, get-content-scrape:speculative, hook-development:speculative, independent-review:speculative, investigate-alert:speculative, local-dev:speculative, m5-onboard:speculative, math-olympiad:speculative, mcp-integration:speculative, memory-sync:speculative, migrate:speculative, morning-ai-radar:speculative, morning-assistant:speculative, morning-confluence:speculative, morning-github:speculative, morning-jira:speculative, morning-outlook:speculative, morning-slack:speculative, morning-spike:speculative, mysticat-debug:speculative, orient:speculative, playground:speculative, plugin-settings:speculative, plugin-structure:speculative, pr-review:speculative, project-artifact:speculative, query-audits:speculative, query-opportunities:speculative, query-scrapes:speculative, query-sites:speculative, receipts:speculative, reframe:speculative, release-check:speculative, release-slate:speculative, run-preflight:speculative, scaffold-init:speculative, scope-audit:speculative, scout-autotune:speculative, scout-bench-create:speculative, scout-memory-init:speculative, scout-pr-review:speculative, scout-scrum-master:speculative, security-review:speculative, servo:agent-loop:speculative, servo:autonomy-readiness:speculative, servo:edd-suitability:speculative, servo:execution-planner:speculative, servo:heartbeat:speculative, servo:oracle-hook:speculative, servo:quality-gate:speculative, servo:scaffold-init:speculative, servo:spec-oracle:speculative, session-report:speculative, shape-release:speculative, silence-alert:speculative, skill-creator:speculative, skill-development:speculative, slack-api:speculative, slack-cli:speculative, slack-docs:speculative, slack-messaging:speculative, slack-search:speculative, slice-land:speculative, spacecat-configuration:speculative, spec-workflow:speculative, steward:speculative, tdd-loop:speculative, test-pr-in-dev:speculative, vision-elicitation:speculative, webpage-replica:speculative, writing-hookify-rules:speculative]
---

Arch pass on slice 113-04 (`arch_review: true` — introduces the hook-protocol
translation layer). Reviewer: read-only jig:reviewer. VERDICT: pass.

Architecturally sound for the advisory scope: a clean split between build-time
config/event/matcher translation (on `CopilotScaffoldRenderer`) and a runtime,
standalone, Copilot-only input adapter (`copilot_hook_adapter.py`, never imports
`scaffold.py`, never modifies canonical scripts) — fitting the HostRenderer pattern;
canonical `hooks/scripts/*.sh` + `lib/*.py` stay byte-identical across all three
hosts; dropping Claude's `continue` (no Copilot `HookOutput` analogue) rather than
guessing is the honest, mapped-or-explicitly-unmappable call.

Load-bearing FORWARD concern — confirmed real, now homed to slice-05 (not a 113-04
blocker, since advisory hooks are fail-open by design): the adapter's always-exit-0
posture is correct for advisory, but reused verbatim for 113-05's ENFORCING hooks
(which block via `exit 2`) it would convert `exit 2`→`exit 0` with no
`permissionDecision:"deny"` — silently losing the gate's teeth (ADR-0061 "keep their
teeth / degrade visibly, not silently"). 113-05 must add runtime output/exit
post-processing + a per-hook advisory/enforcing mode (recorded in slice-05 DoR).

Nits (fixed): narrowed the always-exit-0 justification comment to explicitly
"advisory"; quoted `{script_path}` in `build_hook_command` (space-safe). Open
question carried to 113-05: whether the response-half `translate_hook_protocol`
belongs in the render layer, given the enforcing response signal is a runtime
`exit 2` only the adapter observes.
