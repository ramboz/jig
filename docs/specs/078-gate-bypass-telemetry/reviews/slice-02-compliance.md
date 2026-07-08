---
slice: 078-02 — gate-stats digest
pass: compliance
verdict: pass
reviewer: Explore (jig compliance)
reviewed_at: 2026-07-08T21:20:34Z
prompt_source: review.py implementation
---

Spec-compliance review of slice 078-02 (gate-stats digest) against its 3 ACs. Retroactive review of shipped code (commit 5c31da0).

All three ACs met and meaningfully tested (7-test GateStatsTests):
- AC1 (per-gate counts) — gate_stats (workflow.py:2142-2211) filters event=="gate_bypassed" and tallies per gate; CLI registered + dispatched. test_counts_per_gate + test_excludes_skill_invoked_rows.
- AC2 (window honored) — `--days N` builds a UTC cutoff via _parse_iso_utc; default 30 (matches routing-stats). test_days_window_excludes_old_entries.
- AC3 (empty stays exit 0) — absent sink + zero in-window both return friendly messages, exit 0; caller only writes stdout. test_missing_log/test_empty_log assert returncode 0.

Robustness (malformed JSON, non-dict JSON, unparseable/missing fields, sort order) handled and tested.

VERDICT: pass

Findings:
- [strength] defensive parse loop (try/except + isinstance dict guard + field guards) makes the digest crash-proof on a shared externally-written sink.
- [strength] test asserts skill_invoked rows are excluded, guarding the shared-file invariant.
- [nit] workflow.py:2186-2189 — zero-in-window message labels the parenthetical as "older entries outside the window" even when the sink has only non-bypass rows; count is a correct 0, phrasing slightly imprecise. → deviation log.
RECONCILIATION NOTES: record that AC1's "extend routing-stats OR a sibling gate-stats" was resolved to a sibling command (over the non-binding note's lean to extend), rationale: gate-bypass events are a distinct event type. The bypass-only count (no respected-fire denominator) is an intentional, pre-documented deferral to the refinement-todo denominator entry.
