---
slice: 111-01 — blocked-annotation-and-board
pass: frame-critique
verdict: pass
reviewer: jig:reviewer (independent adversarial frame-critique)
reviewed_at: 2026-08-15T17:50:30Z
prompt_source: review.py frame-critique 111-01
---

## Frame-critique verdict — slice 111-01 (blocked-annotation-and-board)

**Verdict: pass.** Independent read-only `jig:reviewer` pre-implementation
frame-critique: do the 7 ACs faithfully and completely realize ADR-0057?

**Grounding — all DoR claims verified in `workflow.py`:** `render_deferred_table`
(:2231, returns "" on empty — so AC5 byte-identity is achievable),
`collect_slices` (:2063, `claimed_by` via `CLAIM_FIELD` :2112),
`_CLAIM_WORKING_STATUSES` (:4204, exactly the four working states AC4 enumerates),
`_extract_resolution_trigger` (:1544). The ACs fully enumerate the actionable
state set, specify empty-omission, and hand the non-actionable misfile warning to
111-02 correctly.

**Two non-blocking nits — both fixed in the slice before implementation:**
1. AC6 originally implied the deferred/abandoned render path escapes pipes; it
   does not (it relies on an author-side `&#124;` convention, `workflow.py:2141`).
   Reconciled: AC6 now specifies the "Blocked on" cell is **actively escaped**
   (a deliberate improvement, since `blocked_by:` is free text).
2. The path by which the `**Blocked:**` body line reaches `render_blocked_table`
   was unstated. Reconciled: AC1 now states the `collect_slices` row carries the
   extracted body line (as it already carries `abandonment_reason`).

**Known residual (not a flaw):** A2 (Gauge wants ready-but-stuck included) is
un-probed but carries an explicit kill condition in accepted ADR-0057. The
interim window after 111-01 lands but before 111-02 — a `blocked_by:` on a
non-actionable slice neither renders nor warns — is an accepted SPIDR boundary.
