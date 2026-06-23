---
status: DONE
skill: memory-sync
tier: (none — dev infrastructure)
---

# Spec 050: solo-to-team re-detection

## Overview

`/jig:scaffold-init` runs a team-signal check at initialization
(≥2 distinct git contributors, mailmap-aware, monorepo-guarded) and
generates `docs/memory/people.md` only when the signal fires. A
project that starts solo and grows past one contributor never gets
nudged — the signal is evaluated once and never re-evaluated.

This means projects scaffolded on day one as solo work that later
acquire collaborators silently miss the people-context layer that
the memory architecture provides. The agent has no per-person
context for attribution, message framing, or "who owns this module"
decisions — exactly the cases `people.md` was designed for.

This spec adds a **periodic re-check** of the team signal. The check
piggybacks on an existing maintenance touchpoint (lean: `memory-sync`)
rather than introducing a new helper or hook. When the re-check
fires and the project has grown past solo, the user is nudged to
bootstrap `people.md` — not silently generated, because the original
scaffold-init flow gave the user an explicit opt-in moment and the
re-check should preserve that.

## Why now

- **Empirical drift.** Projects that begin as solo work and grow are
  common. jig itself was scaffolded solo and now has a CLAUDE.md
  contributor pattern that benefits from being made first-class.
- **Cheap to add.** The detection logic exists in scaffold-init
  ([signal-detection-findings.md](../001-scaffold-init/signal-detection-findings.md)).
  Re-using it from `memory-sync` is import-and-call.
- **Solves a silent failure.** Missing `people.md` doesn't break
  anything visibly — the agent just operates without per-person
  context. Silent failures are the worst kind because no one
  notices to fix them.
- **Memory layer is the natural home.** `people.md` lives under
  `docs/memory/`. The maintenance pattern for the rest of that
  folder (memory-sync) is where the team-context check belongs.

## Goals

1. **Re-run team signal during `memory-sync`.** When the user
   invokes `/jig:memory-sync` (or it auto-fires at session end),
   re-evaluate the team signal. Reuse `scaffold-init`'s detection
   helper — no parallel implementation.
2. **Nudge, don't silently generate.** When the signal fires AND
   `docs/memory/people.md` is absent, surface a structured prompt
   to the user: "Project has grown to N contributors; bootstrap
   `people.md`? (y/n/never)". `never` writes a `.jig/no-people-md`
   marker that suppresses future nudges (parity with other
   user-overrides in the project).
3. **Refusal to overwrite.** If `people.md` already exists, the
   re-check is a no-op regardless of signal. Manual edits are
   preserved.
4. **Skip when scaffold-init opted out.** If `.jig/no-people-md`
   exists (set by `scaffold-init --solo` or a prior nudge-declined),
   skip the re-check entirely. Don't keep asking.
5. **Threshold parity with scaffold-init.** Re-check uses the exact
   same signal definition as scaffold-init (≥2 distinct git
   authors after mailmap normalization, monorepo parent-repo guard).
   No new threshold, no signal drift.
6. **Visible diagnostic.** `workflow.py stale` (or a sibling check)
   surfaces "project signals team but `people.md` is absent" as a
   freshness audit item — gives the user a way to discover the
   drift without waiting for `memory-sync`.

## Non-goals

- **No auto-population of `people.md` entries.** Bootstrapping
  generates the template scaffold (same shape as scaffold-init's
  output). The user fills in per-person context — the agent doesn't
  guess from git log.
- **No per-person git-log mining.** Contributor counts gate the
  signal; *which* names get entries in `people.md` is the user's
  call, not derived from `git shortlog`.
- **No re-check on every session.** The check fires on `memory-sync`
  invocation (manual or auto-at-end), not on every Stop hook.
  Avoids nudge fatigue.
- **No automatic team→solo regression.** If a project's contributor
  count drops back to 1 (e.g., one person leaves), the re-check
  does NOT delete `people.md`. People-context outlives team-size
  changes.
- **No cross-repo nudging.** Each project's signal is evaluated in
  isolation. No "you've collaborated with X in repo Y; add them
  to people.md in repo Z" inference.

## Open questions

_All four resolved 2026-06-04 before implementation (recorded here; the
spec is still DRAFT, so corrected inline per ADR-0010)._

- **`memory-sync` integration point.** **RESOLVED:** a new
  `memory.py team-check` subcommand, which `memory-sync`'s SKILL.md
  runs as its final step (matches the existing "invoke `memory.py`
  once per item" pattern; lets slice 050-02's `stale` import the same
  helper). The separate-`workflow.py`-command alternative was rejected
  as over-engineering.
- **Nudge UX shape.** **RESOLVED:** structured `[y]/[n]/[never]`
  advisory. A real `input()` prompt fires only when stdin is a TTY
  (AC7 guards the non-TTY path); `--bootstrap` / `--never` flags let
  the agent act on the user's choice in non-TTY (agent-invoked)
  context.
- **`scaffold-init` parity.** **RESOLVED (yes, explicit-only):**
  `scaffold-init --solo` writes a **tracked** `.jig/no-people-md`
  marker (project-level opt-out, like `.jig/test-command`).
  *Auto-detected* solo does NOT write it — otherwise a project
  scaffolded solo that later grows would be permanently suppressed,
  defeating this spec. The `Overrides` dataclass already distinguishes
  an explicit `--solo` (is_team=False) from an inferred solo (None),
  so the marker is written iff the override is explicitly False.
- **Stale-audit signal shape.** **RESOLVED:** a finding row inside
  `workflow.py stale` carrying a `category: team-context` tag (no new
  command surface), consistent with how `last_verified` drift is
  surfaced today.

**Implementation note (threshold parity).** `detect_team()` returns
only a `bool` but the nudge and the stale row need the contributor
count N. The count-of-distinct-mailmap-authors logic is extracted into
a sibling helper returning `int`; `detect_team` becomes
`return <count>(...) >= 2`. Both skills import the shared helper, so
the `≥2` threshold lives in exactly one place (AC6 parity is then
structural, not asserted-by-coincidence).

## Decomposition

Two slices, sequenced. SPIDR Interface-axis split.

### Slices

- [050-01 — memory-sync-team-recheck](slice-01-memory-sync-team-recheck.md) — DONE
- [050-02 — stale-audit-team-signal](slice-02-stale-audit-team-signal.md) — DONE

## References

- **Originating conversation:** 2026-05-28 — review of jig's multi-
  contributor story. Re-detection identified as the missing back-
  edge in scaffold-init's once-only team signal.
- **Pattern precedent:** `scaffold-init`'s team-signal detection
  ([signal-detection-findings.md](../001-scaffold-init/signal-detection-findings.md)),
  mailmap normalization, monorepo guard.
- **Adjacent spec:** Spec 049 (slice-claim on IN_PROGRESS) —
  different mechanism, same "multi-contributor support gaps" theme.
  Kept separate because the code paths and reviewers don't overlap.
- **Doctrine:** Spec 028's "narrow locks where the failure was
  observed" generalized: narrow nudges where the silent drift was
  observed. `people.md` absence is the empirical drift; this spec
  closes it.
