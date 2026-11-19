---
slice: 122-03 — one-blocking-rule
pass: craft
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-11-19T01:03:05Z
prompt_source: review.py pr-review docs/specs/122-arch-pass-escalation-and-rounds/spec.md 122-03 <5 deliverables> --richer-skill pr-review
substrate: shown
applied_skill: pr-review
shown_candidates: [arch-review:high-confidence, independent-review:high-confidence, pr-review:high-confidence, scout-pr-review:high-confidence, servo:agent-loop:high-confidence, servo:autonomy-readiness:high-confidence, servo:quality-gate:high-confidence, access:speculative, adr-workflow:speculative, aem-author-load-rca:speculative, agent-development:speculative, analyze:speculative, breakdown-diagnosis:speculative, breakdown-to-next-report:speculative, bug-fix:speculative, build-dashboard:speculative, build-mcp-app:speculative, build-mcp-server:speculative, build-mcpb:speculative, capture:speculative, cardputer-buddy:speculative, challenge:speculative, clarify:speculative, claude-automation-recommender:speculative, claude-md-improver:speculative, claude-security:speculative, climb:speculative, cmr:speculative, code-health:speculative, command-development:speculative, configure:speculative, content-fidelity:speculative, contracts:speculative, cowork-plugin-customizer:speculative, create-cowork-plugin:speculative, create-viz:speculative, custom-connector:speculative, customer-inquiry-intake:speculative, cutline:speculative, daily-production-report:speculative, data-consolidate:speculative, data-context-extractor:speculative, data-visualization:speculative, design-eval:speculative, design-space-explore:speculative, eval-authoring:speculative, example-command:speculative, example-skill:speculative, explain:speculative, explore-data:speculative, faq:speculative, frame:speculative, frontend-design:speculative, get-content-scrape:speculative, hackathon:speculative, handoff:speculative, hook-development:speculative, inspection-to-capa:speculative, local-dev:speculative, m5-onboard:speculative, math-olympiad:speculative, maturity:speculative, mcp-integration:speculative, memory-sync:speculative, migrate:speculative, migrate-to-copilot:speculative, morning-plant-pulse:speculative, name:speculative, ncr-writeup:speculative, office-hours:speculative, onboarding:speculative, orient:speculative, patterns:speculative, playground:speculative, plugin-settings:speculative, plugin-structure:speculative, project-artifact:speculative, quote-build:speculative, receipts:speculative, reframe:speculative, release-check:speculative, release-slate:speculative, rfq-to-quote:speculative, root-cause-capa:speculative, routines:speculative, run-preflight:speculative, scaffold-init:speculative, scope-audit:speculative, scout:speculative, scout-autotune:speculative, scout-bench-create:speculative, scout-memory-init:speculative, scout-scrum-master:speculative, security-review:speculative, servo:edd-suitability:speculative, servo:execution-planner:speculative, servo:heartbeat:speculative, servo:oracle-hook:speculative, servo:scaffold-init:speculative, servo:spec-oracle:speculative, session-report:speculative, shape-release:speculative, siege:speculative, skill-creator:speculative, skill-development:speculative, slice-land:speculative, solo:speculative, spec-workflow:speculative, sql-queries:speculative, statistical-analysis:speculative, steward:speculative, supplier-escape-to-alternate-source:speculative, supplier-quote-request:speculative, tdd-loop:speculative, test-pr-in-dev:speculative, trade-study-report:speculative, validate-data:speculative, vision-elicitation:speculative, webpage-replica:speculative, write-query:speculative, writing-hookify-rules:speculative]
---

VERDICT: pass

REASONING:
Prose-only slice: the ADR-0014 §3 verdict rule is added once to the output format the craft, arch and code-health prompts share (`_PR_REVIEW_OUTPUT_FORMAT`), and the block-rule paragraphs in spec-workflow/SKILL.md, independent-review/SKILL.md and docs/workflow.md now say one thing. `verdict_clears` is untouched; hosts regenerated. A repo-wide search finds the old wording only in closed spec 031 slices and a review record, correctly excluded. Tests are not vacuous. No blockers; test-precision nits only. End state checked (no git diff, read-only).

SPECIFIC ISSUES:
- [nit][impl] skills/independent-review/test_review.py:4580 — `assertIn("ADR-0014", text)` cannot fail (already cited); AC2's nits-only-pass and deviation-log clauses are not pinned.
- [nit][impl] skills/independent-review/test_review.py:4564 — Regex misses "do not block" / "doesn't block".
- [nit][impl] skills/independent-review/test_review.py:4519-4523 — Scan omits `skills/*/references/*.md`; known limit.
- [nit][impl] skills/independent-review/test_review.py:4509-4511, 4581 — PEP 8 blank lines.
- [strength][impl] skills/independent-review/test_review.py:4526-4530 — `_prose_units` judges each bullet alone.
- [strength][impl] skills/independent-review/review.py:911-914 — Rule added once in the shared format; test runs all three prompts.
- [strength][impl] skills/spec-workflow/SKILL.md:586-588 — Orchestrator never re-records `needs-changes` as `pass`; a blocker-less `needs-changes` is re-run.

RECONCILIATION NOTES:
- Tighten or drop the "ADR-0014" assertion.
- Widen the forbidden-phrase regex.
- Record the references/*.md scan limit.
- Closed records (spec 031 slices, the 122-01 compliance record) keep old wording as intended.
