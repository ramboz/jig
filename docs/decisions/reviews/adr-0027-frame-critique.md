---
adr: 0027
pass: frame-critique
verdict: pass
reviewer: codex-orchestrator
reviewed_at: 2026-06-22T02:31:42Z
prompt_source: python3 /Users/ramboz/.codex/plugins/cache/jig/jig/2.0.0-rc.2/skills/independent-review/review.py frame-critique docs/decisions/adr-0027-host-native-phase-modes.md
---

REASONING:
The highest-risk assumption is that host-native planning/implementation modes are useful enough, and sufficiently stable across Codex and Claude, to deserve jig-facing guidance. Current official docs support a narrow version of that frame: both hosts expose planning/read-before-edit affordances, but they differ in permission semantics and should not be treated as durable state. The ADR survives if implementation remains advisory prose/host-adapter rendering and never turns host mode into transition evidence.

SPECIFIC ISSUES:
- Host mode stability and portability — Product-owned mode labels and permissions can change independently in Codex and Claude Code; if jig encoded them as gates or machine-readable truth, future host changes would misdirect specs 074-02/074-03 and create a second lifecycle source of truth. ADR-0027 explicitly rejects that by keeping artifacts canonical, requiring fresh verification before implementation, and limiting mode use to advisory hints.
