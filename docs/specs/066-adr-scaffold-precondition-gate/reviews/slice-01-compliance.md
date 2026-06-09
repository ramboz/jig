---
slice: 066-01 — classify-and-route-on-adr-new
pass: compliance
verdict: pass
reviewer: general-purpose
reviewed_at: 2026-06-09T17:50:23Z
prompt_source: review.py implementation
---

VERDICT: pass

REASONING:
Slice 066-01 faithfully mirrors 063-01: the live ADR-creation door (`reserve_adr`, the only
path `adr.py new` reaches — `cmd_new` is unreachable from `main()`) now calls the shared
`classify_scaffold_state` to route greenfield→`/jig:scaffold-init` and adoptable→`/jig:migrate`,
gated by the shared `precondition_enabled()` bypass, with the classification running before any
file write or git call so refusals create nothing. All five ACs are met with meaningful tests
(message content + filesystem side-effects + git-call absence across all four states and both
bypass modes). The shared classifier is consumed unchanged (AC2) — `adr.py` imports it and
re-implements no trigger-counting. The full repo suite is green (2501 tests OK, exit 0; adr suite
124 OK) and ruff passes, satisfying AC4's no-regression bar.

SPECIFIC ISSUES:
(none)

RECONCILIATION NOTES:
- The bypass-path legacy refusal message was reworded vs. the original `cmd_new` text
  ("decisions directory not found: {adrs_dir}" -> "refusing: docs/decisions/ not found under
  {project_dir} ..."). Not a behavior regression (`cmd_new` is unreachable from the CLI and the
  scaffolded `reserve_adr` path never previously carried a docs/decisions/-absent check), but a
  slight deviation from a strict "identical observable output" reading of AC3. Worth a one-line
  deviation-log note.
- Two new `adrs_dir.mkdir(parents=True, exist_ok=True)` calls were added to compensate for
  removing the top-level `adrs_dir.is_dir()` guard that previously guaranteed the directory
  existed; both are inline-commented and mirror the pre-existing detached-worktree path. Note as
  the mechanical consequence of the precondition swap.
