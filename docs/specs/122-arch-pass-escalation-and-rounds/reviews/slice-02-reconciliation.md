---
slice: 122-02 — arch-round-carry-over
pass: reconciliation
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-11-19T00:59:01Z
prompt_source: review.py reconciliation docs/specs/122-arch-pass-escalation-and-rounds/spec.md 122-02
---

VERDICT: pass

REASONING:
The 122-02 deviation log holds against the code: `_ROUND_PREAMBLE`/`_ROUND_PROHIBITIONS` replace the standard text only when an arch record exists (review.py:153-201,1113-1116,1204), "Previous round" renders after "Evaluate", and the round-line block no longer says "below". Beyond-AC additions (id definition, reviewer.md opening line) are logged; the bug-review comment, guard and new-behaviour tests, "record as returned" in both SKILL.md files, the owner-approved conventions.md exception and the round-2 arch envelope all match. architecture.md and workflow.md describe what was built; host copies carry the changes. The sweep had weak spots but nothing dishonest.

SPECIFIC ISSUES:
- slice-02 sweep (scaffold templates row) — (Medium) The `no-op` reason misdescribed `workflow.md.template`. (Reworded.)
- slice-02 sweep (evidence row) — (Medium) Listed the reconciliation record before it existed. (Marked as written after this review.)
- slice-02 sweep (exclusion row) — (Medium) Exclusion explained only base drift, not 122-01's own branch changes. (Widened.)
- reviews/slice-02-compliance.md / slice-02-craft.md — (Medium) Recorded after the deviation-4 edits over bodies that predate them; state which pass saw the edits. (Added: round-2 arch only.)
- reviews/slice-02-craft.md:9 — (Low-Medium) `applied_skill: unknown` despite `--richer-skill pr-review`. (Logged.)

RECONCILIATION NOTES:
- No principle violations; jig does not parse the round line, keeping the deterministic/judgment split.
- No over-build; the `str.replace` derivation is guarded by test_review.py:4433-4434.
