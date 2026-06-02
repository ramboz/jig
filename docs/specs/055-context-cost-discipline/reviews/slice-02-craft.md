---
slice: 055-02 — In-session context-growth nudge
pass: craft
verdict: pass
reviewer: jig:reviewer (read-only)
reviewed_at: 2026-06-02T01:53:38Z
prompt_source: review.py pr-review docs/specs/055-context-cost-discipline/spec.md 055-02 <deliverables>
---

VERDICT: pass

REASONING:
High-craft implementation: policy logic in small pure documented functions in context_fill.py; the shell hook is a thin I/O shim parsing stdin once and branching on hook_event_name; the SessionStart path is byte-for-byte unchanged (new UserPromptSubmit branch added ahead of the untouched else). Tokens-vs-window conversion is dimensionally correct (count ÷ token_window; token_window = JIG_CONTEXT_WINDOW_BYTES // RATIO); the tail read truly avoids a full scan (seek last 256KB, drop partial first line, walk backward); per-band + re-arm-on-drop is correct and well-tested; the never-raises contract is enforced at every layer. Tests exercise band transitions, re-arm, drop-then-reclimb, corrupt-tail-then-valid, and malformed/missing/empty inputs. All findings non-blocking.

SPECIFIC ISSUES:
- [strength] read_tail_cache_read_tokens walks the tail backward, skips unparseable lines (corrupt final line never masks an earlier valid record); isinstance bool guard rejects True/False.
- [strength] evaluate_growth is pure; re-arm logic float-tolerant (abs<1e-9); _growth_bands() de-dups a configured threshold coinciding with a fixed band so it can't double-fire.
- [strength] jig-context-check.sh reads stdin once; garbage → {} → silent; growth branch wrapped in nested excepts → can never block a turn.
- [strength] test_uses_last_assistant_record feeds [90,10] and asserts silence — proves the tail (not whole-file) governs.
- [nit] per-session $TMPDIR state file is never cleaned up; stale jig-context-growth-<sid>.json accumulate (low impact; OS-reaped). Note cleanup is intentionally deferred to the OS tmp-reaper.
- [nit] growth_nudge_for_turn has no concurrency guard on the state-file read-modify-write; UserPromptSubmit turns are serial within a session → effectively unreachable; a sentence acknowledging it would age well.
- [nit] DEFAULT_GROWTH_THRESHOLD=0.40 and GROWTH_BANDS=(0.40,0.60,0.80) independently encode 0.40; deriving GROWTH_BANDS=(DEFAULT_GROWTH_THRESHOLD,0.60,0.80) removes the sync footgun.
- [nit] nudge text formats band_pct and actual_pct with :.0f → can read "~40% ... past the 40% mark" just over a band (cosmetic).

RECONCILIATION NOTES:
- Capture the two deferred-by-design choices (tmp state files left to OS reaping; unguarded state RMW safe because UserPromptSubmit is serial). The 0.40 duplication is a tracked nit (GROWTH_BANDS asserted by test_growth_bands_are_40_60_80). Scaffold-mode coverage is solid.

Provenance: reviewer jig:reviewer (read-only); prompt built by review.py pr-review.
