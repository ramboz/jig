---
status: DONE
tier: standard
severity: high
claimed_by: claude/pr-186-review-fix-1bc497
regression_test: scripts/test_usage.py::Bug030UndercountDetectionTests::test_report_flags_undercounted_background_delegation
main_repro_checked_at: 2026-08-04
main_repro_ref: origin/main@16eb943
main_repro_result: reproduces
red_confirmed_at: 2026-08-04
green_confirmed_at: 2026-08-04
fix_class: structural_fix
security_surface: false
escalated_to:
---

# Bug 030: usage-report-misses-agent-subagents

Filed from the review of [PR 186](https://github.com/ramboz/jig/pull/186)
(originally proposed there as bug 029; renumbered to 030 because 029 was taken
on `main` by `slice-path-transition-silent-noop`, PR 188).

## Symptom

`scripts/usage.py` (spec 056 token-usage tracking) under-reports delegation and
per-spec cost for **background/detached** `Agent`-tool delegation. A session
that delegated via the background task queue (`run_in_background: true` —
`TaskCreate`/`Monitor`) is reported with a silent `SUBAGENT … turns: 0` and a
0% subagent share, so it looks like it delegated nothing when it delegated
heavily, and its delegated tokens are missing from the spec's combined total.

Concrete: `usage.py report 043` reports `SUBAGENT … turns: 0` even though the
043 build session made 16 `Agent`-tool delegation calls (implementers +
reviewers) through the background queue.

## Repro

1. Pick a session that delegated via the **background** task queue — its flat
   transcript opens with `type: "queue-operation"` records and carries
   `"name":"Agent"` tool_use blocks with `run_in_background: true` (e.g. the
   spec 043 build session in the primary jig project dir).
2. Run `python3 scripts/usage.py report 043`.
3. Before the fix: `SUBAGENT … turns: 0`, no signal that the number is
   incomplete — indistinguishable from a session that genuinely delegated
   nothing.

## Evidence

Empirical sweep of the live `~/.claude/projects` store (214 `Agent`-tool calls
across jig sessions) — this **corrects** the original PR-186 diagnosis, which
claimed the `Agent` tool never nests and always runs as separate top-level
sessions:

- **Foreground `Agent` delegation nests correctly** at
  `<session>/subagents/agent-*.jsonl` and is counted fine — verified 26/26 on
  one session, 2/2 on another. `usage.py`'s `find_subagent_files` handles these.
- **Background/detached `Agent` delegation does NOT nest** next to its
  orchestrator. Session `79153959` (13 background + 3 foreground calls) produced
  **0** nested files next to it; the subagent transcripts landed under a
  *different* session UUID (`9bd285aa`), or are not discoverably associated at
  all (the detached implementer's own first-person transcript is not on disk).
- Net: `find_subagent_files` globs `<session>/subagents/agent-*.jsonl`
  exclusively, so background-delegated turns are invisible to the parent-spec
  accounting — subagent turns read as 0 and combined cost omits those tokens.
- The original PR-186 quantitative evidence (095=0%, 096=~1%, 061=0%) could not
  be re-verified — those transcripts no longer exist on disk.

## Hypotheses

- [ ] H1: the `Agent` tool never nests (original PR-186 claim) — **falsified**:
  foreground delegation nests 1:1 with `Agent` calls (26/26 observed).
- [x] H2 (leading, confirmed): only the **background/detached** delegation path
  fails to nest; discovery keys on the nested-file shape that solely the
  foreground path (and the classic `Task` tool) produces, so background-queue
  subagents are never attributed to the parent.

## Root cause

`usage.py` subagent discovery assumes every delegated agent's transcript is a
child file of the parent session (`<session>/subagents/agent-*.jsonl`). That
holds for foreground `Agent` delegation (and the classic `Task` tool) but not
for background/detached delegation (`run_in_background: true`), whose transcript
is written under a different session UUID or not discoverably associated with
the parent at all. Because discovery globs the nested path exclusively,
background-delegated work is invisible: subagent turns read as 0 and combined
cost omits the delegated tokens — and, worse, the tool reported that 0 as if it
were ground truth, with no signal that it was incomplete.

## Fix class

`structural_fix` — pragmatic detect-and-warn (chosen over a full attribution
rework, which would be spec-sized and may be infeasible: the background
subagent tokens are not always recoverable from disk).

## Fix

`scripts/usage.py`:

- **Detect** the gap: new `count_agent_tool_calls(records)` counts `Agent`
  tool_use blocks in each flat session; the aggregation loop compares that
  against the nested files actually found (`find_subagent_files`). Any shortfall
  (`Agent` calls − nested files) accumulates onto `Report` /
  `TopReport` as `unattributed_subagent_calls` + `undercounted_session_count`.
- **Warn** instead of silently mis-reporting: `report` and `top` now print an
  explicit "⚠ under-counted … (background/detached delegation, bug 030) — treat
  as a floor, not the true cost" line whenever the shortfall is nonzero. The
  measured subagent/combined totals are unchanged (still a correct floor); the
  header docstring is corrected to describe the foreground-only nesting caveat.

Recovering the missing tokens exactly is explicitly out of scope for this fix
and would need a new attribution model (queue-operation linkage or timing/cwd
correlation).

## Already tried

n/a — root cause was reached by direct filesystem inspection of the transcript
store (foreground vs background nesting behaviour).

## Regression test

`scripts/test_usage.py::Bug030UndercountDetectionTests` — asserts the shortfall
is detected (`unattributed_subagent_calls == 3` for a 3-Agent-call session with
no nested dir), that the warning renders (`under-counted`, `bug 030`), that a
session whose delegation nests 1:1 is NOT flagged, and that
`count_agent_tool_calls` counts only `Agent` blocks.

## Proof

- Red: the `Report`/`TopReport` under-count fields and the "under-counted"
  render line are new — before the fix the assertions `AttributeError` /
  fail to find the string.
- Green: `python3 -m unittest scripts.test_usage` → 98 tests OK.
- Live: `python3 scripts/usage.py report 043` now prints
  `⚠ under-counted: 16 delegated Agent-tool subagent(s) across 1 session(s) …`
  where it previously showed a bare `turns: 0`.

## Learning

A token/attribution tracker that hard-codes one delegation mechanism's on-disk
layout silently rots when the workflow adopts a second mechanism. When the
recoverable data genuinely isn't there, the honest fix is to **detect and flag
the gap** rather than emit a trustworthy-looking wrong number — a silent `0` is
worse than a warned-incomplete `0`.
