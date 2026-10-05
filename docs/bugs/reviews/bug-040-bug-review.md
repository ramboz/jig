---
bug: 040
pass: bug-review
verdict: pass
reviewer: jig:reviewer subagent
reviewed_at: 2026-10-05T01:26:03Z
prompt_source: review.py bug-review
---

Fix targets the documented root cause: the once-only record was per checkout while the contract (spec 080 / workflow template "at most one") is per repository; `suggestion_state_path` reuses the same `--git-common-dir` resolution as `resolve_repo_root`, so all worktrees of a clone share it, and legacy per-checkout records are still read. Regression tests use a real repo + `git worktree add` + the real helper. Bash-embedded python and the Codex renderer rewrite verified (generated Codex hook carries host='codex'). Non-blocking notes, all addressed in the record: explicit `"auto_attach": false` decline is a behaviour addition (recorded as owner-acknowledged scope), message text + write_state serialization changes recorded, Copilot host-label residual and servo-hint follow-up added to call-site closure, PATH pin dropped, comment literal reworded, double rev-parse removed.
