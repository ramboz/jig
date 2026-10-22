---
slice: 119-04 — static-source-compatibility
pass: arch
verdict: pass
reviewer: reviewer:static-architecture
reviewed_at: 2026-10-21T16:27:48Z
prompt_source: review.py arch-review spec119 119-04 --richer-skill arch-review
substrate: shown
applied_skill: arch-review
shown_candidates: [arch-review:high-confidence, access:speculative, adr-workflow:speculative, agent-development:speculative, analyze:speculative, bug-fix:speculative, build-mcp-app:speculative, build-mcp-server:speculative, build-mcpb:speculative, cardputer-buddy:speculative, clarify:speculative, claude-automation-recommender:speculative, claude-md-improver:speculative, code-health:speculative, command-development:speculative, configure:speculative, contracts:speculative, example-command:speculative, example-skill:speculative, explain:speculative, frontend-design:speculative, hook-development:speculative, independent-review:speculative, m5-onboard:speculative, math-olympiad:speculative, mcp-integration:speculative, memory-sync:speculative, migrate:speculative, orient:speculative, playground:speculative, plugin-settings:speculative, plugin-structure:speculative, pr-review:speculative, project-artifact:speculative, reframe:speculative, scaffold-init:speculative, scout-autotune:speculative, scout-bench-create:speculative, scout-memory-init:speculative, scout-pr-review:speculative, scout-scrum-master:speculative, security-review:speculative, session-report:speculative, skill-creator:speculative, skill-development:speculative, slice-land:speculative, spec-workflow:speculative, tdd-loop:speculative, vision-elicitation:speculative, writing-hookify-rules:speculative]
---

VERDICT: pass

REASONING:
The bounded 119-04 additions preserve ADR-0065’s ownership: producers supply verdicts; Jig checks preserved identities and currentness through the existing opt-in review rail. The package-local split is justified by the complete source/policy/runtime/run/output/delivery requirements; no substantially simpler architecture is evident without weakening them, and no genuinely new load-bearing decision requires another ADR. Guidance and proof consistently limit authority to finite static declarations, while the final source, tests and three host copies contain the screenshot repair.

SPECIFIC ISSUES:
- [strength][impl] skills/_common/design_bindings.py:275 — Explicit incompatible-schema dispatch preserves the legacy validator and shared strict reader without adding evaluator dependencies, discovery or lifecycle gates.
- [strength][impl] skills/_common/static_design_bindings.py:229 — Producer links must land in already rehashed inventories; closed browser membership and literal alias identities do not broaden ordinary symlink traversal authority.
- [strength][impl] skills/independent-review/review.py:1591 — Prompt separates native overall authority from component diagnostics and explicitly retains independent compliance’s authority and finite-scope exclusions.

RECONCILIATION NOTES:
No architectural deviation or additional ADR is warranted by this package-local implementation. Retain the documented trusted-local/root-selection and host-loader limitations, evidence-category distinctions, and archived nonpass/repair history during reconciliation.

> Publication cleanup (2026-10-22): the reference to the withdrawn mixed-app
> proof document was removed at the owner's explicit request. The original
> review remains privately archived; this is an edited export, not a new review.
