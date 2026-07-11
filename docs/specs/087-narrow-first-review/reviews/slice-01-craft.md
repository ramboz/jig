---
slice: 087-01 — investigation guidance in code-review prompts + reviewer agent
pass: craft
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-07-11T19:09:02Z
prompt_source: review.py pr-review docs/specs/087-narrow-first-review/spec.md 087-01 <deliverables>
---

VERDICT: pass

REASONING:
Clean, well-scoped additive change: a single `_INVESTIGATION` constant is threaded
into exactly the five code-review builders and deliberately withheld from the three
prose builders, matching the spec's load-bearing scoping decision. The reviewer
agent gains an equivalent section; tests cover presence in all five code passes,
absence in all three prose passes, and each of the five narrow-first moves. No
correctness, security, or robustness concern rises to a blocker; two low-severity
wording nits.

SPECIFIC ISSUES:
- [strength][impl] skills/independent-review/review.py — investigation guidance
  defined once as a module constant and reused across five builders rather than
  copy-pasted; block comment ties the code/prose split to the article's
  task-shaped-not-blanket lesson.
- [strength][impl] skills/independent-review/test_review.py — coverage is
  meaningful: AC1 asserts each of the five moves via regex, AC2/AC3 assert
  presence-in-5 and absence-in-3 as separate cases, AC4 checks the standing agent.
- [nit][impl] skills/independent-review/review.py — shared block said "Start from
  the listed files and the acceptance criteria", but bug-review has no ACs and
  pr/arch/code-health are told not to re-evaluate ACs. FOLDED IN during
  reconciliation: reworded to "the change under review".
- [nit][impl] agents/reviewer.md — standing agent section carries 3 of 5 moves
  (omits batch discovery + retry-simpler). KEPT as-is (deliberate scoping — the
  standing prompt also governs prose passes; per-invocation prompts carry all 5).

RECONCILIATION NOTES:
- Nit #1 folded into the deliverable; nit #2 kept as a deliberate design choice
  (both recorded in the deviation log).
- AC5 host-package drift enforced by build_host_packages.py --check — confirmed
  green during reconciliation.
