---
adr: 0048
pass: frame-critique
verdict: pass
reviewer: reviewer-subagent (3 ADR + 2 slice rounds)
reviewed_at: 2026-08-03T17:51:27Z
prompt_source: review.py frame-critique docs/decisions/adr-0048-...md
---

Frame-critique pass on ADR-0048 (SessionStart git-freshness). Three adversarial
rounds against a fresh read-only reviewer.

Round 1 (needs-changes): always-fetch accuracy claim asserted, not grounded —
the one real incident (#105) was catchable fetch-free; and nudge-fatigue risk on
routinely-behind mid-flight branches.

Round 2 (needs-changes): the earlier `@{upstream}`-first resolution rule
contradicted the "behind = stale base" justification — for a pushed task branch
`@{upstream}` = origin/<branch> and measures own-branch advancement (~0), not
base drift, so the hook would go SILENT on the exact #105 base-drift case.

Round 3 (PASS): resolution precedence inverted to base-first
(origin/main → origin/master, @{upstream} last-resort only), coherent across
ADR + spec + slice, with a dedicated base-first regression test pinned. The
always-fetch decision is honestly framed as a safe superset (never worse for
correctness) with the downstream-staleness hypothesis marked unprobed and named
in kill criteria; correctness rests on none of the remaining unprobed
hypotheses. Reviewer verdict: "None survive — frame holds."

UPDATE (post-accept refinement): a slice-level frame round then found the
base-first rule mismeasured non-main-trunk topologies (git-flow/fork). The
resolution was reworked to the guarded smart-target rule (prefer a non-own
@{upstream}, else trunk); re-verified PASS at the slice level. ADR § "Upstream
semantics", Assumptions (the @{upstream}≠own heuristic), and Kill criteria
(wrong-base) updated to match. Decision content (always-fetch timeout-guarded;
active nudge) unchanged.
