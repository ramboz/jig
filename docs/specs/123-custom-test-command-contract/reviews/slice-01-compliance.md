---
slice: 123-01 — exit-contract
pass: compliance
verdict: needs-changes
reviewer: jig:reviewer
reviewed_at: 2026-11-21T02:50:06Z
prompt_source: review.py implementation docs/specs/123-custom-test-command-contract/spec.md exit-contract <7 deliverables>
---

VERDICT: needs-changes

REASONING:
The production code meets every AC. In `tdd.py`, `_custom_exit` maps everything except 0 and 1 to 2 and prints one contract line of about 230 characters as the last stderr line, in both branches. The selector branch checks the no-match line only on exit 1. Parse errors, undecodable output and helper crashes all exit 2. In `land.py`, `could_not_run` is separate from `warn`/`red`/`not_run`, a blank `.jig/test-command` counts as a declared runner, the row quotes `tdd.py`, and `has_blocker` goes through `tests_block`. The bug-fix gate tests run the real `tdd.py`. Two AC7 sub-claims are not proven by tests: one test can pass with the feature removed, and nothing checks the final verdict end to end. One docstring contradicts the contract.

SPECIFIC ISSUES:
- skills/slice-land/test_land.py — `test_could_not_run_keeps_the_servo_suggestion_silent` depends on the machine: with no servo marker, `render_servo_suggestion` returns "" whether or not `"could_not_run"` is in the silent tuple. Use the 072-02 fixture (XDG_STATE_HOME + marker).
- skills/slice-land/test_land.py — AC7 says "the verdict is not GO", but no test runs `prepare()` with `could_not_run` and asserts exit 1; reverting `has_blocker` to `test_status == "red"` keeps every test green.
- skills/tdd-loop/test_tdd.py — the class docstring says "any other non-zero status stays red", the opposite of the contract tested.
- skills/slice-land/land.py — the COULD NOT RUN row always says "a test runner was detected"; for a blank `.jig/test-command` `detect` found none. Minor.
- skills/slice-land/test_land.py — `_custom_command` puts `sys.executable` in the command without `shlex.quote`. Robustness nit.

RECONCILIATION NOTES:
- The reason reaches the report through a module-level global `_could_not_run_detail` instead of a wider `check_tests` return; record in the deviation log.
- `land.py` (file presence) and `tdd.py detect` classify a blank `.jig/test-command` differently; record it.
- The `REVIEWED` green check is deliberately unchanged (bug 043); confirm in the deviation log.
