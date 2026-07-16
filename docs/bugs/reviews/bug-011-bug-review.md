---
bug: 011
pass: bug-review
verdict: needs-changes
reviewer: jig:reviewer
reviewed_at: 2026-07-16T20:41:43Z
prompt_source: skills/independent-review/SKILL.md (bug-review pass, bug 011)
---

Independent bug-review pass, 2026-07-16. Verdict recorded as **needs-changes** — the verdict the
reviewer actually returned. Findings were addressed after recording; git history is the audit
trail (ADR-0014 §4).

## Assessed as sound

- The fix addresses the named root cause, not the symptom: suppression removed on both
  recorded-corpus paths; containment survives only as `possible_duplicate`.
- The regression test is a genuine capture — it uses the record's exact repro quote, would return
  `[]` against the old `dedup()` (failing on both the length assertion and `out[0]`), and is
  reversal-specific rather than a generic dedup case.
- Scope right: fixing `prune_recorded_stubs` was necessary (same rule, highest-fidelity surface);
  keeping `dedup_scan_against_stubs` as a drop is defensible (covering stub surfaces in the same
  nudge). `hosts/` mirrors faithfully regenerated, no hand edits.
- No behaviour regression: the duplicate note renders only when something is flagged, guarded by
  `test_unflagged_candidate_carries_no_duplicate_marker`. Nudge is noisier by design — the
  maintainer's accepted trade.

## Blocking findings (all addressed)

1. Four comments/docstrings in the touched files still asserted the deleted behaviour —
   `jig-decision-capture.sh:11-12` and `:38-41`, `decision_scratch.py:216`/`:223`/`:140-141`.
   The `decision_scan.dedup` cross-references mattered more than normal dangling refs: that
   "mirrors decision_scan.dedup's containment rule" trail is what *proved* the stub path carried
   the same defect. Breaking it is how the next mirrored defect hides. **Fixed**, and the rule
   now has a single home (`is_contained`) so the mirror cannot drift.
2. Spec 083 drift, uncorrected: `spec.md:251`/`:432` (live prose, IN_PROGRESS) and the AC5s of
   closed slices 04 and 07, whose behaviour this fix inverts. **Fixed** per ADR-0010 — inline
   correction for live prose, `## Amendments` for the closed records. Flagged that open slice
   083-08 (Codex host-parity) would otherwise validate against a stale AC5.
3. The record overclaimed "nothing is ever dropped, so the class cannot recur".
   `dedup_scan_against_stubs` still drops on the identical rule: a Tier-3 *agent* reversal of an
   in-flight stub is silently dropped, since agent prose never produces a stub of its own
   (3/4 = 0.75 in the reviewer's example). Tier-2 user reversals are safe — they fire
   `UserPromptSubmit` and survive as their own stub. **Fixed**: claim scoped to the
   recorded-corpus paths; residual parked in refinement-todo.md.
4. Lifecycle claim no longer true: `flag_recorded_stubs` never shortens the list, so
   `clear_scratch` is unreachable for a populated log and a scratch log outlives its session,
   while the module still called it "ephemeral". **Fixed** (docstring corrected) and parked.
