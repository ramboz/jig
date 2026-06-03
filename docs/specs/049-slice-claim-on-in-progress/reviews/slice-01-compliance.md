---
slice: 049-01 — claim-and-release-on-transition
pass: compliance
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-06-03T21:34:24Z
prompt_source: review.py implementation docs/specs/049-slice-claim-on-in-progress/spec.md 049-01 <deliverables>
---

## Compliance review — slice 049-01

VERDICT: pass

Independent re-review after the initial needs-changes finding was resolved.

- AC1 (stamp `claimed_by` from `JIG_CLAIM_ID` then branch name) — met; tested both ways.
- AC2 (reserve-on-main + race classifier + PR fallback) — met via `_reserve_claim_on_main` reusing `_classify_push_failure`.
- AC3 (collision refusal naming the existing claim + `--release` pointer) — enforced both on-disk (transition) and on origin/main; tested.
- AC4 (clear claim on REVIEWED / back to READY_FOR_IMPLEMENTATION / DRAFT) — met via `_CLAIM_CLEARING_STATUSES`; tested.
- AC5 (`--release` requires `--reason`; appends `## Release log`) — met; tested incl. refusal without reason.
- AC6 — intent-preserving DEVIATION: claims are LOCAL by default with opt-in `--push`/`--pr` (rather than push-by-default + `--no-push`). Unreachable-origin refuses when `--push` is chosen (tested).
- AC7 (subprocess-mocked; no real push) — met via `_SubprocessRecorder`.

Resolved finding: PR-fallback branch is now slugged via `_ref_safe()` (was `claim/{raw label}` — invalid git ref); `claim_branch` uses it, and both PR tests assert ref validity via `_assert_claim_branch_ref_valid`.

Reconciliation notes: record the AC6 local-default deviation and the AC8 live-remote dogfood in the slice deviation log.
