---
slice: 078-01 — emit bypass events
pass: compliance
verdict: pass
reviewer: Explore (jig compliance)
reviewed_at: 2026-07-08T21:20:33Z
prompt_source: review.py implementation
---

Spec-compliance review of slice 078-01 (emit bypass events) against its 5 ACs. Retroactive review of shipped code (commit 5c31da0).

All five ACs met and meaningfully tested:
- AC1 (review-evidence transition emit) — workflow.py:889-898 emits inside `_gate_evidence` when the gate is disabled; covered by transition-bypass tests.
- AC2 (conventions hook emit) — jig-spec-gate.sh:61-72; driven end-to-end through the real bash hook by test_scaffold.py:250-277 (asserts exactly one content-free event).
- AC3 (no emit on normal path) — emit guarded in both gates; edge verified (blocked edit → zero events).
- AC4 (fail-open + content-free) — gate_telemetry.py:37-52 wraps all I/O in try/except; event carries only timestamp/event/gate/env_var/optional spec_ref; unit-tested (unwritable sink → no raise).
- AC5 (gitignored, local) — reuses .claude/skill-usage.jsonl (.gitignore:1); no third sink.

VERDICT: pass

Findings:
- [strength] conventions bypass tested through the real hook subprocess asserting exactly one content-free event — a fail-open-masked wiring regression would still be caught.
- [strength] fail-open + content-free realized by construction, both unit-tested.
- [nit] workflow.py:889-898 — bypass event emitted before the DONE dependency check, so a transition that later fails the dep check still logs a bypass (benign over-count; low severity). → deviation log.
RECONCILIATION NOTES: deviation log must be produced; consider recording the emit-before-DONE-dep-check over-count as a known accepted edge.
