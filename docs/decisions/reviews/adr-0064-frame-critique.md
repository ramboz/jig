---
adr: 0064
pass: frame-critique
verdict: pass
reviewer: reviewer
reviewed_at: 2026-10-03T17:34:01Z
prompt_source: review.py frame-critique docs/decisions/adr-0064-use-case-progress-rollup-in-jig.md
---

**Round 1 — needs-changes.** Highest-risk assumption: the use-case join is a *drift signal* whose Unanchored bucket catches rabbit-hole specs. Wrong by construction: `use_cases:` links are written by the agents whose drift is in question, against goal-level use cases elicited after the corpus existed (110 of 112 specs anchored on adoption day); spec-workflow step 2a steers every new spec to cite or mint a use case; the mis-mapping mitigation assumes knowledge the owner lacks; the report has no time axis. Secondary: the Assumptions entry cited §A2 (false completion), not false anchoring.

**Fixes applied:** bound 5 "a progress view, not a drift detector"; Consequences reworded; a "Known limit (false anchoring)" Assumptions entry; kill criteria rewritten; agent-independent signals parked in `docs/refinement-todo.md` ("a progress signal the drafting agent does not author").

**Round 2 — pass.** Narrowing the claim resolves the finding; no new likely-wrong load-bearing assumption. Consistency nits, all applied before accept: the main assumption still said "drift signal" (now "progress view"); kill criterion 2 recast as an escalation trigger (retirement stays with criterion 1); Context now says the decision answers the progress half of the owner's question, not the on-goal half; "counts not percentages" no longer claimed to mitigate the §A2 all-done case.
