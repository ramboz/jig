---
slice: 122-02 — arch-round-carry-over
pass: compliance
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-11-19T00:45:35Z
prompt_source: review.py implementation docs/specs/122-arch-pass-escalation-and-rounds/spec.md 122-02 <5 deliverables>
---

VERDICT: pass

REASONING:
All five ACs and both edge cases are met. `_previous_arch_record` (review.py:179-186) resolves `evidence_path(..., "arch")` and returns None on `EvidenceError`, so an embedded slice or another pass's record yields the standard round-1 prompt. Preamble, prohibitions and the "Previous round" block change only inside `build_arch_review_prompt` (review.py:1112-1115), with the block after "Evaluate" (review.py:1203). The round line is asked for in both cases; `agents/reviewer.md:40-44` states the exception and the host copies carry it. Tests and `--check` were not run (read-only reviewer).

SPECIFIC ISSUES:
- skills/independent-review/test_review.py:4429-4432 — [Medium] The "keeps the ban" half of AC1 is not pinned: "implementer's reasoning" also appears in the Previous round block. Assert the new bullet text.
- skills/independent-review/review.py:174 — [Medium] `_ROUND_LINE_BLOCK` says the record is "named below"; it renders above.
- skills/independent-review/test_review.py:4478-4490 — [Low/Medium] The byte-identity test never asserts returncode 0, and leaves out bug-review (slice-independent).
- skills/independent-review/test_review.py:4493-4499 — [Low] `test_round_prohibitions_differ_from_the_standard_block` leaks `sys.path` and duplicates an existing assertion.

RECONCILIATION NOTES:
- The id definition ("short stable name … no line number") is an addition beyond the ACs (interpretation of spec A3).
- The reviewer.md preamble qualifier goes beyond AC5's prohibitions-only exception.
- The record path is printed as given (relative or absolute).
