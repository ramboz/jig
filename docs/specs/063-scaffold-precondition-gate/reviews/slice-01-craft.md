---
slice: 063-01 — classify-and-route-on-new
pass: craft
verdict: pass
reviewer: general-purpose
reviewed_at: 2026-06-08T23:22:47Z
prompt_source: review.py pr-review
---

VERDICT: pass

REASONING:
Slice 063-01 is a small, well-shaped change: a leaf-pure `_common/scaffold_state.py`
classifier wired into `reserve_spec` as a route-don't-block precondition, with the
legacy weak refusal preserved verbatim under the bypass. The load-bearing
classification ordering (scaffold.json -> interrupted-scaffold -> trigger-predicate)
is documented in the docstring and pinned by tests, including the subtle "crashed
scaffold with >=3 triggers still routes to recovery" case. Tests assert observable
behavior (no commit, no directory on refusal) rather than internals, follow the
file's existing inline-import / unittest.mock conventions, and the full canonical
suite is green (2487 tests, exit 0) confirming the AC4 no-regression claim. Only
minor nits remain.

SPECIFIC ISSUES:
- [strength] scaffold_state.py:130-154 — load-bearing ordering documented in docstring
  AND production-code comment, then pinned by
  `test_interrupted_scaffold_with_three_triggers_still_greenfield`.
- [strength] scaffold_state.py:45,54-59 — leaf-purity held honestly: shares the single
  `GATE_DISABLE_VALUES` contract (no drift) but deliberately replicates the watermark
  literal (no upward dependency on scaffold-init). Right call on each.
- [strength] test_workflow.py:2331-2369 — routing tests assert observable outcomes
  (message names state + exact command; no `docs/specs/NNN` dir; no `git commit`),
  surviving internal refactor and doubling as the AC2/AC3 "creates no reservation" guard.
- [strength] test_workflow.py:2452-2467 — `test_bypass_preserves_legacy_weak_refusal`
  asserts presence of the legacy message AND absence of either routing string — precise
  regression guard that bypass restores today's behavior exactly.
- [nit] scaffold_state.py:79-109 — `looks_spec_driven` re-implements the >=3-of-4
  trigger count scaffold-init's `_looks_already_spec_driven` already encodes. Explicitly
  sanctioned by spec non-goals + deviation log (transient third copy; rule-of-three
  EXTRACT deferred) — not a blocker, but keep on the radar for the eventual extract.
- [nit] test_workflow.py:2306-2308 — `_make_greenfield` is an empty-body `pass` helper;
  reads as a symmetry placeholder, slightly more indirection than a call-site comment.
  Trivial; leave or inline as taste dictates.

RECONCILIATION NOTES:
The transient trigger-predicate duplication is already captured in the deviation log and
spec non-goals as a deferred rule-of-three EXTRACT — no new action needed, but it is the
one piece of debt this slice knowingly adds and should stay visible until the two tuned
call sites are reconciled. All other observations are strengths or cosmetic nits and need
not block REVIEWED.
