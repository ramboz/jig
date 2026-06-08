---
slice: 064-04 — derived-trigger
pass: craft
verdict: pass
reviewer: pr-review
reviewed_at: 2026-06-08T17:28:59Z
prompt_source: review.py pr-review (064-04 craft pass; re-reviewed after blocker fix)
---

VERDICT: pass

REASONING:
Tightly scoped, pure helper, correctly reads SPEC-level ## Assumptions as the primary signal (not a dead loop), mirrors arch-review-needed's exit-code contract, emits the frame phase first without disturbing arch/code-health ordering. All workflow tests green (309, exit 0).

HISTORY: First craft pass returned needs-changes for one [blocker] — `_assumptions_are_real` used a first-token placeholder check (split on `[\s—:.-]`), false-negativing a real assumption that begins with a placeholder word ("None of the dates are tz-aware", "TBD-style configs are validated") → silently suppressed the trigger (the failure mode 064 guards against). FIXED: switched to a dual rule — (a) a fully emphasis-wrapped line (`_..._`/`*...*`) is the template stub → placeholder; (b) a WHOLE-line bare-token match (trailing punctuation tolerated) → placeholder; anything else is real. Added regression test test_true_for_assumption_starting_with_placeholder_word (3 bullets → True); existing negatives (none/bullet-none/italic stubs/empty) still assert False. An independent focused re-review confirmed the blocker resolved with no new issue (the only conservative edge — a fully-italicized real assumption — is acceptable, since fully-italic prose is exactly the stub shape).

SPECIFIC ISSUES:
- [nit] frame-review-needed requires a slice positional even for an ADR target (short-circuited; mirrors arch-review-needed) — acceptable, docstring notes the short-circuit.
- [strength] derive_frame_review docstring explains why the assumptions-non-empty check subsumes the ADR-0020 external-dependency rule (those claims live in ## Assumptions per 064-02), avoiding a fragile NLP heuristic.
