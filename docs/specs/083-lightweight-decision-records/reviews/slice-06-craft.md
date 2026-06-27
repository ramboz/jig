---
slice: 083-06 — Widen the load-bearing-decision judgment prompt in BOTH session-end surfaces
pass: craft
verdict: pass
reviewer: jig:reviewer (Opus)
reviewed_at: 2026-06-26T19:45:29Z
prompt_source: review.py implementation/pr-review 083-05+06 (paired), read-only jig:reviewer
---

Craft pass (jig:reviewer, Opus, read-only). Slice 083-06: PASS. Both session-end surfaces widened with the identical canonical clause; memory-sync correctly identified as sole judgment owner for out-of-spec load-bearing decisions. Nit (addressed): the per-site "quoted identically in [list]" preambles were themselves unsynced free prose (each enumerated a different subset) — standardized all three to "single-sourced from ADR-0031, drift-tested verbatim across all four surfaces." Strengths: memory-sync prompt closes the loop (owner-gate confirm + route-to-ADR escape); ADR-0031 "consistency, not capture" scope section is unusually honest.
