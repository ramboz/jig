---
slice: 107-01 — protection refusals reach the pull-request fallback
pass: compliance
verdict: pass
reviewer: PR #165 in-band review (post-hoc)
reviewed_at: 2026-08-14T19:56:26Z
prompt_source: post-hoc lifecycle close-out; original review on GitHub PR #165
---

## Post-hoc compliance verdict — recorded for lifecycle close-out

**Verdict: pass.** Recorded after the fact to close the ADR-0014 §5 evidence
gap. The implementation shipped and was accepted in-band on
[PR #165](https://github.com/ramboz/jig/pull/165) ("reservation sees in-flight
branches; protection refusals reach the PR fallback (#147)"), which merged to
`main` as `409ba19`. The slice's Acceptance Criteria are all ticked in the DoD,
each backed by a named regression test (`skills/_common/test_reservation.py`
and the existing protection-path fixtures in `test_bug.py` / `test_adr.py`),
and `run_tests.py` was green at merge.

No separate jig `reviewer`-subagent verdict file was captured at the time — the
review happened on the GitHub PR. This file records that provenance so the
lifecycle marker can reach DONE honestly rather than by bypassing the gate.
The claim (`claimed_by: claude/github-issue-147-c6ab0d`) is orphaned — that
branch merged and was deleted.
