---
slice: 055-03 — Read-once / read-lean discipline
pass: craft
verdict: pass
reviewer: jig:reviewer (read-only)
reviewed_at: 2026-06-02T02:39:18Z
prompt_source: review.py pr-review docs/specs/055-context-cost-discipline/spec.md 055-03 <deliverables>
---

VERDICT: pass

REASONING:
Clean, well-scoped, well-tested. evaluate_read is a pure decision (duplicate beats large; large never consumes the per-path duplicate budget; idempotent seen-recording); read_nudge_for_turn never raises; the per-session state file uses a distinct jig-read-paths- prefix (vs growth's jig-context-growth-) with the same session-id sanitization; the large-read size stat handles unreadable/nonexistent paths (stat failure -> size=-1 -> silent); _resolve_read_lean_bytes mirrors the sibling env resolvers; the shell branch gates on tool_name=='Read', stays silent for non-Read PreToolUse, parses stdin once, never blocks. Coverage is thorough and behavior-named. No correctness/security/robustness defects.

SPECIFIC ISSUES:
- [strength] context_fill.py — duplicate-vs-large priority correct and documented; large first-read doesn't consume the duplicate budget (test_duplicate_takes_priority_over_large).
- [strength] context_fill.py — large-read size stat wrapped: unreadable/nonexistent path -> size=-1 -> silent (test_unreadable_path_does_not_crash).
- [strength] context_fill.py — read-tracking state uses a distinct jig-read-paths- prefix from the growth nudge; provably no collision.
- [strength] jig-context-check.sh — PreToolUse branch gates on tool_name=='Read', wraps body in try/except, prints only on non-empty nudge; non-Read regression repeats an Edit 3x to prove no accumulation/nudge.
- [strength] tests — non-Read-silent regression + scaffold-wiring assertion (Read matcher lands; Edit|Write|MultiEdit undisturbed; project-relative path) both pinned.
- [nit] test_context_fill.py — ReadLeanDefaultsTests only asserts the default is a positive int; does not pin the 64 KiB value (cf. test_growth_bands_are_40_60_80) nor unit-test the JIG_READ_LEAN_BYTES out-of-range/non-numeric fallback (unlike _resolve_threshold/_resolve_growth_threshold which both have explicit fallback tests). _resolve_read_lean_bytes's fallback branch is unexercised at unit level.
- [nit] context_fill.py — the per-session seen list grows unbounded within a session, re-serialized on every Read (O(paths) x O(reads)). Tiny in absolute terms and a natural consequence of the PreToolUse(Read) mechanism; flagging for awareness.

RECONCILIATION NOTES:
- Record JIG_READ_LEAN_BYTES + 64 KiB default in the status-board Notes per Close-out. Two nice-to-haves: (1) add a unit test pinning the 64 KiB default + the malformed-value fallback (match the other env knobs); (2) note the unbounded in-session seen-list growth as accepted-by-design (consistent with the growth nudge's tmp-reaper deferral).

Provenance: reviewer jig:reviewer (read-only); prompt built by review.py pr-review.
