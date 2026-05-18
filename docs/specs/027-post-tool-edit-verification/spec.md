---
status: DRAFT
skill: (none — dev infrastructure)
tier: (none — dev infrastructure)
---

# Spec 027: PostToolUse edit verification

## Overview

`hooks/hooks.json` wires `Edit|Write|MultiEdit` to `jig-spec-gate.sh`
as **PreToolUse** — gate-only, runs before the write happens. There
is no symmetric **PostToolUse** hook on the same surface. The
practical consequence: an agent that says "I added test X" is taken
at its word until the `reviewer` subagent runs hours later. By then
the context that produced the false claim is gone, and the deviation
log records "reviewer caught stale claim" rather than "agent caught
its own claim in the same turn."

This is the same anti-pattern that produced the 012-01 stale-CLAUDE.md-
labels finding, the 016-01 stale `014-` label sweep, the 017-* seven-
incident staleness catalog, and the 022-02 "stale SKILL.md prose at
4 locations" implementation review. Each was an edit that didn't land
the way the agent claimed it did, caught by a reviewer one or more
review-cycles later.

This spec adds a PostToolUse hook that re-reads the file region the
tool just touched and emits an `additionalContext` warning if a
basic self-check fails. The hook is intentionally cheap and best-
effort: a real reviewer subagent still catches semantic drift; this
only catches mechanical "the edit silently didn't take" or "the
claimed substring isn't in the file" cases — within the same turn,
before the context dissolves.

## Why now

- **Recurring root cause.** The deviation-log catalog above is the
  empirical signal. The reviewer subagent catches these reliably but
  late. Same-turn catching is structurally cheaper.
- **Hook event is available.** `PostToolUse` is documented in
  Claude Code's hook surface and already used by other projects;
  jig has no scope-claim conflict.
- **The PreToolUse half is in place.** `jig-spec-gate.sh` is the
  symmetric example — a small Python-3 hook script firing on the
  same matcher. PostToolUse extends the same pattern with no new
  primitives.

## Goals

1. **New PostToolUse hook.** Fires on `Edit|Write|MultiEdit`. Reads
   the tool result + tool input (e.g., `new_string`, `file_path`,
   `content`). Performs cheap, mechanical self-checks.
2. **Mechanical-only checks.** Specifically: (a) for `Edit`, the
   `new_string` is present in the file at the expected location after
   the edit (defends against silent no-op edits or partial writes);
   (b) for `Write`, the file content matches the requested content
   (defends against truncation or transcription drift); (c) for
   `MultiEdit`, every applied edit is verified individually.
3. **No semantic checks.** The hook does NOT try to verify ACs,
   tests, or claims — those stay with the reviewer subagent. Out-of-
   scope to prevent scope creep.
4. **Emits `additionalContext` on mismatch.** Names the file, the
   expected substring, and a one-sentence remediation suggestion
   ("re-read the file and retry the edit"). Never sets `continue:
   false` — same soft-warning stance as spec 026's context-fill
   warning.
5. **Opt-out via env var.** `JIG_POST_EDIT_VERIFY=0` disables. Off-by-
   default would defeat the point; on-by-default with documented
   opt-out is the right balance. Tests pin both states.
6. **Bounded cost.** The hook reads only the region the tool touched
   — not the whole file — and times out at ~2 seconds. A test pins
   that a 10MB file with a single-line edit doesn't full-file-read.

## Non-goals

- **No semantic verification.** Reviewer subagent's job.
- **No test-running.** TDD-loop's job.
- **No verification of `Bash` tool effects.** Bash output is too
  open-ended for cheap mechanical checks. Out of scope.
- **No automatic retry.** The hook surfaces a warning; the agent
  decides whether to retry. Auto-retry belongs in servo's loop driver,
  not in a single-turn hook.
- **No PreToolUse changes.** `jig-spec-gate.sh` stays as-is.

## Open questions

- **Where the hook script lives.** New file in `hooks/scripts/jig-
  post-edit-verify.sh`, parallel to existing five scripts. Pin in
  slice 027-01.
- **Multi-line edit detection.** Edit + Write produce a known
  `new_string` / `content`. MultiEdit's array is iterable; the hook
  walks each. Edge case: an edit that *deletes* (sets `new_string`
  empty); the check shifts to "old_string no longer present." Spell
  out in implementation.
- **Race with subsequent edits.** If the agent issues two rapid
  Edits to the same region, the post-check on Edit #1 may run after
  Edit #2 has already modified the region. Per Claude Code's tool
  serialization, this shouldn't happen — but worth a guard. Decide
  during slice 027-01: tolerate (best-effort) or warn (false-positive
  risk).

## Decomposition

One active slice.

### Slices

- [027-01 — post-edit-verify-hook](slice-01-post-edit-verify-hook.md) — DRAFT

## References

- **Originating conversation:** 2026-05-18 — AI-native review of jig,
  P0 item #5 ("No PostToolUse verification").
- **Servo counterpart:** Servo's oracle (spec 002) subsumes this for
  the unattended case — the oracle re-scores reality on every loop
  iteration. Jig keeps the in-turn check because supervised sessions
  don't run an oracle on every edit.
- **Existing parallel hook:** `hooks/scripts/jig-spec-gate.sh` — the
  PreToolUse half on the same `Edit|Write|MultiEdit` matcher; this
  spec mirrors its shape for the post-side.
- **Recurring-staleness evidence:** 012-01 deviation log §7; 016-01
  stale-`014-` label sweep; 017 staleness catalog (7 incidents);
  022-02 implementation review.
