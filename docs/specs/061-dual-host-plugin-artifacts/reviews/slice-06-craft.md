---
slice: 061-06 - Claude install verification
pass: craft
verdict: pass
reviewer: pr-review
reviewed_at: 2026-06-08T17:04:10Z
prompt_source: review.py pr-review <spec> 061-06 <deliverables>
---

VERDICT: pass

claude_install_smoke.py is a faithful, well-structured sibling of codex_install_smoke.py — shared SmokeResult/status constants/_run_command/_looks_surface_unavailable/exit semantics, correct UNAVAILABLE-vs-FAIL degradation, read-only `plugin validate`-only live probes, and stub-runner tests that need no real CLI and never mutate global config. Test quality strong (tight assertions, claude- prefix invariant asserted, timeout path covered, clean temp-dir hygiene).

BLOCKERS: none

NOTES:
- `run_smoke` declares `require_live_claude` but never uses it in-body (gating lives in `exit_code`); faithfully mirrored from the Codex sibling's same dead param. Candidate for a follow-up cleanup in both files.
- Justified divergence (deliberate, not a copy slip): `_run_command` uses `env=dict(env) if env else None` vs the Codex sibling's `env=dict(env)` — inherits parent env when `{}`, more robust for the scaffold-helper probe. Recorded in the deviation log.
- Cosmetic: module docstring AC-banner ordering puts AC5 before AC4; `_CaptureOut` defined after first use. Content accurate.
