---
bug: 025
pass: craft
verdict: pass
reviewer: pr-review skill craft pass
reviewed_at: 2026-08-02T02:42:33Z
prompt_source: pr-review skill craft pass
---

High-craft fix. Both host builders single-source their runtime-scripts allowlists from install_contract (no duplicated literals); the host difference (Codex ships only host-neutral spec_lint.py; Claude ships the full trio) is correctly implemented and clearly documented; regenerated committed packages are byte-identical to source. New regression tests are well-structured, non-vacuous, and drift-proof; stale "no scripts" assertions were correctly relaxed to allow the allowlist while still banning dev tooling. Only pre-existing/minor nits, none blocking (the dangling test_runtime_scripts_only comment reference was subsequently corrected).
