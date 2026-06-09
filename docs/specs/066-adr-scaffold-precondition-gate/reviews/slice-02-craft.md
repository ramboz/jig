---
slice: 066-02 — adr-skill-step0-precondition
pass: craft
verdict: pass
reviewer: general-purpose
reviewed_at: 2026-06-09T18:06:16Z
prompt_source: review.py pr-review
---

VERDICT: pass

REASONING:
A tight, well-scoped documentation slice that faithfully mirrors the shipped 063-02 pattern onto
the ADR door. The SKILL.md Step 0 prose is clear, routes greenfield->scaffold-init /
adoptable->migrate, names the anti-pattern, and points at adr.py new's own routing without
restating the heuristic. The two tests are robust where it counts: the guard test isolates the
"Author a new ADR" section before asserting — load-bearing here because the routing targets and
docs/decisions/ appear in seven other places in the file — and the scaffold-parity test pins the
copied body against drift. Findings are all nit-or-strength; nothing blocks REVIEWED.

SPECIFIC ISSUES:
- [strength] test_workflow_contract.py — section-isolation (find("### 1. Author a new ADR") -> next
  "\n### ") is genuinely load-bearing: /jig:scaffold-init, /jig:migrate, docs/decisions/ each appear
  multiple times OUTSIDE this section, so without isolation the assertions would pass trivially. The
  bound correctly stops at "### 2. Accept the ADR".
- [strength] test_workflow_contract.py — the negative "no restated heuristic" assertion + the
  positive "must name adr.py" assertion together encode AC2 as an executable contract.
- [strength] test_scaffold_mode.py — the parity test states WHY parity holds (scaffold copies the
  live SKILL.md body, path-substituted) and reuses the 063-02 four-anchor shape; adr-workflow is
  confirmed in _TIER_SKILLS["tier-1"].
- [nit] test_workflow_contract.py — the forbidden-token list (3-of-4 variants) is vacuously true
  today (none exist in the file); it's a forward-looking pin with no present-tense bite, and a
  restatement like "3+ markers" would slip past. Low risk given the explicit "don't restate" prose.
- [nit] test_workflow_contract.py — test_names_the_decisions_skeleton_anti_pattern keys partly off
  the docs/decisions/ mention in the precondition sentence rather than the anti-pattern paragraph;
  the hand-roll/improvis assertion carries the real AC3 signal. Inherited from 063-02.
- [nit] adr-workflow/SKILL.md:43 — minor prose redundancy (confirm-state then "you don't have to
  decide yourself — adr.py new routes"); reads fine on second pass, mirrors 063-02.

RECONCILIATION NOTES:
All findings are nits/strengths — none blocks REVIEWED. Worth logging: (1) the heuristic-restatement
guard is a forward-looking pin, vacuously true today; (2) the anti-pattern test keys partly off the
precondition sentence, with hand-roll/improvis carrying the real AC3 signal. Both shapes are inherited
verbatim from the 063-02 sibling — deliberate parity, not new drift.
