---
adr: 0049
pass: frame-critique
verdict: pass
reviewer: jig:reviewer (fresh, 2 rounds)
reviewed_at: 2026-08-03T17:52:48Z
prompt_source: review.py frame-critique docs/decisions/adr-0049-...md
---

Adversarial frame-critique of ADR-0049 (two rounds, fresh independent reviewers each).

Round 1 (needs-changes): the original "route to the ORIGINATING spec" frame silently
assumed every design-fidelity gap has an originating jig spec, and dead-ended the #179
trigger (a mockup-first cross-platform rebuild with NO spec). Secondary: "never DONE"
was retroactive fiction; fidelity-vs-refinement had no operational test; spec 071 "DONE"
overstated (overview table shows 071-01 IN_PROGRESS).

Revision: routing broadened to the spec spine for BOTH provenances (originating spec when
one exists; a NEW greenfield spec with the mockup as design-value ACs when none does);
added the operative fidelity-vs-refinement test (does the visual target change?); grounded
the 071 rail on the code deriver (workflow.py:330) rather than the drifted headline status;
Assumptions now records servo-availability + the 071 drift honestly.

Round 2 (PASS): the revised frame survives. Both provenances land in spec-workflow (no new
vehicle); routing tests are honestly framed as judgments, not gates. One cheap tightening
adopted: added an ambiguous-case tie-breaker to decision point 2 (an ambiguous-but-functional
gap defaults to the spine; reserve bug-fix for a confirmed behavioral malfunction). Reviewer
also noted spec 071's overview-table drift as a non-load-bearing open cleanup on 071 itself.
