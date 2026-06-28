---
slice: 072-02 — unscaffolded-suggestion
pass: craft
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-06-27T20:49:29Z
prompt_source: review.py pr-review docs/specs/072-servo-pull-hint/spec.md 072-02 <deliverables> (richer ~/.claude/skills/pr-review applied)
---

VERDICT: pass

REASONING:
Craft is solid and faithfully mirrors the established 072-01 helper pattern
(module banner, _SERVO_* path tuples, filesystem-only probes, pure render_* +
side-effect-isolated writer). The _output_is_interactive seam is a clean,
stubbable named function with a defensive try/except; the once-per-project
budget is consumed only on an interactive land and the marker write is genuinely
best-effort (OSError swallowed, exit code unperturbed). Tests cover every DoD
edge case incl. shown!=seen, schema mismatch, unparseable marker, opt-out,
mutual exclusion with .servo/, and the write-failure best-effort path with an
exit-code-equality assertion. No blockers.

SPECIFIC ISSUES:
- [strength] skills/slice-land/land.py — _output_is_interactive is a clean,
  documented seam (defensive try/except on closed/replaced stdout) that makes
  the AC6 "shown != seen" logic testable without a real TTY.
- [strength] skills/slice-land/land.py — render_servo_suggestion is kept pure
  (write deferred to the caller, gated on interactivity); guard ordering is
  clear and mutual exclusivity with the 072-01 advisory prevents a double
  `## servo` header.
- [strength] skills/slice-land/test_land.py — best-effort and never-changes-exit
  tests assert against a baseline exit code rather than a hardcoded value.
- [nit] backslash line-continuation in _servo_available — FIXED inline (wrapped
  in parens).
- [nit] `target or Path.cwd()` computed twice in prepare — FIXED inline (single
  shared `servo_target` local now feeds both advisory and suggestion).
- [nit] test helper `raw: str = None` non-Optional annotation — FIXED inline
  (dropped the annotation; `str | None` avoided to stay Python-3.9-safe per the
  repo floor).

RECONCILIATION NOTES:
- Known residual (already in the slice, frame-critique round 3): AC6's isatty()
  is a fail-open proxy — non-TTY harness/pty runs re-fire the nudge until
  .jig/no-servo-hint is dropped. Deliberate (unobserved budget burn is
  unrecoverable; re-nudge is one line + one-file opt-out). Carry into the
  deviation log verbatim as the accepted trade-off.
- .jig/servo-hint-shown is gitignored both in the repo's own .gitignore and in
  scaffold's generated _GITIGNORE_SECRET_PATTERNS (the repo dogfoods the
  scaffold) — consistent with the semantic-index/no-servo-hint precedent. Note
  in the deviation log that the tuple now mixes secret + local-state entries.
