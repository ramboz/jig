---
status: IN_PROGRESS
skill: scaffold-init
use_cases: []
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 096: scaffold-init defaults to plugin mode

> Reported on [issue #127](https://github.com/ramboz/jig/issues/127).

## Overview

**`scaffold-init` defaults to the heavier scaffold topology, silently.**
`scaffold.py` selects between two topologies on one axis (`with_machinery`):

- **plugin mode** (`scaffold_mode: "plugin-only"`) — write only the docs tree and
  host primer; skills/agents/hooks/templates stay under the installed jig plugin
  and run from `${CLAUDE_PLUGIN_ROOT}`.
- **in-repo mode** (`scaffold_mode: "in-repo"`) — additionally *copy* jig's whole
  machinery into the project's `.claude/`, so the project is self-contained.

Spec 016-03 made **in-repo the default**. So a no-flag scaffold copies jig's
machinery into the target — in one real scaffold, **79 tracked files**, about half
the repo, dwarfing the actual project. For the common case (a solo/personal
project on a machine that already has the jig plugin), that is the wrong default:
it creates two sources of truth that silently drift, pollutes the repo's file
count / diffs / history, makes ownership of the copied files ambiguous, and takes
the heavier commitment silently. The `--plugin-only` off-switch exists, but the
axis appears in none of the skill's five (content-only) Q&A questions, so an
operator never surfaces it and silently accepts in-repo.

in-repo is still the right choice when the plugin cannot be assumed present — CI /
cloud agents on a bare checkout, teams without universal jig install, archival
repos. The ask is not to remove in-repo; it is to make it the deliberate opt-in it
deserves to be, and make plugin mode the lean default.

## Decision (ADR-0039)

Recorded in [ADR-0039](../../decisions/adr-0039-scaffold-defaults-to-plugin-mode.md)
(Proposed): **default to plugin mode; in-repo behind an explicit `--in-repo`**,
for **both hosts**. Concretely:

1. Flip the `with_machinery` default to `False` (plugin mode).
2. Add `--in-repo` as the opt-in, with `--with-machinery` and `--copy-machinery`
   as aliases of the same switch. Keep `--plugin-only` (now redundant with the
   default) for clarity and back-compat.
3. Surface the axis as a sixth Q&A question in the skill.
4. Have the wizard's stdout summary name the chosen mode and why.

Rejected alternatives (see ADR-0039): keeping the in-repo default and only adding
the question + summary (leaves the heavy mode as the silent default for anyone who
skips the question); and a per-host default (the axis is host-independent — the
same objections apply to a Codex project whose plugin is installed).

## Security-floor note (ADR-0013)

Flipping the default does **not** strip jig's security floor, because the plugin
provides most of it. Probed against `hooks/hooks.json` and the plugin-only branch
of `scaffold()`:

- `.gitignore` secret patterns — written in **both** modes.
- secret-scan hook, spec-gate, context-check, and the other gates — **run from
  the installed plugin** in plugin mode (registered globally in the plugin's
  `hooks/hooks.json`), so they need no per-project copy.
- `## Security (MUST)` primer block — written in both modes.
- `permissions.deny` guardrails — the **one** part plugin mode does not seed
  (a plugin cannot write project `settings.json permissions`). This is the
  pre-existing behavior of the already-shipped `--plugin-only` path, not a
  regression introduced here. Whether plugin mode should also seed it is **out of
  scope** (ADR-0039 Open questions).

## Decomposition

SPIDR analysis. The change is one default flip plus its surfacing; four of five
axes collapse:

- **Spike:** none. The off-switch (`--plugin-only`) and both code paths already
  exist and are proven; nothing is unknown.
- **Paths:** one — the `with_machinery` selection in `scaffold.py`, shared by both
  hosts. No new copy/skip logic.
- **Interfaces:** the CLI flag surface (`--in-repo`/`--copy-machinery` aliases;
  flipped default), the wizard summary line, and the SKILL.md Q&A — all facets of
  the *same* user-facing choice, not separable value.
- **Data:** one field — `scaffold_mode` in `scaffold.json`, already emitted
  correctly for either value; no schema change.
- **Rules:** one — "no flag ⇒ plugin mode; `--in-repo` ⇒ copy machinery."

→ **One slice.** The vertical slice is "a no-flag scaffold produces a lean
plugin-mode project, in-repo is a deliberate opt-in, and the operator can see and
choose the axis." The flag, the summary, and the question are one coherent
behavior; splitting them would ship intermediate states with no standalone value.

## Slices

- [096-01 — default-plugin-mode](slice-01-default-plugin-mode.md)

## Out of scope

- **Seeding `permissions.deny` on the plugin-only path.** A real follow-up
  (ADR-0039 Open questions), but it changes what plugin mode *does*; this spec only
  changes which mode is the default.
- **A detected (rather than static) default** that picks in-repo when no plugin is
  present. Needs a plugin-presence probe that does not exist today (ADR-0039 Open
  questions).
- **Retrofitting already-scaffolded projects.** Projects already scaffolded in
  in-repo mode are untouched; this changes only what a *new* no-flag scaffold
  produces.
