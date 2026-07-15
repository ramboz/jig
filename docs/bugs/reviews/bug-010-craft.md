---
bug: 010
pass: craft
verdict: pass
reviewer: pr-review-subagent
reviewed_at: 2026-07-15T01:05:21Z
prompt_source: richer pr-review skill craft pass
---

The patch is narrowly scoped and matches the root cause: default Node runs use
bare `node --test` from project cwd while explicit paths and selectors retain
targeted behavior. Regression coverage exercises default discovery, explicit
paths, and selector ordering; documentation and generated host payloads are in
sync. No blockers or nits were found.
