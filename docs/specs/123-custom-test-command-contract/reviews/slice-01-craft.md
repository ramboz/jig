---
slice: 123-01 — exit-contract
pass: craft
verdict: pass
reviewer: jig:reviewer (pr-review rubric)
reviewed_at: 2026-11-21T02:50:06Z
prompt_source: review.py pr-review --richer-skill pr-review docs/specs/123-custom-test-command-contract/spec.md exit-contract <7 deliverables>
substrate: shown
applied_skill: pr-review
shown_candidates: [arch-review:high-confidence, independent-review:high-confidence, pr-review:high-confidence, scout-pr-review:high-confidence, servo:agent-loop:high-confidence, servo:autonomy-readiness:high-confidence, servo:quality-gate:high-confidence, access:speculative, adr-workflow:speculative, aem-author-load-rca:speculative, agent-development:speculative, analyze:speculative, breakdown-diagnosis:speculative, breakdown-to-next-report:speculative, bug-fix:speculative, build-dashboard:speculative, build-mcp-app:speculative, build-mcp-server:speculative, build-mcpb:speculative, capture:speculative, cardputer-buddy:speculative, challenge:speculative, clarify:speculative, claude-automation-recommender:speculative, claude-md-improver:speculative, claude-security:speculative, climb:speculative, cmr:speculative, code-health:speculative, command-development:speculative, configure:speculative, content-fidelity:speculative, contracts:speculative, cowork-plugin-customizer:speculative, create-cowork-plugin:speculative, create-viz:speculative, custom-connector:speculative, customer-inquiry-intake:speculative, cutline:speculative, daily-production-report:speculative, data-consolidate:speculative, data-context-extractor:speculative, data-visualization:speculative, design-eval:speculative, design-space-explore:speculative, eval-authoring:speculative, example-command:speculative, example-skill:speculative, explain:speculative, explore-data:speculative, faq:speculative, frame:speculative, frontend-design:speculative, get-content-scrape:speculative, hackathon:speculative, handoff:speculative, hook-development:speculative, inspection-to-capa:speculative, local-dev:speculative, m5-onboard:speculative, math-olympiad:speculative, maturity:speculative, mcp-integration:speculative, memory-sync:speculative, migrate:speculative, migrate-to-copilot:speculative, morning-plant-pulse:speculative, name:speculative, ncr-writeup:speculative, office-hours:speculative, onboarding:speculative, orient:speculative, patterns:speculative, playground:speculative, plugin-settings:speculative, plugin-structure:speculative, project-artifact:speculative, quote-build:speculative, receipts:speculative, reframe:speculative, release-check:speculative, release-slate:speculative, rfq-to-quote:speculative, root-cause-capa:speculative, routines:speculative, run-preflight:speculative, scaffold-init:speculative, scope-audit:speculative, scout:speculative, scout-autotune:speculative, scout-bench-create:speculative, scout-memory-init:speculative, scout-scrum-master:speculative, security-review:speculative, servo:edd-suitability:speculative, servo:execution-planner:speculative, servo:heartbeat:speculative, servo:oracle-hook:speculative, servo:scaffold-init:speculative, servo:spec-oracle:speculative, session-report:speculative, shape-release:speculative, siege:speculative, skill-creator:speculative, skill-development:speculative, slice-land:speculative, solo:speculative, spec-workflow:speculative, sql-queries:speculative, statistical-analysis:speculative, steward:speculative, supplier-escape-to-alternate-source:speculative, supplier-quote-request:speculative, tdd-loop:speculative, test-pr-in-dev:speculative, trade-study-report:speculative, validate-data:speculative, vision-elicitation:speculative, webpage-replica:speculative, write-query:speculative, writing-hookify-rules:speculative]
---

VERDICT: pass

REASONING:
The change does what the slice says and stays in scope. `_custom_exit` applies the 0/1/else contract in both custom-command branches, with exactly one last-line message. It checks the exit code before the no-match line, and parse failures, undecodable output and helper crashes now all exit 2. In `land.py`, a blocking `could_not_run` status is kept apart cleanly from the doc-only `warn`. No correctness or security blockers. The tests run the real `tdd.py` and `bug.py` end to end and would fail if the feature were removed, with one wiring gap noted below.

SPECIFIC ISSUES:
- [nit][impl] skills/tdd-loop/test_tdd.py — class docstring says "any other non-zero status stays red", contradicting the contract.
- [nit][impl] skills/tdd-loop/test_tdd.py — the docs-check comment says "AC7"; it is AC9.
- [nit][impl] skills/slice-land/test_land.py — no `prepare()`-level test for `could_not_run`; reverting `has_blocker` would keep the Spec123 land tests green.
- [nit][impl] skills/slice-land/land.py — the reason reaches the report through a module-level global (`_could_not_run_detail`); with one caller, returning the detail would be cleaner.
- [nit][impl] skills/slice-land/land.py — the row says "a test runner was detected" even for a blank `.jig/test-command`.
- [nit][impl] skills/tdd-loop/tdd.py — `except (FileNotFoundError, OSError)` is redundant (pre-existing).
- [strength][impl] skills/tdd-loop/tdd.py — the contract lives in one place (`_custom_exit`), `CUSTOM_EXIT_CONTRACT` is reused by `NO_RUNNER_HINT`, and the docstring explains the single-last-line rule.
- [strength][impl] skills/tdd-loop/tdd.py — requiring `returncode == 1` before the no-match check keeps the bug 021 mapping; both orderings are tested.
- [strength][impl] skills/bug-fix/test_bug.py — gate tests run the real `tdd.py` with a positive exit-1 control.
- [strength][impl] skills/tdd-loop/test_tdd.py — the edge-case tests use real processes (SIGKILL, undecodable bytes) and a patched crash.

RECONCILIATION NOTES:
- Fix the stale docstring and the AC label; add a `prepare()`-level test or record it; accept or follow up the module global; accept or reword the row.
