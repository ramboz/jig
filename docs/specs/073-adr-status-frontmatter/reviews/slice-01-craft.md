---
slice: 073-01 — reader honors frontmatter status
pass: craft
verdict: pass
reviewer: jig:reviewer (independent, read-only)
reviewed_at: 2026-06-15T17:12:45Z
prompt_source: review.py pr-review docs/specs/073-adr-status-frontmatter/spec.md 073-01
---

VERDICT: pass

REASONING:
Tight, well-scoped ~50-LOC change to a single module-private reader plus 11 focused tests, faithfully implementing ADR-0026's frontmatter-first/prose-fallback rule with Superseded != Accepted in both paths. Respects the slice's implementation notes (inline Superseded check, no premature _classify_status extraction), preserves the (ok, reason) tuple contract + diagnostic parity; docstring clear about both branches + rule-of-three rationale. Tests DAMP, behavior-named, isolated, assert observable returns; each AC has a fixture; the prose-only bug-fix case mirrors real adr-0002/0008. No blockers.

SPECIFIC ISSUES:
- [strength] workflow.py:759-799 — isolate-`## Status`-once shared by both branches, superseder pulled before branching; docstring precisely states resolution order + justifies the inline check per ADR-0002.
- [strength] test_workflow.py:1529-1537 — `test_frontmatter_accepted_ignores_absent_prose_status` is the load-bearing guard for AC1's no-prose-consult clause; pairs with the bug-fix regression using a real-shaped fixture.
- [nit] workflow.py:782-790 — frontmatter branch keys on `if "status" in fields:`; a bare empty `status:` parses to "" and would emit "<name> is  (not Accepted)" (double space). Unreachable for real ADRs (legacy lack the key; 073-02's writer always stamps a value). Cosmetic. Defer.
- [nit] workflow.py:774-778 — superseder regex requires the bracketed `Superseded by [ADR-NNNN]` link form (exactly what adr.py supersede writes). A hand-edited unbracketed `Superseded by ADR-0200` line in a legacy prose-only ADR would fall through to `^Accepted` -> satisfied. Out of scope (hand-edited prose diverging from the writer); worth a one-line note that superseder detection is link-form-specific. Defer.

RECONCILIATION NOTES:
Both nits are cosmetic/defer-class — land in the deviation log, do not block REVIEWED. No deviations from spec/ADR-0026. Strengths to carry: isolate-section-once structure; DAMP AC-mapped tests.
