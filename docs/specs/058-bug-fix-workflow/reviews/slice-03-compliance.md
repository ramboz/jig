---
slice: 058-03 — gated transitions: diagnose gate + red→green teeth + fix_class
pass: compliance
verdict: pass
reviewer: Linnaeus
reviewed_at: 2026-06-23T23:22:50Z
prompt_source: review.py implementation docs/specs/058-bug-fix-workflow/spec.md 058-03 skills/bug-fix/bug.py skills/bug-fix/test_bug.py hosts/claude/skills/bug-fix/bug.py hosts/codex/plugins/jig/skills/bug-fix/bug.py
---

VERDICT: pass

REASONING:
The implementation satisfies slice 058-03: diagnose gating is gnarly-blocking, standard-advisory, and bypassable; `FIXING` enforces `fix_class` plus red exit semantics; `REVIEWED` enforces green and routes failures back to `DIAGNOSING` with `## Already tried` evidence. The current tests cover the requested edge cases, including diagnose bypass, red/green test-gate bypasses, invalid/missing `fix_class`, invalid status, illegal ordering, red exit 0/2 handling, and green failure back-edge behavior. The Claude and Codex host copies match the source helper exactly.

RECONCILIATION NOTES:
None observed.
