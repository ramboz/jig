---
slice: 087-01 — investigation guidance in code-review prompts + reviewer agent
pass: compliance
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-07-11T19:09:02Z
prompt_source: review.py implementation docs/specs/087-narrow-first-review/spec.md 087-01 <deliverables>
---

VERDICT: pass

REASONING:
All five acceptance criteria met on the evidence. The shared `_INVESTIGATION`
block (review.py) carries all five narrow-first moves (anchor, locate-before-read
with Grep/Glob, batch discovery, focused ranges, retry-with-simpler-query) and is
embedded in exactly the five code-review builders (implementation, pr-review,
bug-review, arch-review, code-health) while deliberately absent from the three
prose builders (reconciliation, frame-critique, design-review). `agents/reviewer.md`
adds an equivalent "How to investigate efficiently" section, and the host copies
(hosts/claude, hosts/codex incl. generated jig-reviewer.toml) mirror the markers.
Tests cover presence in all 5 code passes, absence in all 3 prose passes, and the
agent section. Test-quality snapshot signals all read false.

SPECIFIC ISSUES:
(none blocking)

RECONCILIATION NOTES:
- reviewer.md section is a condensed 3-move version (anchor, locate-before-read,
  focused ranges) — intentionally omits "batch discovery" and "retry-with-simpler-
  query". Satisfies AC4 "equivalent"; recorded as a deliberate choice.
- AC5 (host-package drift) verified by marker presence; drift test run separately
  and green.
- Deviation log / reconciliation sweep were _TODO at review time (expected;
  reconciliation runs later).
