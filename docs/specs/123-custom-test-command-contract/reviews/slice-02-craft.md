---
slice: 123-02 — dead-end-policy-recipe
pass: craft
verdict: pass
reviewer: jig:reviewer (pr-review rubric)
reviewed_at: 2026-11-21T02:50:08Z
prompt_source: review.py pr-review --richer-skill pr-review docs/specs/123-custom-test-command-contract/spec.md dead-end <10 deliverables>
substrate: shown
applied_skill: pr-review
shown_candidates: [arch-review:high-confidence, independent-review:high-confidence, pr-review:high-confidence, scout-pr-review:high-confidence, servo:agent-loop:high-confidence, servo:autonomy-readiness:high-confidence, servo:quality-gate:high-confidence, access:speculative, adr-workflow:speculative, aem-author-load-rca:speculative, agent-development:speculative, analyze:speculative, breakdown-diagnosis:speculative, breakdown-to-next-report:speculative, bug-fix:speculative, build-dashboard:speculative, build-mcp-app:speculative, build-mcp-server:speculative, build-mcpb:speculative, capture:speculative, cardputer-buddy:speculative, challenge:speculative, clarify:speculative, claude-automation-recommender:speculative, claude-md-improver:speculative, claude-security:speculative, climb:speculative, cmr:speculative, code-health:speculative, command-development:speculative, configure:speculative, content-fidelity:speculative, contracts:speculative, cowork-plugin-customizer:speculative, create-cowork-plugin:speculative, create-viz:speculative, custom-connector:speculative, customer-inquiry-intake:speculative, cutline:speculative, daily-production-report:speculative, data-consolidate:speculative, data-context-extractor:speculative, data-visualization:speculative, design-eval:speculative, design-space-explore:speculative, eval-authoring:speculative, example-command:speculative, example-skill:speculative, explain:speculative, explore-data:speculative, faq:speculative, frame:speculative, frontend-design:speculative, get-content-scrape:speculative, hackathon:speculative, handoff:speculative, hook-development:speculative, inspection-to-capa:speculative, local-dev:speculative, m5-onboard:speculative, math-olympiad:speculative, maturity:speculative, mcp-integration:speculative, memory-sync:speculative, migrate:speculative, migrate-to-copilot:speculative, morning-plant-pulse:speculative, name:speculative, ncr-writeup:speculative, office-hours:speculative, onboarding:speculative, orient:speculative, patterns:speculative, playground:speculative, plugin-settings:speculative, plugin-structure:speculative, project-artifact:speculative, quote-build:speculative, receipts:speculative, reframe:speculative, release-check:speculative, release-slate:speculative, rfq-to-quote:speculative, root-cause-capa:speculative, routines:speculative, run-preflight:speculative, scaffold-init:speculative, scope-audit:speculative, scout:speculative, scout-autotune:speculative, scout-bench-create:speculative, scout-memory-init:speculative, scout-scrum-master:speculative, security-review:speculative, servo:edd-suitability:speculative, servo:execution-planner:speculative, servo:heartbeat:speculative, servo:oracle-hook:speculative, servo:scaffold-init:speculative, servo:spec-oracle:speculative, session-report:speculative, shape-release:speculative, siege:speculative, skill-creator:speculative, skill-development:speculative, slice-land:speculative, solo:speculative, spec-workflow:speculative, sql-queries:speculative, statistical-analysis:speculative, steward:speculative, supplier-escape-to-alternate-source:speculative, supplier-quote-request:speculative, tdd-loop:speculative, test-pr-in-dev:speculative, trade-study-report:speculative, validate-data:speculative, vision-elicitation:speculative, webpage-replica:speculative, write-query:speculative, writing-hookify-rules:speculative]
---

VERDICT: pass

REASONING:
The slice does what it set out to do. The no-runner message comes from one helper, `_report_no_runner`, which both `detect` and `run` call. The single-line hint is built from shared constants (`CUSTOM_EXIT_CONTRACT`, `RECIPES_DOC`), so its wording cannot drift from the contract. The Gradle wrapper fails closed: it deletes old reports before the run, reads only the `<testsuite>` header counts, and exits 1 only when those counts show a failure or an error. Its tests run the script extracted from the document itself, and none of the tests checked are vacuous: the "noisy" case, the stale-report case and the no-report case each go red if their feature is removed. All findings are nits.

SPECIFIC ISSUES:
- [nit][impl] skills/tdd-loop/tdd.py:60 — the hint says "line 1 of .jig/test-command", but the parser takes the first non-blank, non-comment line.
- [nit][impl] skills/tdd-loop/test_tdd.py:1154 — the end-to-end subtest copies `os.environ` without removing `JIG_GRADLE*`/`JIG_GRADLEW`, which `_run` does remove (flakiness risk).
- [nit][impl] skills/tdd-loop/test_tdd.py:1060 — the skip guard checks `/bin/sh`, but the tests run `sh` through PATH; `shutil.which("sh")` would match.
- [nit][impl] skills/tdd-loop/test_tdd.py:1168-1170 — the `assertNotIn`/`assertNotRegex` checks look for exact old wording, so they are close to vacuous; the `assertIn` checks do the real work.
- [nit][impl] skills/bug-fix/SKILL.md:170 — the new sentence and the unrelated repository-closure sentence share one long line (cosmetic).
- [strength][impl] skills/tdd-loop/test_tdd.py:1052-1057 — the test extracts the wrapper from the published document by its marker, so document and test cannot drift.
- [strength][impl] skills/tdd-loop/test_tdd.py:1036,1128-1140 — the noisy fixture and the two-direction stale-report test each fail if their guarded behaviour is removed.
- [strength][impl] skills/tdd-loop/tdd.py:67-75 — the absolute recipes path is on an earlier line, keeping the quoted last line within 300 characters.
- [strength][impl] skills/tdd-loop/test-command-recipes.md:4-5 — the ADR is linked by GitHub URL, so the link works in a consuming project.

RECONCILIATION NOTES:
- Fix or record the "line 1" wording in the hint.
- Filter `JIG_GRADLE*` in the end-to-end recipe test.
- The "deleting reports forces a Gradle re-run" assumption stays unverified; the wrapper fails closed if it is wrong. A run whose only selected test is skipped comes out green; the document states this.
- Several new tests check exact wording in SKILL.md and the recipes document; rewording will need the tests updated.
