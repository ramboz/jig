---
slice: 061-03 - host-package drift guard
pass: craft
verdict: pass
reviewer: pr-review (jig:reviewer)
reviewed_at: 2026-06-05T22:21:45Z
prompt_source: review.py pr-review <slice> 061-03 <deliverables>
---

Clean, idiomatic, well-factored. check_drift/_diff_packages/_file_map small + single-purpose; scratch-dir rebuild genuinely read-only (mkdtemp + finally rmtree, asserted). Failure message names stale path + regenerate command + git add. Tests cover determinism, in-sync, modified/missing/extra-file drift, both edge cases, --check wiring. Non-blocking nits: build_all returns claude_code or codex_code (Claude non-zero masks Codex in return; both still run+print); build_codex_plugin.build lacks an out= sink (asymmetric vs Claude builder); module docstring header lags ('061-02'); _Sink one-liner slightly clever. All cosmetic — recorded in deviation log.
