---
status: REPORTED
tier:
severity: medium
claimed_by:
regression_test:
main_repro_checked_at:
main_repro_ref:
main_repro_result:
red_confirmed_at:
green_confirmed_at:
fix_class:
security_surface: false
escalated_to:
closure_schema: 1
---

# Bug 043: reviewed-gate-env-error-reopens-bug

Reported: found while implementing spec 123 (issue 250), 2026-11-20. Not fixed there by the owner's instruction.

## Symptom

At `→ REVIEWED`, `bug.py` treats every non-zero `tdd.py` exit as a failed
fix, including exit 2 (environment error: the test could not be run). It sets
the record back to `DIAGNOSING`, stamps the review-reopened field (which makes
recorded review verdicts stale) and appends "green check failed" to
`## Already tried`. The `→ FIXING` gate already separates the two cases
("environment error … not evidence of red", no mutation). Since spec 123 /
ADR-0068 a custom command is told to exit 2 on purpose for a build failure or
a missing tool, so a transient environment failure at `REVIEWED` now discards
review evidence and writes a false "fix attempt failed" entry.

## Repro

Code reading (`skills/bug-fix/bug.py`, the `new_status == "REVIEWED"` arm:
`if result.returncode != 0:` → `DIAGNOSING`). A fixture exists:
`Bug021GateSurfacesTargetingRefusalTests.test_reviewed_green_failure_surfaces_tdd_report`
feeds an exit 2 ("unresolved selector") and asserts the record lands in
`DIAGNOSING`.

## Evidence

- Raised by the frame critique of slice 123-01 (2026-11-20).
- Not changed in spec 123: the back-edge on a failed green check is part of
  the bug lifecycle ([ADR-0016](../decisions/adr-0016-bug-fix-lifecycle.md)),
  and the bug 021 test above pins exit 2 → `DIAGNOSING` as the current
  behaviour. Changing it needs its own diagnosis: is an unresolved selector
  at `REVIEWED` a failed fix (the test was renamed or deleted) or an
  environment error?

## Hypotheses

<!-- Anti-anchoring: >=2 candidates, mark the leading one. Any Markdown
     list works (-, *, +, or 1.); the gate counts top-level items only
     (indented sub-bullets are notes, not hypotheses). -->
- [ ] H1: <alternative explanation>, falsify by <check>
- [x] H2 (leading): <leading explanation>, confirm by <check>

## Root cause

## Repository closure inventory

<!-- Spec 091 / ADR-0037: pre-fix repository closure. Standard & gnarly
     bugs gate ROOT_CAUSED -> FIXING on substantive answers below. This
     is an effort-and-protocol standard, NOT a completeness proof: show
     the search you actually ran. A bare "none found" fails; record
     residual uncertainty as an assumption WITH the protocol behind it,
     applying the same enumeration standard as `## Root cause` (ADR-0052).
     Prefer a configured semantic index; the portable floor is targeted
     search + `git log`/`git blame`. -->

**Equivalent / convergent logic searched:**

**Relevant history inspected:**

**Affected call sites:**

**Reuse decision:**

## Fix class

## Fix

## Call-site closure

<!-- Spec 091 / ADR-0037: before REVIEWED, account for every site named
     in the inventory above as changed, tested, or intentionally left
     alone. Accounting, not mandatory widening. -->

**Disposition per affected site:**

## Already tried

## Regression test

## Proof

## Learning
