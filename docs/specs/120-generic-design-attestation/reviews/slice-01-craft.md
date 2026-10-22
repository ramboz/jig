---
slice: 120-01 — attest generic static evidence
pass: craft
verdict: pass
reviewer: reviewer
reviewed_at: 2026-10-22T19:45:23Z
prompt_source: review.py pr-review; native craft plus independent recovery
substrate: shown
applied_skill: scout-pr-review
shown_candidates: [arch-review:high-confidence, independent-review:high-confidence, pr-review:high-confidence, scout-pr-review:high-confidence, access:speculative, adr-workflow:speculative, agent-development:speculative, analyze:speculative, bug-fix:speculative, build-mcp-app:speculative, build-mcp-server:speculative, build-mcpb:speculative, cardputer-buddy:speculative, clarify:speculative, claude-automation-recommender:speculative, claude-md-improver:speculative, code-health:speculative, command-development:speculative, configure:speculative, contracts:speculative, example-command:speculative, example-skill:speculative, explain:speculative, frontend-design:speculative, hook-development:speculative, m5-onboard:speculative, math-olympiad:speculative, mcp-integration:speculative, memory-sync:speculative, migrate:speculative, orient:speculative, playground:speculative, plugin-settings:speculative, plugin-structure:speculative, project-artifact:speculative, reframe:speculative, scaffold-init:speculative, scout-autotune:speculative, scout-bench-create:speculative, scout-memory-init:speculative, scout-scrum-master:speculative, security-review:speculative, session-report:speculative, skill-creator:speculative, skill-development:speculative, slice-land:speculative, spec-workflow:speculative, tdd-loop:speculative, vision-elicitation:speculative, writing-hookify-rules:speculative]
---

VERDICT: pass

REASONING:
Full native-delta craft cleared explicit alias membership and ordinary
no-follow reads, with meaningful positive/refusal coverage. It found a
multiline indexed roster write that defeated assignment-pattern counting.
The independent recovery returned VERDICT: pass for the final root correction:
one original-byte literal array and no other non-comment COMPONENTS reference
after lexical continuation normalization. The finite supported profile no
longer needs to enumerate shell assignment forms or execute a driver.

SPECIFIC ISSUES:
- [strength][impl] static_design_bindings.py:759-768: closed outside-reference
  boundary replaces assignment-pattern enumeration without Bash execution.
- [strength][impl] test_static_design_bindings.py:840-854: changed driver is
  repinned before freshness/public recording refusal is tested.

RECONCILIATION NOTES:
The review note to correct deviation item8 was applied: it now describes the
final no-other-reference restriction and both red/green regressions.
No additional scope deviation or scoring/native-authority drift. Final Servo
cut and real application approval are not established by this pass.

### 2026-10-22 — post-review dependency resolution

The separate final code-correspondence check is now complete for reviewed
Servo `a62a475` and fresh two-epoch carriers; see slice deviation item 5.
This preserves the craft pass's original scope: byte correspondence is not
retrospective acquisition approval or real application approval/DONE.
