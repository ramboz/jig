---
slice: 122-01 — escalate-stops-the-slice
pass: craft
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-11-18T03:36:59Z
prompt_source: review.py pr-review docs/specs/122-arch-pass-escalation-and-rounds/spec.md 122-01 <6 deliverables> --richer-skill pr-review
substrate: shown
applied_skill: pr-review
shown_candidates: [arch-review:high-confidence, independent-review:high-confidence, pr-review:high-confidence, scout-pr-review:high-confidence, servo:agent-loop:high-confidence, servo:autonomy-readiness:high-confidence, servo:quality-gate:high-confidence, access:speculative, adr-workflow:speculative, aem-author-load-rca:speculative, agent-development:speculative, analyze:speculative, breakdown-diagnosis:speculative, breakdown-to-next-report:speculative, bug-fix:speculative, build-dashboard:speculative, build-mcp-app:speculative, build-mcp-server:speculative, build-mcpb:speculative, capture:speculative, cardputer-buddy:speculative, challenge:speculative, clarify:speculative, claude-automation-recommender:speculative, claude-md-improver:speculative, claude-security:speculative, climb:speculative, cmr:speculative, code-health:speculative, command-development:speculative, configure:speculative, content-fidelity:speculative, contracts:speculative, cowork-plugin-customizer:speculative, create-cowork-plugin:speculative, create-viz:speculative, custom-connector:speculative, customer-inquiry-intake:speculative, cutline:speculative, daily-production-report:speculative, data-consolidate:speculative, data-context-extractor:speculative, data-visualization:speculative, design-eval:speculative, design-space-explore:speculative, eval-authoring:speculative, example-command:speculative, example-skill:speculative, explain:speculative, explore-data:speculative, faq:speculative, frame:speculative, frontend-design:speculative, get-content-scrape:speculative, hackathon:speculative, handoff:speculative, hook-development:speculative, inspection-to-capa:speculative, local-dev:speculative, m5-onboard:speculative, math-olympiad:speculative, maturity:speculative, mcp-integration:speculative, memory-sync:speculative, migrate:speculative, migrate-to-copilot:speculative, morning-plant-pulse:speculative, name:speculative, ncr-writeup:speculative, office-hours:speculative, onboarding:speculative, orient:speculative, patterns:speculative, playground:speculative, plugin-settings:speculative, plugin-structure:speculative, project-artifact:speculative, quote-build:speculative, receipts:speculative, reframe:speculative, release-check:speculative, release-slate:speculative, rfq-to-quote:speculative, root-cause-capa:speculative, routines:speculative, run-preflight:speculative, scaffold-init:speculative, scope-audit:speculative, scout:speculative, scout-autotune:speculative, scout-bench-create:speculative, scout-memory-init:speculative, scout-scrum-master:speculative, security-review:speculative, servo:edd-suitability:speculative, servo:execution-planner:speculative, servo:heartbeat:speculative, servo:oracle-hook:speculative, servo:scaffold-init:speculative, servo:spec-oracle:speculative, session-report:speculative, shape-release:speculative, siege:speculative, skill-creator:speculative, skill-development:speculative, slice-land:speculative, solo:speculative, spec-workflow:speculative, sql-queries:speculative, statistical-analysis:speculative, steward:speculative, supplier-escape-to-alternate-source:speculative, supplier-quote-request:speculative, tdd-loop:speculative, test-pr-in-dev:speculative, trade-study-report:speculative, validate-data:speculative, vision-elicitation:speculative, webpage-replica:speculative, write-query:speculative, writing-hookify-rules:speculative]
---

VERDICT: pass

REASONING:
The slice stays in scope: one shared parser (`escalations`) and one shared message (`escalation_guidance`), used in exactly two places — the `record-review` STOP notice and the arch branch of `validate_evidence`. No new state or command; nothing outside 122-01 is touched (the D1 prose drift is left for 122-03). The change fails safe: an escalation never makes a record clear, and pass, craft and malformed records keep today's messages, with tests pinning each negative case. No correctness blockers; the issues are parser cases missed without warning and one test that cannot fail when its target is removed.

SPECIFIC ISSUES:
- [nit][impl] skills/_common/review_evidence.py:482-486 — The heading regex misses annotated or bold headings already used in this repo's records ("SPECIFIC ISSUES (round 5, nits):", `**SPECIFIC ISSUES:**`); such a record silently falls back to "re-run the review". Accept a parenthetical and optional `**`.
- [nit][impl] skills/_common/review_evidence.py:492-496 — An empty anchor (`- [blocker][spec] — ESCALATE: …`) does not parse; spec-level escalations have no natural file:line. Allow an empty anchor.
- [nit][impl] skills/_common/test_review_evidence.py:1069-1072 — `test_fenced_envelope_parses_like_unfenced` passes with the fence-skip deleted. Cover a case where the fence matters or drop the skip.
- [nit][impl] skills/_common/review_evidence.py:566-569 — `escalated_decisions` detects "well-formed, non-pass" by comparing against a rebuilt `_non_clearing_problem` string, then re-reads the file. A field on `VerdictRecord` would remove the coupling.
- [nit][impl] skills/independent-review/test_review.py:4276-4303 — The STOP notice is tested only for `--verdict fail`; add a `needs-changes` case.
- [nit][impl] skills/_common/review_evidence.py:552-553 — Wording repeats itself ("escalated to a person — N decision(s) a person must decide"); keep "a person must decide".
- [strength][impl] skills/_common/review_evidence.py:547-559 — Parser and message defined once, shared by recorder and gate (ADR-0003's two-callers rule).
- [strength][impl] skills/_common/review_evidence.py:489-496 — The anchor may not contain a separator, ruling out "… — then ESCALATE:"; tests cover it and the hyphenated-path case.
- [strength][impl] skills/_common/test_review_evidence.py:1120-1162 — Tests pin the fail-safe edges (needs-changes stops, pass clears, craft unchanged, malformed generic).
- [strength][impl] skills/spec-workflow/SKILL.md:640-665 — The recovery case is concrete and actionable.

RECONCILIATION NOTES:
- Parser stricter than spec A3's "parse leniently" (parenthetical/bold headings, empty anchors, lowercase or bold token); blocking unaffected. Widen or log.
- Fence-skip effectively untested.
- AC2's check-reviews/transition coverage is through `validate_evidence` unit tests; both callers pass messages through unchanged (workflow.py:969-974).
- Consider exposing well-formedness on `VerdictRecord`.
