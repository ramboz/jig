---
slice: 096-01 — orientation reports work in flight
pass: reconciliation
verdict: pass
reviewer: jig:reviewer subagent (reconciliation pass; all 7 findings applied)
reviewed_at: 2026-07-23T05:09:13Z
prompt_source: review.py reconciliation docs/specs/096-orient-sees-work-in-flight/spec.md orientation
---

Reconciliation pass returned **needs-changes** with seven findings. Its job was
to check the *record*, not the code — and it earned its place: four of the seven
were artifacts disagreeing with the written account, and one was a genuinely
vacuous test that both compliance rounds had missed.

## Applied

1. **Status board was stale.** It still read `IN_PROGRESS (claude/orient-…)` for
   096-01 after the REVIEWED transition had cleared the claim. The sweep claimed
   "regenerated" — true of a pre-transition run, but the artifact it pointed at
   was already wrong. Regenerated after the transition.
2. **"Reconciliation review passed" was ticked before this review existed.** That
   box is ticked by the RECONCILED transition, not by hand; ticking it early
   asserted a gate that had not been passed — the one this pass was deciding.
   Un-ticked.
3. **New-test count was wrong: 27, should be 30.** 19 in `OrientWorkInFlightTests`
   + 11 in `test_orient_skill_surface.py`. The 27 was the round-1 figure carried
   forward, and the parenthetical "less the 3 that replaced vacuous ones" was a
   post-hoc rationalisation of a stale number — those three live *inside* the 30.
4. **`test_long_branch_name_is_capped` did not test the cap.** It asserted
   `len(headline) < 400`; a 201-character branch renders ~309 chars, so it passed
   with `_ORIENT_IN_FLIGHT_REF_MAX` deleted. Same defect class round 1 caught
   three times — it slipped through because the mutation re-check had been scoped
   only to those three. Now pins the boundary (`MAX` survives, `MAX+1` does not),
   and the slice's test plan says so.
5. **`SKILL.md`'s headline template still showed three fields** with no
   `· in flight:`, while the body 80 lines below told the reader to expect it. The
   sweep's docs-consistency bullet had covered the `orient()` docstring and the
   frontmatter description but missed this. Fixed in source and both host mirrors.
6. **Evidence miscount** in the compliance record ("two claims" followed by
   three). Corrected.
7. **The compliance frontmatter implied an independent re-pass that never
   happened.** Round 2 returned needs-changes; its two new defects and the PARTIAL
   were closed by the *implementer*, with no round-3 artifact. The record now says
   so explicitly under "Who verified what", and deviation entry 12 states the
   general limitation: all three reviewers were read-only, so every executable
   claim was verified by the implementer.

## Recorded

Deviation entries **10** (the vacuous cap test) and **11** (the four record
corrections) were added, so the log now accounts for what this pass changed
rather than absorbing it silently.

## What this pass confirmed

Deviation entries 1–8 each match the code as read. `hosts/**` are line-for-line
identical to their sources including the Codex `${PLUGIN_ROOT}` rewrite, with
tests correctly excluded. AC3's aggregate wording matches `_in_flight_summary`'s
single deadline; AC9 matches `_sanitize_orient_ref`. AC5–AC8 are all present in
`SKILL.md` and pinned by the surface tests. It found no scope creep among the
files it could tie to the slice.

## Limitation of this pass

Read-only tools, so it could not run `run_tests.py`, `git diff`,
`build_host_packages.py --check`, `spec_lint.py`, or the mutation check. Those
were verified by the implementer and are reported in the sweep. Post-fix state:
`Ran 3527 tests … OK (skipped=4)`, `pyright: clean`, host packages in sync, spec
lint clean, and `git diff origin/main -- skills/spec-workflow/test_workflow.py`
still has zero deletion lines.
