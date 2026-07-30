---
bug: 017
pass: bug-review
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-07-30T17:18:54Z
prompt_source: review.py bug-review docs/bugs/017-record-review-blocks-on-stdin.md
---

VERDICT: pass

REASONING:
All four issues from the first (needs-changes) round are fixed and verified in
the tree: the `record-review` parser description now states the body is
required and that "stdin is never read implicitly (bug 017)"; the code-health
comment no longer says "(or stdin)"; `adr.py`'s accept-gate refusal now
includes `--summary-file <path>`; and `_record_adr_review` catches
`ReviewError` locally, matching the bug/slice recorders. The blank-body
conjunct is correctly gated on `required` and returns early for
`required=False`, so the code-health graceful degrade (spec 060-05 AC2) is
untouched, and no in-repo caller records a legitimately empty body. The
regression tests keep their teeth: the pipe test still hangs against the
unfixed helper and now also pins `returncode == 2`; the blank-body test would
have exited 0 with a recorded verdict pre-fix. Host mirrors carry the
identical lines.

SPECIFIC ISSUES:
(none outstanding — the round-1 issues below were fixed and re-verified)
- review.py parser description — stale implicit-stdin contract. FIXED.
- adr.py:955 — refusal printed a command that would now exit 2. FIXED.
- review.py code-health comment "(or stdin)". FIXED.
- _record_adr_review except tuple missing ReviewError. FIXED.
- bug record miscounted the regression tests (three vs four). FIXED.

RECONCILIATION NOTES:
- CLI contract change: `record-review` now requires a non-blank body on all
  three targets (slice, `--adr`, `--bug`) — wider than the hang fix. Stated
  plainly in the bug record's Fix section.
- Enforcement is uniform rather than gated on `isatty()`, a deliberate
  widening of the maintainer's "force a body when non-interactive" direction;
  rationale recorded (an `isatty()` fork is the defect class).
- Slice 045-02 shipped "body is optional" as logged behaviour; that claim is
  now false and carries an ADR-0010 `## Amendments` entry, as does slice
  060-05 for the code-health degrade.
- Bug board regenerated at close.
