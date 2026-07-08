---
slice: 086-03 — register the eval as a named ci_check gate
pass: compliance
verdict: pass
reviewer: general-purpose
reviewed_at: 2026-07-08T19:13:12Z
prompt_source: review.py implementation 086-03 (re-review)
---

Compliance pass (fresh-context general-purpose subagent; re-review after the
gate-ordering fix). PASS — all four ACs met.

AC1: ci_steps() lists "Skill-routing eval" as an explicitly named FIRST step
invoking skill_routing.py --min-rank1 with the floor single-sourced from
skill_routing.MIN_RANK1_RATE; run_steps prints the name. AC2: the routing gate
runs FIRST (before the anonymous "Run test suite" that would also trip on the
floor via test_skill_routing.py), and test_routing_regression_fails_named_gate_
before_suite induces a routing-step failure and asserts run_steps stops at the
named gate (rc=1, len(ran)==1, "Skill-routing eval" in output); the order is
itself guarded by test_ci_steps_roster_and_order; both ci_check.py and ci.yml
place the step first. AC3: routing gate exits 0 on the current tree; all 4
wiring tests pass. AC4: zero new deps (stdlib + sibling import), py39-safe,
test-covered.

Non-blocking follow-ups (→ deviation log + refinement-todo at reconciliation):
- ci.yml:51 hardcodes --min-rank1 0.85 (a YAML step can't import), so it can lag
  a future MIN_RANK1_RATE ratchet; backstopped by the suite's own floor check.
- test_ci_check.py:14-16 forward-references a "logged follow-up" for a real
  ci_check<->ci.yml parity guard that is not yet in refinement-todo, and the
  slice-03 deviation log is still a TODO placeholder — make the reference true by
  adding the parity-guard entry during reconciliation.
