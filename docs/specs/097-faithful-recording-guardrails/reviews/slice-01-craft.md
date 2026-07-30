---
slice: 097-01 — append-only accepted decisions convention
pass: craft
verdict: pass
reviewer: jig:reviewer (pr-review)
reviewed_at: 2026-07-24T23:06:22Z
prompt_source: review.py pr-review docs/specs/097-faithful-recording-guardrails/spec.md 097-01 <deliverables>
---

Craft (pr-review) pass on slice 097-01 by an independent jig:reviewer subagent.

VERDICT: pass. Cleanly scoped doc-only change (conventions template + 2 host mirrors + tests); faithful to the spec, mirrors match source.

SPECIFIC ISSUES:
- [nit][impl] test_scaffold.py test_template_keeps_proposed_records_editable — asserts bare 'edit' in section, which an inverted 'must never be edited' would also satisfy; strengthen to assert the editable sense ('edit freely' / 'edit its body inline'). Addressed in reconciliation (dogfooding this spec's own vacuous-test discipline).
- [strength][impl] conventions template Why-block preserves the 'rejected on the erased reasoning' nuance from issue #124.
- [strength][impl] both host mirrors identical to source (AC #3 holds).
