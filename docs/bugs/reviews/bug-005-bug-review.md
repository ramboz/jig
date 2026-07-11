---
bug: 005
pass: bug-review
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-07-11T15:24:24Z
prompt_source: review.py bug-review
---

VERDICT: pass

REASONING:
The fix targets the documented root cause (the list-item extractor), not a
symptom. `_top_level_list_items` replaces `line.strip().startswith("-")` with a
marker-agnostic regex (`-`/`*`/`+`/`1.`/`1)`) plus an indent<2 top-level filter,
flipping both documented failure directions. Five of six new tests are genuine
red-before/green-after pins (the sixth is a dash back-compat guard). Changed gap
strings retain the "hypotheses"/"evidence" substrings other tests assert, so
nothing regresses. The `_section` heading fragility is deliberately deferred and
documented.

SPECIFIC ISSUES:
- skills/bug-fix/bug.py — `_has_leading_marker` treats any `(leading)` substring
  as a marker; a new (advisory-only) false-positive surface. Acceptable widening.
- skills/bug-fix/bug.py — `indent >= 2` excludes CommonMark-legal 2-3 space
  top-level items; rare given the zero-indent convention the template teaches.

RECONCILIATION NOTES:
- `_section` heading/trailing/fenced-code fragility deferred; logged to
  docs/inbox.md so the adjacent fragility is not silently dropped.
- Template ships `- [ ] / - [x]` placeholders: the gate is presence/shape only;
  an unedited scaffold is still tripped by the empty `## Evidence` gap. Design is
  intentional (quality is the bug-review pass's job).
