---
adr: 0052
pass: frame-critique
verdict: pass
reviewer: jig:reviewer subagent (fresh context, round 4)
reviewed_at: 2026-07-31T21:32:17Z
prompt_source: review.py frame-critique docs/decisions/adr-0052-grounding-enumeration-for-universal-claims.md
---

Frame-critique PASS on round 4 (rounds 1–3 returned needs-changes and were fixed).

The frame is sound and the operative rule is faithfully mirrored in both live-prose
homes (spec-workflow/SKILL.md step 6 and bug-fix/SKILL.md §2 Diagnose), matching the
ADR's recommended text. The core load-bearing move — shifting the burden from author
self-classification ("bounded vs unbounded") to a falsifiable positive articulation
("state why the search is exhaustive") routed to the external frame-critique reviewer
— is a genuine improvement over the incident it is grounded in (#132), a verified base
case. The ADR marks its two load-bearing unverified assumptions honestly (reviewer
efficacy; materiality of the unbounded-search risk) rather than asserting them, and its
Kill criteria + Open questions watch exactly the residual regress.

No blocking issues. Residual (disclosed, not blocking): the external reviewer may share
the author's blind spot on look-bounded-but-isn't sets — recorded as load-bearing
Assumption 1 with a matching kill criterion and open question.

Reconciliation notes for the deviation log:
- ADR-0010 routing correctly applied: decision content recorded in this new ADR (ADRs
  are extended/superseded, never amended in place per ADR-0006), operative guidance
  landed as inline edits to the two SKILL.md files (git as audit trail). ADR-0020 §1
  prose is deliberately left unedited — the enumeration carve-out lives only in ADR-0052
  + the two SKILLs. Intended mechanism, not drift.
