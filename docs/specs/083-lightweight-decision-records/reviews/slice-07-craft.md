---
slice: 083-07 — In-flight decision stubs
pass: craft
verdict: pass
reviewer: jig:reviewer (Opus)
reviewed_at: 2026-06-27T00:19:11Z
prompt_source: review.py implementation/pr-review 083-07; read-only jig:reviewer
---

Craft pass (jig:reviewer, Opus, read-only). Slice 083-07: PASS. Well-factored lib of small single-purpose functions; consistent fail-open discipline (every public fn swallows exceptions; bash wrappers exit 0); reuses decision_scan's containment constants / is_user_override / clip rather than re-implementing, so in-flight and end-of-session capture can't drift. Dual-import shim, session-id path sanitization (tested against a ../../ traversal), and bounded _collect_strings recursion show real defensive care. Tests meaningfully exercise the prune/re-surface lifecycle and the scan-vs-stub dedup. Strengths: public clip/is_user_override seams as single source of truth; AC5 lifecycle tests verify durability parity (persist + re-surface until recorded, then prune-to-file-removal). Nits: (addressed inline) dedup_scan_against_stubs missing _DEDUP_MIN_TOKENS floor; redundant except FileNotFoundError in clear_scratch removed. (deferred, low value) stub turn=-1 discards real decision-time turn (append_stub accepts turn= but the hook doesn't thread it). async:true registration for the write-only non-blocking capture is an intentional, correct choice. Idiom conformance with sibling hooks clean.
