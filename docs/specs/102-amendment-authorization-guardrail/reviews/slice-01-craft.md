---
slice: 102-01 — surface-and-stop-authorization-rule
pass: craft
verdict: pass
reviewer: jig:reviewer (independent subagent)
reviewed_at: 2026-08-02T14:23:58Z
prompt_source: review.py pr-review
---

Both documentation surfaces carry the required governance text at their points of use;
tests scoped via `_closed_spec_drift_item`/`_flat` rather than whole-file token matches,
and the two headline claims are pinned by assertions that go red if the prose is deleted.

[strength][impl] test helpers `_flat` (wrap-robust prose assertion) + `_closed_spec_drift_item`
(scope to the single checklist item) satisfy the DoD "scoped content assertion (not a
whole-file token match)" requirement — reusable pattern.
[strength][impl] analyze posture explicitly contrasts with "no file writes" ("escalated,
not decided"), exactly AC3's reinforce-not-restate requirement.
[nit][impl] (ADDRESSED during craft) test_scoped_to_records_not_live_prose originally
asserted only "records", which the pre-existing ADR-0010 text already contains — vacuous
for the AC2 scoping sentence. Tightened to assert "governs records only" + "needs no
sign-off" (phrases unique to the new sentence) and mutation-tested red→green.
[nit][impl] British spellings "Authorisation"/"behaviour" in new prose — harmless, aligned
with the AC wording; tests key off lowercase substrings, no functional risk.

No blockers. AC4 host-mirror drift guard confirmed green out-of-band (build_host_packages.py
--check exits 0).
