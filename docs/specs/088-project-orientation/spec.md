---
status: IN_PROGRESS
skill: spec-workflow
use_cases: []
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 088: Project orientation

> Reserved on 2026-07-12 via `workflow.py new`. Body to be drafted in a feature branch.

## Overview

Issue [#84](https://github.com/ramboz/jig/issues/84) reports a pickup failure in
scaffolded projects that have accepted architecture and draft slices but no generated
application code yet. An agent can inspect the shallow filesystem, call the project
greenfield, and ask the user to repeat decisions already captured in
`docs/architecture.md` and the slice corpus.

The creation path already has a deterministic project-state classifier in
`workflow.py new`; the implementation-pickup path has no equivalent computed
orientation step. Add a read-only `workflow.py orient --project-dir .` command that
prints one compact headline from jig's durable artifacts, and inject the same headline
automatically through a non-blocking `SessionStart` hook. The command reports scaffold
state, live spec rollups, and the slice currently requiring lifecycle attention. It
does not infer whether an application skeleton exists from generic filesystem layout.

## Current state (verified)

- `_common.scaffold_state.classify_scaffold_state()` classifies projects as
  `scaffolded`, `adoptable`, or `greenfield`; `workflow.py new` consumes it during
  spec creation.
- `workflow.py collect_slices()` already reads slice labels and lifecycle states
  across embedded and file-per-slice layouts, and `compute_spec_status()` derives
  spec rollups.
- `workflow.py session-plan` requires a caller-selected spec path, while the pickup
  instructions in `skills/spec-workflow/SKILL.md` and `docs/workflow.md` tell the
  agent to inspect the status board directly. No `orient` or project-level `status`
  command exists.
- Session-start hooks run context and semantic-index checks but emit no computed
  project-orientation headline.

## Assumptions

None.

## Decomposition

SPIDR — **Rules** axis. The missing behavior is one orientation rule applied at the
project pickup boundary. A single vertical slice delivers the complete user-visible
path: the CLI computes the headline, tests prove its selection rules and purity,
and the pickup documentation invokes it. Splitting CLI, tests, and guidance into
separate slices would be horizontal phasing. No Spike is needed because the relevant
classifier, lifecycle readers, and command surface were verified directly.

## Slices

- [088-01 — computed orientation at project pickup](slice-01-project-orientation.md)
