---
slice: 056-03 — `.jig/spec-ref` marker for exact session→spec attribution
pass: craft
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-06-03T04:41:26Z
prompt_source: review.py pr-review 056-03
---

VERDICT: pass

REASONING:
A clean, well-scoped implementation. The writer (`workflow.py:_write_spec_ref_marker`) and reader (`usage.py:read_spec_ref_marker`) agree on a simple `key=value` format; the marker write is genuinely side-effect-isolated (broad except swallows all failures, ordered after status writes, gated only on IN_PROGRESS); attribution correctly prefers the marker over the content heuristic while honestly flagging heuristic-only sessions. Test coverage is thorough and meaningful — marker-wins-over-conflicting-content, idempotency, write-failure non-blocking, gate isolation, normalization, and the heuristic-fallback regression.

SPECIFIC ISSUES:
- [strength] `_write_spec_ref_marker` is exemplary best-effort design: empty-spec-number no-op, `mkdir(parents=True, exist_ok=True)`, atomic write via the shared `atomic_write_text`, broad `except Exception` with a noqa rationale tying it to AC #1/#4. Ordering after `_write_spec_rollup` and gating on IN_PROGRESS keeps it from ever interfering with the review-evidence gate.
- [strength] The `_MarkerTreeMixin` test fixture: the marker session's content deliberately screams a different spec (071) than its marker (070), so the precedence tests prove behavior rather than merely exercising the path.
- [strength] `attribute_session` cleanly funnels both attribution methods through one entry point returning `(spec, method)`, so the confidence split and rendered caveat stay in sync with the attribution logic.
- [nit] `workflow.py` `IN_PROGRESS_STATUS = "IN_PROGRESS"` is a single-use constant duplicating the literal already in `VALID_STATUSES`; a bare comparison would be equally clear. Harmless, cosmetic.
- [nit] `workflow.py:629` comment "the marker only follows a committed transition" reads as if a git commit occurs; the transition only writes files (no commit here). Ordering rationale is sound; wording slightly overstates it.

RECONCILIATION NOTES:
- Both nits are non-blocking; suitable for the deviation log rather than blocking REVIEWED. (Comment-wording nit will be fixed in reconciliation.)
- The writer/reader format contract is duplicated across two files by design; the cross-referencing comments are the right mitigation for a two-caller inline mirror (consistent with the project's extract-at-three-callers convention). Worth a one-line status-board Notes entry (marker shape + stamping point).
- The session→spec cwd matching assumes session `cwd` equals the worktree root (= spec.md `parents[3]`); holds for the worktree-per-task pattern. Record as the load-bearing attribution invariant.
