---
status: RESOLVED_ON_MAIN
tier: standard
severity: medium
claimed_by: claude/github-issue-187-fix-6836d0
regression_test: skills/spec-workflow/test_workflow.py::TransitionTests::test_slice_path_transition_is_not_overwritten_by_spec_rollup
main_repro_checked_at: 2026-08-04
main_repro_ref: origin/main@eadd8533c8fd2aabfa8bd0a18800638116217174
main_repro_result: resolved_on_main
red_confirmed_at:
green_confirmed_at:
fix_class:
security_surface: false
escalated_to:
---

# Bug 029: slice-path-transition-silent-noop

## Symptom

On **jig 2.5.0**, `workflow.py transition` silently no-ops the frontmatter
`status:` write — while printing a `transitioned … A → B` success line and
exiting 0 — when the first positional (`spec`) argument is a *slice-file* path
(`docs/specs/NNN-slug/slice-NN-*.md`) instead of the `spec.md` path. Because
the write never lands but the command reports success, `status-board` later
renders a reviewed/reconciled/DONE slice as `IN_PROGRESS`, and the state
machine never passes through the intermediate states (every call re-reads the
"from" state as `IN_PROGRESS`). Reported in GitHub issue
[#187](https://github.com/ramboz/jig/issues/187). This is a re-report of the
symptom from the CLOSED [#86](https://github.com/ramboz/jig/issues/86)
(bug 006), observed on a newer version tag.

## Repro

Deterministic minimal repro from the issue — a file-per-slice spec whose
target slice `001-01` is `IN_PROGRESS`, invoked with the *slice file* rather
than `spec.md`:

```bash
WF=<jig>/skills/spec-workflow/workflow.py
export JIG_REVIEW_EVIDENCE_GATE=0
python3 "$WF" transition ".../001-demo/slice-01-thing.md" "001-01" REVIEWED
grep '^status:' .../001-demo/slice-01-thing.md
```

- On **v2.5.0** source: prints `IN_PROGRESS → REVIEWED`, exit 0, but
  `status:` remains `IN_PROGRESS` — the silent no-op. **Reproduces.**
- On current `main`: `status:` advances to `REVIEWED` (and through
  `RECONCILED`/`DONE`, stamping `last_verified`). **Does not reproduce.**

## Evidence

- Ran the issue's exact repro against the **v2.5.0** `skills/` tree
  (`git checkout v2.5.0 -- skills`): `transition <slice-file> 001-01 REVIEWED`
  exited 0 with the success line, on-disk `status: IN_PROGRESS`. Confirms the
  reporter's environment.
- Ran the same repro against current worktree `HEAD` (== `origin/main` @
  `eadd853`): the full `REVIEWED → RECONCILED → DONE` sequence via the
  slice-file path advances `status:` correctly at each step and stamps
  `last_verified: <today>` on `RECONCILED`. Clean on main.
- The fix is the input-normalization boundary added by bug 006: `transition()`
  calls `_canonical_transition_spec_path(spec_md)`
  (`skills/spec-workflow/workflow.py:1223`), which resolves a slice-file path
  to its sibling `spec.md` before `_write_spec_rollup()` runs — so the rollup
  can no longer clobber the just-written slice `status:`.
- Version ancestry: the fix (`a247f76`, *"preserve slice status through
  rollup"*, PR [#87](https://github.com/ramboz/jig/pull/87)) is **not** an
  ancestor of `v2.5.0` (cut 2026-07-03); it first shipped in **v2.7.1**. The
  reporter is on 2.5.0, which predates the fix.
- The existing regression test
  `TransitionTests::test_slice_path_transition_is_not_overwritten_by_spec_rollup`
  drives the slice-file path through REVIEWED/RECONCILED/DONE and asserts the
  slice `status:` advances while the rollup leaves the overview untouched — a
  superset of this issue's single-slice repro. It is **green** on `HEAD`.

## Hypotheses

- [ ] H1: A distinct code path regressed the fix between v2.7.1 and current
      `main`, so the slice-file no-op is live again. Falsify by running the
      issue's exact repro against current `HEAD` and by running the bug-006
      regression test — if `status:` advances and the test is green, no live
      regression.
- [x] H2 (leading): Version skew — the reported symptom is the already-fixed
      bug 006 (#86), and the reporter is on **v2.5.0**, which predates the fix
      (`a247f76`, first shipped v2.7.1). Confirm by reproducing on v2.5.0
      source, confirming clean on fresh `origin/main`, and checking that the
      fix commit is not an ancestor of the `v2.5.0` tag.

## Root cause

Not a live defect on `main`. The reported behaviour is the exact defect fixed
by **bug 006 / issue #86**: before `a247f76`, `transition()` wrote the slice
`status:`, then `_write_spec_rollup()` reinterpreted the *slice-file* path as
`spec.md` and overwrote `status:` back to the computed spec rollup (the
`last_verified` stamp survived because the rollup writes status only). The fix
normalizes the caller-supplied path to the canonical `spec.md` at the command
boundary (`_canonical_transition_spec_path`) before any downstream write.

That fix is present on every release from **v2.7.1** onward, but **absent from
v2.5.0**, the version in the report. The issue therefore reproduces on the
reporter's install and is already resolved on `main`. H2 confirmed; H1
falsified (repro clean on `HEAD`, regression test green).

## Fix class

No source change on `main` — resolved on trunk by the prior `structural_fix`
(`a247f76`, bug 006). Terminal outcome: `RESOLVED_ON_MAIN`. The remedy for
affected users is to upgrade off v2.5.0 (≥ v2.7.1).

## Fix

None required. The slice-file-path input is already normalized at the
`transition()` boundary on `main`; the guard test is present and green.

## Already tried

n/a — root cause established on first diagnosis (version skew, not a live
regression).

## Regression test

Already present and green on `main`:
`skills/spec-workflow/test_workflow.py::TransitionTests::test_slice_path_transition_is_not_overwritten_by_spec_rollup`
(from bug 006). It exercises the slice-file path through REVIEWED → RECONCILED
→ DONE and asserts the slice `status:` advances while the sibling overview is
untouched — covering this issue's scenario. No new test is warranted.

## Proof

- v2.5.0 repro: `transition <slice-file> 001-01 REVIEWED` → exit 0, success
  line, `status: IN_PROGRESS` (reproduces).
- `HEAD` (`eadd853`) repro: same command → `status: REVIEWED`; full
  REVIEWED/RECONCILED/DONE sequence advances and stamps `last_verified`
  (clean).
- `git merge-base --is-ancestor a247f76 v2.5.0` → false (fix not in 2.5.0);
  first tag containing `a247f76` is `v2.7.1`.
- Bug-006 regression test: 1 test green on `HEAD`.

## Learning

A reported defect that carries a version tag older than the fix is a
resolved-on-main re-report, not a live regression — reproduce against *that
version's* source AND against fresh `origin/main`, and check whether the fix
commit is an ancestor of the reported tag, before writing any patch. The
bug-fix ceremony's fresh-main recheck is exactly the gate that catches this:
it routes the work to `RESOLVED_ON_MAIN` instead of manufacturing a duplicate
of an already-shipped fix.

## Main recheck

- 2026-08-04 - `origin/main@eadd8533c8fd2aabfa8bd0a18800638116217174` -> resolved_on_main: Issue #187 repro (transition <slice-file> 001-01 REVIEWED; JIG_REVIEW_EVIDENCE_GATE=0) on fresh origin/main advances status: to REVIEWED (full REVIEWED/RECONCILED/DONE clean); reproduces only on v2.5.0 source, which predates fix a247f76 (PR #87, first shipped v2.7.1). Bug-006 regression test green on HEAD.
