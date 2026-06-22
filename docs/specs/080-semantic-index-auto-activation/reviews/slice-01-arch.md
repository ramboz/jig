---
slice: 080-01 - activation contract and opt-in state
pass: arch
verdict: pass
reviewer: jig-reviewer
reviewed_at: 2026-06-21T23:59:13Z
prompt_source: review.py arch-review docs/specs/080-semantic-index-auto-activation/spec.md 080-01 skills/_common/semantic_index.py skills/_common/test_semantic_index.py
---

VERDICT: pass

REASONING:
The helper fits skills/_common as a stdlib-only shared contract for both host adapters, without Claude/Codex-specific behavior in the callable surface. Public-vs-internal boundaries are coherent: public providers are the default registry, Scout is gated behind explicit overlay permission, and failures return compact status rather than blocking. Telemetry is content-free and fail-open, matching the slice's local instrumentation boundary.

SPECIFIC ISSUES:
- [strength] skills/_common/semantic_index.py:3 — Declares and implements the helper as stdlib-only shared contract code, which matches the _common boundary in docs/architecture.md.
- [strength] skills/_common/semantic_index.py:197 — Keeps Scout out of the public registry unless internal overlays are explicitly enabled.
- [strength] skills/_common/semantic_index.py:361 — Telemetry boundary is content-free and fail-open, avoiding command output or repository content leakage.

RECONCILIATION NOTES:
Record the strengths above; no deviations observed.
