---
slice: 080-01 - activation contract and opt-in state
pass: craft
verdict: pass
reviewer: jig-reviewer
reviewed_at: 2026-06-21T23:59:02Z
prompt_source: review.py pr-review docs/specs/080-semantic-index-auto-activation/spec.md 080-01 skills/_common/semantic_index.py skills/_common/test_semantic_index.py
---

VERDICT: pass

REASONING:
The implementation is scoped cleanly for the host-neutral slice, with bounded provider calls, explicit overlay gating, focused unit coverage, and an explicit empty provider registry that disables built-ins. The prior allowed_overlays=[] nit is resolved by key-presence handling, with regression coverage.

SPECIFIC ISSUES:
- [strength] skills/_common/semantic_index.py:222 — Explicit key-presence handling preserves allowed_overlays: [] instead of falling back to internal_overlays.
- [strength] skills/_common/test_semantic_index.py:91 — Regression test verifies an empty allowed_overlays list disables the legacy overlay fallback.
- [strength] skills/_common/semantic_index.py:396 — The registry selection preserves explicit empty provider registries instead of falling back to built-ins.
- [strength] skills/_common/semantic_index.py:322 — Injected internal providers still require overlay permission, which keeps Scout behind the internal boundary.

RECONCILIATION NOTES:
Record the resolved craft blockers/nit and the regression coverage for providers={} and allowed_overlays: [] precedence.
