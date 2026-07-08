---
slice: 078-01 — emit bypass events
pass: craft
verdict: pass
reviewer: Explore (jig craft)
reviewed_at: 2026-07-08T21:20:33Z
prompt_source: review.py pr-review
---

Craft / PR-review pass of slice 078-01 (emit bypass events). Retroactive review of shipped code (commit 5c31da0).

VERDICT: pass

Scope matches the slice exactly (adds gate_telemetry.py; wires the two in-scope gates only; reuses the sink with an `event` discriminator; does not touch deferred gates, does not make gates harder to bypass, does not add the digest). No blockers.

Findings:
- [strength] fail-open by construction (bare except: pass), verified by three separate unwritable-sink tests.
- [strength] content-free by construction: the signature has no channel for diff/secret content; tests assert sensitive tokens never appear.
- [strength] test pins that the hook emits only on an actual gated-file edit, not merely when the approval env var is set (catches an over-emit trap).
- [strength] sink reuse with an `event`-keyed filter mirrors spec 041's routing_stats pattern; append-single-write is the correct concurrent-log idiom.
- [nit] gate_telemetry.py:24,55 — `project_dir` untyped while return type is annotated; call-sites pass str (hook) and Path-derived (workflow). Annotate `project_dir: str | os.PathLike`. → deviation log.
- [nit] workflow.py:887-898 — the review-evidence emit fires for any transition into a gated state when the gate is disabled, including a READY_FOR_REVIEW transition on a slice WITHOUT frame_review (where the enabled gate's required set is empty — nothing to bypass), recording a phantom bypass that slightly inflates the gate_stats count. Arguably acceptable (the disable flag was honored on a transition the gate owns). → deviation log.
RECONCILIATION NOTES: (1) docs/memory/learnings.md:~397-400 says skill-usage.jsonl "has two writers — filter event=='skill_invoked'"; 078 adds a THIRD event type/writer (gate_bypassed) — note now stale, fix in memory-sync. (2) host-vendored copies already carry the module (parity confirmed). (3) both nits defer-worthy, non-blocking.
