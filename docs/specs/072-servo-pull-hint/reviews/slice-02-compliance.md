---
slice: 072-02 — unscaffolded-suggestion
pass: compliance
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-06-27T20:46:15Z
prompt_source: review.py implementation docs/specs/072-servo-pull-hint/spec.md 072-02 <deliverables>
---

VERDICT: pass

REASONING:
All six acceptance criteria are met and meaningfully tested. The precise-state
conjunction (AC1) is enforced by render_servo_suggestion's five guard clauses
plus _servo_available's JSON+schema check; the per-machine guarantee and
marker-absent silence (AC2) hold; the suggestion is appended after has_blocker
is computed so it never gates (AC3); doc-only suppression keys on
test_status == "warn" (AC4); the path is purely filesystem with no subprocess
(AC5, asserted by stubbing subprocess.run to raise); the once-per-project
budget is consumed only on an interactive isatty() land via a best-effort write
that swallows OSError (AC6). XDG path resolution, mutual exclusion with the
072-01 advisory, and the best-effort failure path are all correct, and every
DoD edge case has a dedicated test.

SPECIFIC ISSUES:
- [nit] test_land.py — second-land test pre-seeded the marker rather than
  chaining two real prepare() calls; best-effort test asserted code in (0,1)
  (trivially true). BOTH ADDRESSED inline post-review: the second-land test is
  now a real write->silence round-trip; the best-effort test asserts exit-code
  EQUALITY against a servo-silent baseline. Re-ran ServoSuggestionTests: 14 green.

RECONCILIATION NOTES:
- Known residual (already in the slice, frame-critique round 3): isatty() is a
  fail-open proxy; under jig's own non-TTY agent-harness mode the budget is
  never consumed so the nudge re-fires until .jig/no-servo-hint is dropped.
  Confirmed implemented as specified; record in deviation log as accepted-by-design.
- .jig/servo-hint-shown lives in scaffold.py's _GITIGNORE_SECRET_PATTERNS (a
  "secret-ignore" block) though it is local state, following the spec-080
  semantic-index precedent in the same tuple. Consistent, but the tuple's name
  no longer fully matches its contents — note in deviation log.
- No new ADR warranted: consumes the existing ADR-0022 §5 reversal already
  sanctioned for the slice-land surface (filesystem-only, no servo invocation).
