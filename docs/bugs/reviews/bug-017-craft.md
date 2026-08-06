---
bug: 017
pass: craft
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-07-30T17:18:54Z
prompt_source: pr-review skill craft pass
---

VERDICT: pass

REASONING:
Both round-1 blockers are closed: the `record-review` parser description now
states the required-body contract and "stdin is never read implicitly (bug
017)", and `adr.py` emits a copy-pasteable command including
`--summary-file <path>`. Both host mirrors carry the new strings, so the
rebuild was run. The blank-body tightening moves enforcement from "did you
type the option" to "is there a body", making SKILL.md's claim literally true,
and the new test is not vacuous: delete the `if required and not body.strip()`
guard and the command records the verdict and exits 0, failing all three of
its assertions. The remaining round-1 nits are all applied.

SPECIFIC ISSUES:
- [strength] review.py `_read_summary` — the restructure into `body = ...`
  plus a single post-resolution blank check keeps one enforcement point for
  all three sources (path, `-`, absent) instead of duplicating it per branch;
  `required=False` short-circuits before the check, so code-health's AC2
  degrade is provably untouched.
- [strength] test_review.py `test_blank_body_is_refused_like_a_missing_one`
  asserts the distinct "empty verdict body" string rather than reusing the
  missing-option assertion, so the two refusal paths cannot silently collapse.
- [nit] bug record wording around the missing-option vs blank-body bullets
  read oddly together. FIXED after the review.

RECONCILIATION NOTES:
- Contract change to log: `--summary-file /dev/null`, an empty file, and
  `--summary-file -` fed an empty pipe now all exit 2 where they previously
  recorded frontmatter-only evidence.
- Deviation worth keeping visible: enforcement is uniform rather than gated on
  `isatty()` — a deliberate widening of "force a body when non-interactive";
  the rationale (an `isatty()` fork is the defect class) is in the record.
- Out-of-changeset file touched for a good reason: `skills/adr-workflow/adr.py`
  (plus its two host mirrors) — the gate hint had to change or the tool would
  keep advertising a command that fails.
