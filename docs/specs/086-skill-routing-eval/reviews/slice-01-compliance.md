---
slice: 086-01 — routing-eval harness (collision + trigger + ratchet)
pass: compliance
verdict: pass
reviewer: general-purpose
reviewed_at: 2026-07-08T19:13:11Z
prompt_source: review.py implementation 086-01 (re-review)
---

Compliance pass (fresh-context general-purpose subagent; re-review after the
test-coverage fixes). PASS — all six ACs met, no blockers.

Report command works (19 skills, IDF-weighted collisions sorted + flagged,
per-case triggers, --json); description reader decodes folded/literal/plain/
quoted scalars; collision + trigger rules gate correctly; ratchet has proven
teeth (--min-rank1 1.01 → exit 1). Independent verification: 28/28 unit tests
pass, ruff + pyright clean (py39, zero third-party deps), skills↔cases
correspond exactly 19:19, all negative owners resolve to real skills.

Coverage on the previously-flagged ACs:
- AC2 — test_no_routable_skill_resolves_empty independently walks every
  skills/*/SKILL.md and asserts a non-empty parse + set(descriptions)==routable;
  replaces the vacuous count>=15 check. A folded-reader regression now fails
  loudly.
- AC4 — test_case_file_per_routable_skill asserts bidirectional set equality;
  test_negative_case_owners_are_real_skills fails on a typo'd owner (which would
  otherwise silently downgrade the pairwise route-away test).
- AC5 — ratchet exercised four ways (collision <0.75; positives 57/57 in top_k;
  rank-1 ≥0.85 at 95%; negative route-away ≥0.90 at 100%), floors raise-only.

No correctness/robustness/security defects. Inputs are repo-controlled; no
external attack surface.

Reconciliation note (for the deviation log): AC4 wording says each negative's
owner "outranks the case's skill," but enforcement is the AC5 MIN_NEG_ROUTE_AWAY
floor (0.90), not a hard 100% — by design (main()'s hard gate covers only
positives-outside-top_k and collisions; negatives are floor-ratcheted). Current
baseline is 100%. Note the floored-not-hard-100% framing in the deviation log.
