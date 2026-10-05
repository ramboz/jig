---
bug: 040
pass: craft
verdict: pass
reviewer: jig:reviewer subagent (2 rounds)
reviewed_at: 2026-10-05T01:26:03Z
prompt_source: pr-review skill craft pass
---

Round 1 needs-changes: usage.py `_activation_bucket` would report the new `opted_out` outcome as activation-failed (medium); unnecessary PATH pin in hook tests bypassed the CI matrix interpreter (low); architecture.md implied per-host record naming but Copilot uses `claude` (low); nits on a comment literal garbled by the Codex rewrite, a duplicated common-dir helper, double git rev-parse, an import outside try, and gpgsign-sensitive test commits. Round 2 re-verify: all fixed (`opted-out` bucket + test, shared `_git_common_dir()`, PATH pin removed, docs corrected, hook restructured, gpgsign disabled in test commits). Stdlib-only, py3.9-safe. Remaining optional nit: pass a precomputed legacy path into `_already_suggested`.
