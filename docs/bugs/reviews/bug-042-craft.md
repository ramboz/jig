---
bug: 042
pass: craft
verdict: pass
reviewer: reviewer subagent (fresh, round 3 on the final code)
reviewed_at: 2026-11-21T02:43:55Z
prompt_source: pr-review skill craft pass
---

VERDICT: pass

REASONING:
`transition` computes `crosses_frame_gate` once and passes it to both gates. `_gate_frame_critique` validates ahead of the claim block and is silent under the bypass; `_gate_evidence` is the only `emit_gate_bypass` site on this path, so a bypassed move logs exactly one event for a gated target or a flagged crossing and zero for unflagged moves, back-edges and releases. With the gate enabled and a crossing to READY_FOR_IMPLEMENTATION / IN_PROGRESS, `_gate_evidence` matches neither validation branch and returns, so nothing is validated twice. The tests are discriminating; guards are labelled as guards. The reviewer was read-only (suite and ruff run by the implementer).

ROUND HISTORY (fresh reviewer each round):
- Round 1, needs-changes: refusal on an IN_PROGRESS target fired after the claim-ref reservation; "each pinned by a test" untrue for the unknown/missing-origin case; flag-reader mismatch between predicate and validator (embedded slices); nits — misleading "ungated FOR AN UNFLAGGED SLICE" comment, overlong docstring, function-local `import json`, hand-managed evidence state across subTests, undocumented READY_FOR_IMPLEMENTATION re-stamp / `--release` interaction, `required_passes` docstring pointer.
- Round 2, pass: should-fix items on stale record prose, a missing `--release` test and an at-least-one bypass assertion; nits on the bypass event being emitted before the claim refusals, fail-open `EvidenceError` branch, `commit.gpgsign` in the git fixture, a stale comment in `TransitionGateBypassTelemetryTests`.
- Round 3 (confirming pass on the final code, after the round-2 items were applied), pass (nits): two stale record sentences; flagged bypassed → IN_PROGRESS and → READY_FOR_REVIEW exactly-one cases unpinned; single blank line after `_gate_frame_critique`; one unwrapped SKILL.md line.

DISPOSITION (implementer, after round 3):
- Record sentences corrected; SKILL.md line rewrapped; second blank line added.
- Left as is: the two extra exactly-one subTests (same emit site as the pinned cases), the function-local `import shutil` (mirrors the fixture's `tearDown`), and the foreign-claim warning text.
