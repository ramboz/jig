---
slice: 122-02 — arch-round-carry-over
pass: arch
verdict: needs-changes
reviewer: jig:reviewer
reviewed_at: 2026-11-19T00:44:14Z
prompt_source: review.py arch-review docs/specs/122-arch-pass-escalation-and-rounds/spec.md 122-02 <5 deliverables> --richer-skill arch-review (round 1)
substrate: shown
applied_skill: arch-review
shown_candidates: [arch-review:high-confidence, access:speculative, adr-workflow:speculative, aem-author-load-rca:speculative, agent-development:speculative, analyze:speculative, breakdown-diagnosis:speculative, breakdown-to-next-report:speculative, bug-fix:speculative, build-dashboard:speculative, build-mcp-app:speculative, build-mcp-server:speculative, build-mcpb:speculative, capture:speculative, cardputer-buddy:speculative, challenge:speculative, clarify:speculative, claude-automation-recommender:speculative, claude-md-improver:speculative, claude-security:speculative, climb:speculative, cmr:speculative, code-health:speculative, command-development:speculative, configure:speculative, content-fidelity:speculative, contracts:speculative, cowork-plugin-customizer:speculative, create-cowork-plugin:speculative, create-viz:speculative, custom-connector:speculative, customer-inquiry-intake:speculative, cutline:speculative, daily-production-report:speculative, data-consolidate:speculative, data-context-extractor:speculative, data-visualization:speculative, design-eval:speculative, design-space-explore:speculative, eval-authoring:speculative, example-command:speculative, example-skill:speculative, explain:speculative, explore-data:speculative, faq:speculative, frame:speculative, frontend-design:speculative, get-content-scrape:speculative, hackathon:speculative, handoff:speculative, hook-development:speculative, independent-review:speculative, inspection-to-capa:speculative, local-dev:speculative, m5-onboard:speculative, math-olympiad:speculative, maturity:speculative, mcp-integration:speculative, memory-sync:speculative, migrate:speculative, migrate-to-copilot:speculative, morning-plant-pulse:speculative, name:speculative, ncr-writeup:speculative, office-hours:speculative, onboarding:speculative, orient:speculative, patterns:speculative, playground:speculative, plugin-settings:speculative, plugin-structure:speculative, pr-review:speculative, project-artifact:speculative, quote-build:speculative, receipts:speculative, reframe:speculative, release-check:speculative, release-slate:speculative, rfq-to-quote:speculative, root-cause-capa:speculative, routines:speculative, run-preflight:speculative, scaffold-init:speculative, scope-audit:speculative, scout:speculative, scout-autotune:speculative, scout-bench-create:speculative, scout-memory-init:speculative, scout-pr-review:speculative, scout-scrum-master:speculative, security-review:speculative, servo:agent-loop:speculative, servo:autonomy-readiness:speculative, servo:edd-suitability:speculative, servo:execution-planner:speculative, servo:heartbeat:speculative, servo:oracle-hook:speculative, servo:quality-gate:speculative, servo:scaffold-init:speculative, servo:spec-oracle:speculative, session-report:speculative, shape-release:speculative, siege:speculative, skill-creator:speculative, skill-development:speculative, slice-land:speculative, solo:speculative, spec-workflow:speculative, sql-queries:speculative, statistical-analysis:speculative, steward:speculative, supplier-escape-to-alternate-source:speculative, supplier-quote-request:speculative, tdd-loop:speculative, test-pr-in-dev:speculative, trade-study-report:speculative, validate-data:speculative, vision-elicitation:speculative, webpage-replica:speculative, write-query:speculative, writing-hookify-rules:speculative]
---

VERDICT: needs-changes

REASONING:
The design matches spec 122 D3: only the arch builder does a read-only check for its own record at the ADR-0014 §1 path (`_previous_arch_record` reuses `_evidence.evidence_path`, so embedded slices and other-pass records fall through to round 1), switching preamble and prohibitions only then. The agent definition and host packages agree. One documented project rule now contradicts the change: `docs/conventions.md` still requires the "first time" sentence in every reviewer invocation prompt. One wording slip in the round-line block.
round: 1 · open: conventions-first-time-rule-drift/docs/conventions.md, round-line-says-below/skills/independent-review/review.py · searched: docs/conventions.md, docs/architecture.md, review_evidence.evidence_path, record_review body write

SPECIFIC ISSUES:
- [blocker][spec] docs/conventions.md:61-63 — The rule requires "You are seeing this work for the first time." in the first paragraph of every reviewer invocation prompt; `_ROUND_PREAMBLE` omits it by design (AC1). Add the spec 122-02 exception so convention and prompt agree.
- [nit][impl] skills/independent-review/review.py:174 — `_ROUND_LINE_BLOCK` says the previous record is "named below", but it renders above.
- [nit][impl] skills/independent-review/review.py:161-167 — `_ROUND_PROHIBITIONS` relies on `str.replace`; the test at test_review.py:4493 catches a silent no-op.
- [strength][impl] skills/independent-review/review.py:179-186 — Carry-over keys only on the canonical evidence path; no new state, knob or parser.
- [strength][impl] skills/independent-review/review.py:1112-1115 — Change confined to `build_arch_review_prompt`; byte-for-byte test across other passes.
- [strength][spec] skills/independent-review/review.py:189-200 — Read-after-own-review ordering limits anchoring.

RECONCILIATION NOTES:
- conventions.md "first time" rule needs the spec 122-02 exception.
- Round counting depends on recording the full envelope (incl. the last REASONING line) with record-review; consider saying so in the docs.
- AC4's byte-identical test does not cover bug-review (slice-independent builder; low risk).
