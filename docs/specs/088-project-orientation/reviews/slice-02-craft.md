---
slice: 088-02 — the `/jig:orient` judgment skill
pass: craft
verdict: pass
reviewer: jig:reviewer (pr-review lens)
reviewed_at: 2026-08-12T04:26:37Z
prompt_source: review.py pr-review docs/specs/088-project-orientation/spec.md 088-02 --richer-skill none
substrate: shown
applied_skill: none
shown_candidates: [arch-review:high-confidence, independent-review:high-confidence, pr-review:high-confidence, scout-pr-review:high-confidence, servo:agent-loop:high-confidence, servo:quality-gate:high-confidence, access:speculative, adobe-security-antipatterns:speculative, adobe-security-audit:speculative, adobe-security-client:speculative, adobe-security-cloud:speculative, adobe-security-foundations:speculative, adobe-security-lang:speculative, adobe-security-services:speculative, adr-workflow:speculative, agent-development:speculative, analyze:speculative, audit-migrator:speculative, block-kit:speculative, bug-fix:speculative, build-mcp-app:speculative, build-mcp-server:speculative, build-mcpb:speculative, cardputer-buddy:speculative, clarify:speculative, claude-automation-recommender:speculative, claude-md-improver:speculative, claude-security:speculative, code-health:speculative, command-development:speculative, configure:speculative, contracts:speculative, create-slack-app:speculative, cutline:speculative, debug-workflow:speculative, design-eval:speculative, example-command:speculative, example-skill:speculative, explain:speculative, frontend-design:speculative, hook-development:speculative, investigate-alert:speculative, local-dev:speculative, m5-onboard:speculative, math-olympiad:speculative, mcp-integration:speculative, memory-sync:speculative, migrate:speculative, morning-ai-radar:speculative, morning-assistant:speculative, morning-confluence:speculative, morning-github:speculative, morning-jira:speculative, morning-outlook:speculative, morning-slack:speculative, morning-spike:speculative, mysticat-debug:speculative, orient:speculative, playground:speculative, plugin-settings:speculative, plugin-structure:speculative, project-artifact:speculative, query-audits:speculative, query-opportunities:speculative, query-scrapes:speculative, query-sites:speculative, receipts:speculative, reframe:speculative, release-check:speculative, release-slate:speculative, scaffold-init:speculative, scope-audit:speculative, scout-autotune:speculative, scout-bench-create:speculative, scout-memory-init:speculative, scout-scrum-master:speculative, security-review:speculative, servo:edd-suitability:speculative, servo:heartbeat:speculative, servo:oracle-hook:speculative, servo:scaffold-init:speculative, servo:spec-oracle:speculative, session-report:speculative, shape-release:speculative, silence-alert:speculative, skill-creator:speculative, skill-development:speculative, slack-api:speculative, slack-cli:speculative, slack-docs:speculative, slack-messaging:speculative, slack-search:speculative, slice-land:speculative, spacecat-configuration:speculative, spec-workflow:speculative, tdd-loop:speculative, vision-elicitation:speculative, writing-hookify-rules:speculative]
---

Independent craft pass (pr-review lens) on slice 088-02 (the `/jig:orient` judgment skill).

**Verdict: pass.** No blockers. The craft is strong and internally consistent: the fixed 10-section layout is sequential and de-duplicated, `layout.docs_root` is resolved before any artifact read, the offline / `gh`-unavailable path is explicitly handled ("could not check" ≠ "nothing waiting"), and the documented `--fetch` freshness instruction matches a real flag on `workflow.py orient`. Surface tests are notably non-vacuous — assertions are scoped to section *bodies* (via a `section_body()` helper) to defeat heading/whole-file tautologies.

**Nits (non-blocking — deviation-log items):**
- `skills/orient/test_orient_skill_surface.py:1` — module docstring attributes the tests to "slice 101-01, AC5–AC8" and the freshness class to "Bug 031", but this deliverable is slice 088-02 (ACs 1–7). Content is real; the provenance labels misdirect a future reader.
- `skills/orient/SKILL.md:203` — Section 3 example uses `__…__` double-underscore bold inside the blockquote, inconsistent with the `**…**` bold-title idiom the prime directive mandates.
- `skills/orient/SKILL.md:250-260, 299-302, 312-313` — the zero-write invariant is restated three times (dedicated section + judgment bullet + Gotchas bullet); load-bearing but heavier than the repo's one-line-index discipline.

**Strengths:**
- Anti-tautology comments + `section_body()` helper are exemplary guards against "would still pass if the list were deleted".
- `docs_root` resolution is defensive, naming the concrete failure it prevents (mis-reporting a track-local repo as "no spec-driven project").

**Scope note:** the delivered SKILL.md has evolved past 088-02's acceptance surface — it carries the interactive `--fetch`/freshness segment (bug 031, PR #190) and the open-PR/collaboration-layer survey (spec 101-01, PR #122). Coherent and backed by a real flag, but worth a deviation-log line so a future reader knows the reviewed file includes later-spec/bug layers.

Reviewer: jig:reviewer (read-only, context-isolated). Prompt source: review.py pr-review docs/specs/088-project-orientation/spec.md 088-02 --richer-skill none.
