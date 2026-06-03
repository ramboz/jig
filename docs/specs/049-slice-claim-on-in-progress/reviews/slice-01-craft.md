---
slice: 049-01 — claim-and-release-on-transition
pass: craft
verdict: pass
reviewer: pr-review
reviewed_at: 2026-06-03T21:34:37Z
prompt_source: review.py pr-review docs/specs/049-slice-claim-on-in-progress/spec.md 049-01 <deliverables>
---

## Craft review (pr-review) — slice 049-01

VERDICT: pass (no [blocker] findings)

Faithfully extends the established 003-03 / 028-01 / 051 reserve-on-main pattern to slice ownership, with house-style provenance markers and an honest inline-mirror-not-extract note (ADR-0002 second-caller rule). Tests are meaningful, not superficial.

Strengths:
- Reservation correctly ordered before the on-disk write — a collision/race/unreachable-origin refusal leaves the caller's slice file untouched (verified by `test_push_race_refuses_and_leaves_local_untouched`).
- `_assert_claim_branch_ref_valid` is a real regression guard for the slugged PR-fallback branch.
- Idempotent re-claim short-circuits with no push (both on-disk and origin paths tested).

Nits (deferred, logged in deviation log):
- `_append_release_log` appends to end-of-section rather than anchored under the `## Release log` heading — fine for the current single-trailing-section shape.
- The "foreign + still IN_PROGRESS" predicate is expressed twice (on-disk vs origin/main). Intentionally separate sources; a third caller would trigger extracting a shared predicate per ADR-0002.
- `from unittest.mock import patch` re-imported per test method (matches surrounding style).
