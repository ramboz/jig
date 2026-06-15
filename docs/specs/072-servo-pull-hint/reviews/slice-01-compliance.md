---
slice: 072-01 — present-infra-hint
pass: compliance
verdict: pass
reviewer: jig:reviewer subagent (read-only)
reviewed_at: 2026-06-15T17:13:41Z
prompt_source: review.py implementation 072-01
---

VERDICT: pass

REASONING:
All six acceptance criteria for slice 072-01 are met by `render_servo_advisory` (land.py:491-524) and its integration in `prepare` (land.py:604-612), which appends the advisory strictly *after* `has_blocker` is computed from `checks` alone (land.py:574-579) — so it provably cannot alter the exit code. Detection is filesystem-only (`.exists()`/`.glob()`/`.stat()`; no subprocess, no servo invocation), the opt-out marker is checked first, and the advisory names servo's post-ADR-0008 `/goal`-driven / Routine-triggerable shape with a resumable-run path while never saying "hand-rolled." `ServoAdvisoryTests` (test_land.py:2087-2317) exercises each AC meaningfully — including AC2's case-insensitive "zero servo substring" assertion (sound because no-mode `prepare` renders only the slice label, not the tmpdir path), AC4's identical-exit-code + `startswith` append-only check, and AC5's subprocess-raises isolation. Faithful to the spec's loosest-possible, advisory-text-only, Option-D-binding-stays-PARKED approach. No principle violations.

SPECIFIC ISSUES:
(none)

RECONCILIATION NOTES:
- No deviations from the planned slice shape. The `.servo/oracle.sh` presence signal (land.py:463) is named in the slice's AC1 but not in spec.md Assumptions (which names only `.servo/install.json`); within slice scope, not a deviation, but worth a one-line note in the deviation log for traceability.
- Slice DoD review/reconciliation items correctly still unticked at compliance time.
- Close-out items (ADR-0022 Scope/Status, status-board Notes, slice-land Skills-table row) remain for the reconciliation/close-out phase per the slice's `### Close-out (post-DONE)` block.
