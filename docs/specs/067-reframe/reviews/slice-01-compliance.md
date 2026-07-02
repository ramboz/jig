---
slice: 067-01 — The `/jig:reframe` skill: keystone ADR + dispositions
pass: compliance
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-07-02T16:48:43Z
prompt_source: review.py compliance docs/specs/067-reframe/spec.md 067-01 <deliverables>
---

VERDICT: pass

REASONING:
All seven ACs for 067-01 are met. skills/reframe/SKILL.md is a complete judgment-only
skill contract: active frontmatter, both invocation styles, the full 6-term disposition
vocabulary + `## Emergent work`, the keystone-ADR-via-`adr.py new` flow, the two-level
coverage floor (L1 named classes + L2 within-touched read), the reduces-and-surfaces /
does-not-eliminate honesty framing + T1 backstop, the no-`.py`-helper contract, the
not-a-`## Assumptions`-sweep / not-a-corpus-walker statements, and the Q1 no-op /
not-locatable refusal. All registration surfaces + pinned-tier guards carry reframe
(Tier-1); DoR satisfied (ADR-0024 Accepted); pre-impl frame-critique passed. Surface
tests exercise the structural ACs and correctly defer AC2/AC5 quality to the gate.

SPECIFIC ISSUES:
- [nit] CLAUDE.md is at exactly the spec-076 lean-primer budget (70 lines, zero headroom);
  reframe was added by extending line 31, not a new line, so the guard passes. Flag as a
  maintenance seam for the next primer edit. (informational)

RECONCILIATION NOTES:
- Fill the slice-01 deviation log (still a _TODO_) with the resolved open questions:
  (a) manifest lives INLINE in the keystone ADR; (b) /jig:reframe is draft-on-invoke only
  (no report-only mode). Both resolved as-planned (confirmations, not deviations).
- Record the L1-class-list "jig-corpus-shaped" staleness note as a folded-in frame-critique
  finding (scoped, faithful, adjacent to T2), not silent scope.
