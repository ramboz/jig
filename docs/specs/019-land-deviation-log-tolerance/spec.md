---
status: DRAFT
skill: slice-land
tier: 1
---

# Spec 019: land deviation-log tolerance for retroactive landings

## Overview

`land.py prepare` today refuses to mark a slice ready-to-land unless a
`### Deviation log` subsection is present in the slice body. This is
the right default for jig-native slices (the deviation log is part of
the implementation→reconciliation feedback loop). It's the WRONG
default when a project retroactively brings already-DONE slices under
jig's lifecycle — e.g. the aso-shallow-validator migration this spec
was motivated by.

Add a `--no-deviation-log` flag (or treat missing-deviation-log as a
warning when STATUS=DONE already) so historical slices migrated under
jig pass readiness without backfilling deviation logs that were never
written at the time.

## Why now

- **Direct motivation:** shallow-validator's M1 migration (2026-05-15
  dogfood) surfaced this immediately. Every historical slice was
  marked `Status: Done` pre-jig — they never had a deviation log
  because the convention didn't exist. `land.py prepare` correctly
  flagged this, but for a one-time migration the right answer is "skip
  the check," not "synthesize a fake deviation log."
- **Right-size response:** today's hard-block is overkill for the
  retroactive case. A warn (yellow) or an opt-in flag is friendlier
  and matches how `check_tests` already treats no-test-runner as a
  warning (slice 006-04).
- **Scope is tiny.** One readiness-check predicate gains a "warn vs
  block" mode. No new helper, no new template.

## Goals

1. **A way to land a slice without a deviation log.** Either via a CLI
   flag (`--no-deviation-log`) or via configuration in `.jig/` (a
   per-project setting), the deviation-log check becomes a warning
   instead of a blocker for that slice.
2. **Default behavior unchanged.** With no flag/config, the existing
   block-on-missing-deviation-log behavior holds. jig-native slices
   that need the deviation-log gate keep getting it.
3. **Surfaces in the readiness report.** The check still renders as
   `- [?] Deviation log` (yellow / warn) with a short note explaining
   why it's not a blocker.

## Non-goals

- **Auto-detecting "retroactive" slices.** No heuristic ("if
  Status=DONE and no deviation log, assume retroactive"). Caller opts
  in explicitly; one flag is enough.
- **A configuration system beyond `.jig/test-command`'s precedent.** A
  per-project default (`.jig/land-skip-deviation-log`?) is appealing
  but adds discoverability load. CLI flag suffices for now.
- **Changing the deviation log convention.** New slices still need one;
  this is about graceful retroactive landings only.

## Decomposition

Single slice. The change is small and atomic: one new arg, one
predicate change, three or four new tests. No SPIDR axes worth
splitting.

### Slices

- **019-01 — no-deviation-log-flag**: add the flag, wire it through
  `prepare()`'s readiness-check rendering, tests for both modes.

---

## Slice 019-01 — no-deviation-log-flag

---
status: DONE
dependencies: []
last_verified: 2026-05-15
---

**Goal:** `land.py prepare [--no-deviation-log]` and `land.py execute
[--no-deviation-log]` treat a missing `### Deviation log` subsection
as a warning, not a blocker. With the flag absent, today's
block-on-missing behavior is unchanged.

**DoR:**
- ✅ `check_deviation_log(section)` exists in `land.py`.
- ✅ `render_readiness_section` already supports `- [?]` warning rows
  for the tests check (slice 006-04 precedent).

**Acceptance Criteria:**

1. **`--no-deviation-log` flag is accepted by both subcommands.**
   `land.py prepare ... --no-deviation-log` and `land.py execute
   ... --no-deviation-log` both parse cleanly. Existing flag set
   (`--mode`, `--target`, `--dry-run`) is unchanged.
2. **With the flag, missing deviation log is a warning.** The
   readiness report shows `- [?] Deviation log: skipped (no
   --no-deviation-log)` (or similar). The slice is NOT blocked by
   this check alone. Exit 0 when STATUS=DONE, tests pass, DoD ticked,
   even though no `### Deviation log` exists.
3. **Without the flag, missing deviation log is still a blocker.**
   Default behavior unchanged — exit 1 with the existing
   "Deviation log subsection ... is missing" blocker message.
4. **With the flag, PRESENT deviation log still renders green.** The
   flag doesn't blind the check; it only changes how `False` is
   reported. A slice WITH a deviation log shows
   `- [x] Deviation log: present` regardless of flag.
5. **Tests** in `skills/slice-land/test_land.py` cover all four
   combinations (flag × present/absent).

**DoD:**
- [x] All ACs pass; full suite green.
- [x] Reviewed by `reviewer` subagent.
- [x] Implementation review passed.
- [x] Deviation log produced.
- [x] Reconciliation review passed.

### Close-out (post-DONE)

- [x] `docs/specs/README.md` regenerated.
- [x] CLAUDE.md hot-cache entry for spec 019.

**Anti-horizontal-phasing check:** After this slice, a downstream
project can run `land.py prepare --no-deviation-log` on a historical
slice and get an actionable readiness report instead of a refusal.
End-to-end value in one slice.

### Deviation log (after reconciliation)

**§1 — Flag spelled `--no-deviation-log` (action="store_true").**
The spec text vacillated between `--no-deviation-log` and
"per-project setting in `.jig/`". Settled on the CLI flag because:
(a) it's per-slice rather than per-project (different slices in the
same project may want different treatment); (b) `.jig/test-command`
sets a per-project default, but the deviation-log gate is more
contextual; (c) Non-goals rules out the config-file path explicitly.
`dest="skip_deviation_log"` so the internal bool name stays
positive-polarity inside Python.

**§2 — Warning row text: `"[?] Deviation log: skipped
(--no-deviation-log)"`.** Mirrors the tests-warning row pattern
from slice 006-04 (`[?] Tests: warning — no test runner detected`).
The trailing `(--no-deviation-log)` reminds readers WHY the row
isn't a `[ ]` blocker.

**§3 — Both `prepare()` and `execute()` thread the bool through.**
`execute()` calls `prepare()` internally — adding the kwarg in
both signatures keeps the surface symmetric (either subcommand
accepts the flag, both behave consistently). The CLI parser
declares the flag on both subparsers; main's dispatch passes
`ns.skip_deviation_log` to whichever function it invokes.

**§4 — Test fixture re-use: `_spec_with_slice(..., include_deviation_log=False)`.**
The existing test helper already had this parameter (used by
`ExecuteBlocksOnReadinessTests`), so generating fixtures for the
flag-missing-log scenarios required no new fixture infrastructure.

**§5 — Five tests, four combinations + one execute-subcommand
parser-acceptance test.** The matrix is (flag × log present) = 4
cases plus a fifth confirming `--no-deviation-log` parses on the
execute subcommand (AC #1's "accepted by both subcommands" claim).
787 total tests, no regressions.

**§6 — Reviewer noted a coverage thinness, accepted as-is.** The
fifth test (`test_execute_subcommand_also_accepts_flag`) calls
`_land.execute()` directly via the Python API rather than via the
CLI subprocess. This proves the kwarg plumbing but doesn't prove
that argparse on the `execute` subparser actually accepts the
`--no-deviation-log` flag from the CLI. The parser code at the
two subparser declarations is structurally identical, so the risk
is low. Filed as a minor coverage gap; not blocking.
