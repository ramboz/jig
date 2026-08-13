---
slice: 088-02 — the `/jig:orient` judgment skill
pass: arch
verdict: pass
reviewer: jig:reviewer (arch-review lens)
reviewed_at: 2026-08-12T04:27:16Z
prompt_source: review.py arch-review docs/specs/088-project-orientation/spec.md 088-02 --richer-skill none
substrate: shown
applied_skill: none
shown_candidates: [arch-review:high-confidence, access:speculative, adobe-security-antipatterns:speculative, adobe-security-audit:speculative, adobe-security-client:speculative, adobe-security-cloud:speculative, adobe-security-foundations:speculative, adobe-security-lang:speculative, adobe-security-services:speculative, adr-workflow:speculative, agent-development:speculative, analyze:speculative, audit-migrator:speculative, block-kit:speculative, bug-fix:speculative, build-mcp-app:speculative, build-mcp-server:speculative, build-mcpb:speculative, cardputer-buddy:speculative, clarify:speculative, claude-automation-recommender:speculative, claude-md-improver:speculative, claude-security:speculative, code-health:speculative, command-development:speculative, configure:speculative, contracts:speculative, create-slack-app:speculative, cutline:speculative, debug-workflow:speculative, design-eval:speculative, example-command:speculative, example-skill:speculative, explain:speculative, frontend-design:speculative, hook-development:speculative, independent-review:speculative, investigate-alert:speculative, local-dev:speculative, m5-onboard:speculative, math-olympiad:speculative, mcp-integration:speculative, memory-sync:speculative, migrate:speculative, morning-ai-radar:speculative, morning-assistant:speculative, morning-confluence:speculative, morning-github:speculative, morning-jira:speculative, morning-outlook:speculative, morning-slack:speculative, morning-spike:speculative, mysticat-debug:speculative, orient:speculative, playground:speculative, plugin-settings:speculative, plugin-structure:speculative, pr-review:speculative, project-artifact:speculative, query-audits:speculative, query-opportunities:speculative, query-scrapes:speculative, query-sites:speculative, receipts:speculative, reframe:speculative, release-check:speculative, release-slate:speculative, scaffold-init:speculative, scope-audit:speculative, scout-autotune:speculative, scout-bench-create:speculative, scout-memory-init:speculative, scout-pr-review:speculative, scout-scrum-master:speculative, security-review:speculative, servo:agent-loop:speculative, servo:edd-suitability:speculative, servo:heartbeat:speculative, servo:oracle-hook:speculative, servo:quality-gate:speculative, servo:scaffold-init:speculative, servo:spec-oracle:speculative, session-report:speculative, shape-release:speculative, silence-alert:speculative, skill-creator:speculative, skill-development:speculative, slack-api:speculative, slack-cli:speculative, slack-docs:speculative, slack-messaging:speculative, slack-search:speculative, slice-land:speculative, spacecat-configuration:speculative, spec-workflow:speculative, tdd-loop:speculative, vision-elicitation:speculative, writing-hookify-rules:speculative]
---

Independent arch pass (arch-review lens) on slice 088-02 (the `/jig:orient` judgment skill) — required because the slice declares `arch_review: true`.

**Verdict: pass.** No blockers. The change respects jig's hooks-are-deterministic / skills-are-judgment boundary (architecture.md § design principles): `/jig:orient` is a prose Tier-1 judgment skill with no new hook and no duplicated deterministic algorithm. It genuinely layers on `workflow.py orient` (which owns the `--fetch` flag and lifecycle-focus rollup) rather than re-deriving focus — SKILL.md explicitly defers the active-rollup computation to the command. The zero-write contract is architecturally clean and honest, with persistence correctly deferred to the separate #91 dashboard-integration concern. Registration is present across the pinned surfaces (scaffold.py, scaffold_contract.py, both host packages).

**Strengths:**
- "Start from the deterministic headline" makes the layer-don't-re-derive boundary load-bearing prose, not just intent — it names the exact command, marks its output as the factual base, and states the anti-drift rationale.
- Zero-write is stated as both contract and judgment, cleanly separating "say the truth" from "become it," with capture pushed to the calling job.

**Nits (non-blocking — deviation-log items):**
- `skills/orient/test_orient_skill_surface.py:1-11` — docstring/class comments reference "slice 101-01, AC5–AC8" and "Bug 031", not 088-02's ACs 1–7. The tests pin later collaboration-survey / freshness additions but not 088-02's own core ACs (name=`orient`, layered-not-re-derived, zero-write). Not an arch defect; provenance labels mislead.
- `CLAUDE.md:13`, `docs/decisions/adr-0045:276` — residual "compass" mentions, but historical/adoption-record prose outside the plugin runtime and host packages, so AC1's scope is satisfied. Flagged for reconciliation to confirm intentional history.

**Leanness:** no over-engineering, premature abstraction, or speculative generality; a simpler design would not satisfy the fixed-layout + grounded-survey ACs.

Reviewer: jig:reviewer (arch-review lens, read-only, context-isolated). Prompt source: review.py arch-review docs/specs/088-project-orientation/spec.md 088-02 --richer-skill none.
