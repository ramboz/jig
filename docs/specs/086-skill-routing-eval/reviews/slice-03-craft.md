---
slice: 086-03 — register the eval as a named ci_check gate
pass: craft
verdict: pass
reviewer: pr-review skill (general-purpose subagent)
reviewed_at: 2026-07-08T19:13:12Z
prompt_source: review.py pr-review 086-03 (re-review)
---

Craft pass (pr-review methodology, fresh-context general-purpose subagent;
re-review after the gate-ordering fix). PASS — no blockers.

Small, focused integration slice. The gate is ordered FIRST so a regression
fails a NAMED step, the Python gate single-sources its floor from
skill_routing.MIN_RANK1_RATE, and the new test asserts the failure is NAMED
(stdout contains "Skill-routing eval"), not just a stop-on-first-failure smoke
test.

Strengths:
- [strength] Routing gate placed FIRST so a regression fails the named step, not
  the anonymous "Run test suite"; WHY documented inline.
- [strength] Floor single-sourced from skill_routing.MIN_RANK1_RATE in the
  Python gate; the argv test pins against the module constant.
- [strength] The regression test checks stdout contains "Skill-routing eval" —
  guards the named-failure property that is the point of the slice.
- [strength] Honest inline note that the roster test does not parse ci.yml and a
  real parity guard is a follow-up — good tech-debt discipline.

Nits (→ deviation log):
- [nit] ci.yml:51 hardcodes the 0.85 floor, duplicating MIN_RANK1_RATE; the
  "can't lag a ratchet" invariant holds only for ci_check.py. Backstopped by the
  suite. Add a parity assertion or annotate the YAML step to point at the
  enforcing test.
- [nit] test_ci_check.py comment says it "induces a routing regression"; it
  induces a step failure exercising the wiring (the real regression lives in
  test_skill_routing.py). Tighten the wording.
- (out of scope, pre-existing) ci_check.py "Code-health floor" vs ci.yml
  "Code-health floor (ruff)" name divergence — corroborates the parity-guard
  follow-up.
