---
slice: 122-01 — escalate-stops-the-slice
pass: compliance
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-11-18T03:36:59Z
prompt_source: review.py implementation docs/specs/122-arch-pass-escalation-and-rounds/spec.md 122-01 <6 deliverables>
---

VERDICT: pass

REASONING:
All five ACs for slice 122-01 are met. `escalations()` (`skills/_common/review_evidence.py:499-544`) parses `[blocker]` + `ESCALATE:` entries in order, handles the anchored and bare forms, ignores `[nit]`/`[strength]` entries, other sections and fence lines, joins continuation lines, and returns `[]` with no SPECIFIC ISSUES section. `validate_evidence` still refuses an escalated non-pass arch record with a "person must decide" diagnostic (`:695-704`); other passes keep today's text. `record-review` writes the record unchanged, exits 0 and prints the STOP notice (`review.py:2019-2027`). The arch prompt section (`review.py:1138-1146`) is in both routes, and both SKILL.md recovery texts cover the case. The suite was not run (read-only reviewer).

SPECIFIC ISSUES:
- [nit][impl] skills/_common/test_review_evidence.py:1069-1072 — Vacuous-test check: `test_fenced_envelope_parses_like_unfenced` still passes if the fence-skip at `review_evidence.py:524` is deleted. Add a fixture where the fence line matters, or remove the skip. (Medium)
- [nit][impl] skills/_common/review_evidence.py:524 — A fence line is skipped but does not end the section; with no RECONCILIATION NOTES, text after a closing fence is still read as SPECIFIC ISSUES. (Medium)
- [nit][impl] skills/_common/review_evidence.py:482-496 — Bold headings (`**SPECIFIC ISSUES:**`) and case or bold variants of the token (`Escalate:`, `**ESCALATE:**`) are missed, falling back to the generic "re-run" diagnostic; spec A3 promises lenient parsing. (Medium)
- [nit][spec] skills/independent-review/review.py:1144 (also skills/spec-workflow/SKILL.md:645) — Prompt and docs give `<file:line>`; AC4 says `<anchor>`. Spec-level escalations often have no file:line.

RECONCILIATION NOTES:
- AC4 wording: `<file:line>` vs `<anchor>`.
- Beyond AC1: `## SPECIFIC ISSUES` headings, en-dash separator, "(decision text missing)" for an empty decision.
- `escalated_decisions` fires only for a well-formed non-pass record; malformed records keep generic diagnostics (tested).
- `needs-changes` arch records with escalations also stop (fails safe); state in the deviation log.
- Consider bold/case-variant tokens and headings, and a closing fence ending the section.
- `skills/independent-review/SKILL.md:177-178` still says `needs-changes` becomes reconciliation-log items — slice 122-03's scope.
- Full suite not run by the reviewer.
