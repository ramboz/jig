---
status: DONE
tier: standard
severity: medium
claimed_by: main
regression_test: skills/slice-land/test_land.py::PrepareBranchFreshnessWarningTests::test_prepare_warns_when_branch_behind_origin_main
main_repro_checked_at: 2026-06-29
main_repro_ref: origin/main@05a2e57
main_repro_result: reproduces
red_confirmed_at: 2026-06-29
green_confirmed_at: 2026-06-29
fix_class: guardrail
security_surface: false
escalated_to:
---

# Bug 001: branch-freshness-preflight

## Symptom

GitHub issue #62 reports that long-lived feature worktrees can be many commits
behind `origin/main`. Review/reconcile test runs then happen against a stale
base, so failures may be misclassified as "pre-existing bugs on main" even when
fresh `origin/main` is green.

## Repro

1. Work a slice on a feature branch that has not merged or rebased the latest
   `origin/main`.
2. Run `land.py prepare` or transition the slice through REVIEWED/RECONCILED.
3. Observe that the workflow reports readiness/evidence state but does not warn
   that `HEAD..origin/main` is non-empty, leaving stale-base test failures easy
   to misattribute.

## Evidence

- `skills/slice-land/land.py` already protects live direct landing with
  `_check_ff_viable()`, which fetches and checks `origin/main` before push.
- `prepare()` only runs readiness checks and renders next steps; it does not
  compute branch freshness before presenting test results.
- `workflow.py transition` gates REVIEWED/RECONCILED evidence, but emits no
  stale-base warning before those phase changes.

## Hypotheses

- [x] **Missing advisory guardrail.** The direct landing push is safe, but
   the human interpretation phases do not surface branch divergence, so stale
   test output can be diagnosed as a main failure.
   - Confirm by adding a regression test that `prepare()` appends a warning
     when `HEAD..origin/main` is non-zero.
   - Falsify if `prepare()` or REVIEWED/RECONCILED transitions already call an
     origin/main divergence check.
- [ ] **Existing `stale` audit should cover it.** The doc freshness
   audit may be expected to catch this.
   - Falsified by `workflow.py stale` operating on `last_verified` plus
     dependency modification dates, not branch graph divergence.

## Root cause

The origin-aware safety added for direct landing is located at the push
boundary, after review/reconcile have already interpreted test failures.
`prepare()` and the REVIEWED/RECONCILED transitions have no soft
`HEAD..origin/main` preflight, so stale-base test results are presented without
the context needed to avoid false "main is broken" findings.

## Fix class

guardrail

## Fix

Add a best-effort branch-freshness warning that fetches `origin/main`, counts
`HEAD..origin/main`, and reports a non-blocking warning when the current branch
is behind. Surface it in `land.py prepare` and on REVIEWED/RECONCILED
transitions; keep live landing's existing hard fast-forward guard.

## Already tried

- 2026-06-29 - green check failed for `skills/slice-land/test_land.py::PrepareBranchFreshnessWarningTests::test_prepare_warns_when_branch_behind_origin_main` (tdd.py exit 1)
  because the sandboxed full runner passed unittests but failed pyright/uv cache
  access. Re-ran the REVIEWED gate with escalated permissions so `uvx pyright`
  could read its cache; the gate then passed and stamped `green_confirmed_at`.

## Regression test

`skills/slice-land/test_land.py::PrepareBranchFreshnessWarningTests::test_prepare_warns_when_branch_behind_origin_main`

## Proof

- Red gate: `bug.py transition 001 FIXING` witnessed the regression red and
  stamped `red_confirmed_at: 2026-06-29`.
- Focused green checks:
  - `python3 -m unittest test_land.PrepareBranchFreshnessWarningTests`
  - `python3 -m unittest test_workflow.TransitionBranchFreshnessWarningTests.test_reviewed_emits_branch_freshness_warning_without_blocking`
  - `python3 scripts/build_host_packages.py --check`
- Green gate: `bug.py transition 001 REVIEWED` passed under escalated
  permissions and stamped `green_confirmed_at: 2026-06-29`.

## Learning

When review/reconcile tests fail on a long-lived worktree, check whether the
branch contains freshly fetched `origin/main` before recording the failure as
"pre-existing on main." A soft `HEAD..origin/main` warning catches the stale-base
misdiagnosis without blocking offline/local-only workflows.

## Main recheck

- 2026-06-29 - `origin/main@05a2e57` -> reproduces: focused tdd selector errors because land.py lacks _branch_freshness_warning; prepare has no branch freshness section
