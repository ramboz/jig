---
status: DONE
skill: migrate
tier: 0
---

# Spec 021: migrate copies machinery into target's `.claude/`

## Overview

Spec 016 (scaffold-mode) taught `scaffold-init` to copy
`skills/` + `agents/` + `hooks/` + `settings.json` into the target
project's `.claude/` directory, with SKILL.md path-string rewriting,
hook-script copy, and settings.json merge against the
`managed_by_jig` marker. Slice 016-03 flipped `--with-machinery` to
default-on, making scaffolded install the default shape for greenfield
projects.

Spec 008 (slice 008-05) made `scaffold-init` refuse on already-spec-driven
layouts and route the user to `/jig:migrate`. But `/jig:migrate` only
ships doc-shape operations today (`report`, `rename-decisions`,
`split-slices`) — it has no equivalent of `scaffold-init`'s
machinery copy.

Net effect: a project adopting jig via the migration path lands in
plugin-mode by default, with no path to the scaffold-mode parity that
spec 016 made the default for greenfield. The two specs landed in
parallel and never reconciled.

Spec 021 closes the gap by adding `migrate.py copy-machinery
<project-dir>` — a single new subcommand that reuses scaffold-mode's
helpers verbatim. After this spec, the two adoption paths produce
identical `.claude/` shapes.

## Why now

- **Direct user signal (2026-05-15):** conversation in worktree
  `nice-stonebraker-152c09` surfaced the gap explicitly. A migrating
  project that asks "where are my hooks?" gets no answer from
  `/jig:migrate` today.
- **Reconciliation between specs 008 and 016 is overdue.** When
  scaffold-mode landed (016-03 flipped the default 2026-05-15) the
  migrate path was not updated. Every `/jig:migrate` user since then
  has gotten worse-than-greenfield treatment by default.
- **Implementation cost is low.** scaffold.py's machinery-copy
  helpers (`_copy_skills_and_agents`, `_copy_hooks_and_register`,
  `UnmanagedHooksError`) are already factored out as small functions.
  Lifting them behind a public façade `copy_machinery()` is a one-hour
  refactor; the new subcommand is another hour of glue + tests.
- **No competing approach.** Unlike spec 020 where a deterministic
  helper was the wrong shape, this work is purely mechanical: copy
  files, rewrite path strings, merge settings.json. The judgment was
  already done in spec 016.

## Goals

- A `/jig:migrate` user can run a single subcommand to bring their
  project's `.claude/` to scaffold-mode parity.
- Code reuse, not parallel implementation. scaffold.py's
  machinery-copy logic is the source of truth; migrate.py calls into
  it via a public façade.
- The same safety guarantees that 016-02 / 016-03 already enforced
  (UnmanagedHooksError refusal, executable-bit pinning, marker-based
  settings.json merge) apply to migrate's invocation unchanged.
- The `migrate.py report` operations section is updated to suggest
  the new subcommand at the appropriate verdict, so users discover
  it through the same channel that surfaces `rename-decisions` and
  `split-slices` today.
- Documentation in `skills/migrate/SKILL.md` mirrors the shape of
  spec 016's coverage in `skills/scaffold-init/SKILL.md`.

## Non-goals

- **No refactor of scaffold.py's internals.** The existing
  `_copy_skills_and_agents` / `_copy_hooks_and_register` functions
  stay where they are. We add a public wrapper, we don't move the
  underscored helpers to `_common`. (A future spec can lift them to
  `skills/_common/machinery.py` if a third caller appears; YAGNI
  today.)
- **No interactive Q&A in `migrate.py copy-machinery`.** scaffold-init
  has the wizard; migrate is post-scaffold and skips it. The
  subcommand takes a project directory and an optional `--force` and
  that's it.
- **No partial / per-skill copy.** scaffold-mode copies everything
  or nothing; migrate inherits that shape. A user who wants
  selective copy can run, then delete what they don't want.
- **No automatic invocation from `migrate.py report`.** The report
  remains read-only (per slice 008-01's contract). It suggests the
  next operation; the user runs it.

## Decomposition

Single vertical slice. The work is mechanical and the seam between
scaffold.py and migrate.py is clean; splitting "extract façade" from
"call façade" would be horizontal phasing.

### Slices

- [slice-01-copy-machinery-subcommand](slice-01-copy-machinery-subcommand.md) (DRAFT)

## SPIDR analysis

**Path** chosen. The work is one happy-path operation (copy
machinery) with the same refusal rule scaffold-mode already enforces
(unmanaged hooks). No data-shape variation, no rules-axis branching,
no novel interface — the subcommand parallels the existing report /
rename-decisions / split-slices shape exactly. Spike would be
unjustified: spec 016 already validated every step end-to-end.
