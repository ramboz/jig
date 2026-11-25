---
slice: 123-01 — exit-contract
pass: compliance
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-11-21T02:55:04Z
prompt_source: review.py implementation docs/specs/123-custom-test-command-contract/spec.md exit-contract <7 deliverables>
---

VERDICT: pass

REASONING:
Round 3 (round 1 and round 2 returned needs-changes; their findings are folded in and listed in the slice deviation log, items 7 and 8). Every acceptance criterion for 123-01 is met in the current tree. `_custom_exit` maps only 0 and 1 straight through and turns everything else into exit 2, with a single contract line on stderr (about 230 characters). Both custom branches route through it, and the no-match check runs only on exit 1, so exit 2 reports the contract line first. Each AC6a path exits 2: an unparsable file, undecodable output (`errors="replace"`) and a helper crash in `main`. In `land.py`, `check_tests` adds `could_not_run` for a detected or declared runner, `tests_block` feeds `has_blocker`, the readiness row quotes `tdd.py`'s reason, and the servo suggestion stays silent for the new status.

The tests run the real `tdd.py` for AC1-6, AC6a and AC7, and cover the listed edge cases: a killed command (SIGKILL), exit 2 plus a no-match line, a blank or comment-only file, and the pytest module missing (a shadowing module). None is vacuous: removing the feature turns each one red. No test-quality signal fired.

SPECIFIC ISSUES:
- skills/slice-land/land.py:628-631 — Low/nit: the blocker line says "exit 2 with a runner detected"; the readiness row says "detected or declared". Optional wording alignment.
- skills/slice-land/land.py:311-314,340-365 — Medium (design, already recorded in deviation 2): the reason travels in the module-level global `_could_not_run_detail`. Works for the one in-process caller and its reset is tested; accepted and recorded, so not blocking.

RECONCILIATION NOTES:
- The deviation log records the main departures (polarity, slice-land scope, AC6a, blank file as declared runner, global detail, `errors="replace"` covering built-in targeted runs, the D4 behaviour change).
- Optionally note that the `render_blockers` wording was narrower than the row's.
- AC5's "selector without `{test}`" part is covered by the existing bug 021 test, not a new Spec123 test.
