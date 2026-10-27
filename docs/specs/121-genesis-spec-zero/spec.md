---
status: DONE
skill: scaffold-init
use_cases: [UC-1, UC-2, UC-11]
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 121: Genesis-spec zero

A freshly scaffolded project's own first spec will be `001`. The worked
example that `scaffold-init` seeds moves to a **genesis spec** `000-adopt-jig`,
the `002-first-spec` placeholder stops being emitted, and a project can drop
the genesis spec with one command once it no longer needs it. Implements
[ADR-0067](../../decisions/adr-0067-genesis-spec-zero.md).

## Overview

Slice [048-05](../048-guidelines-gap-response/slice-05-seed-reference-spec.md)
seeds two numbered specs into a greenfield `docs/specs/`: `001-adopt-jig` (a
`DONE` worked example) and `002-first-spec` (a `DRAFT` stub). Adopters keep
reporting two problems: their own numbering starts at `003`, and the seed is
noise they cannot safely delete once real specs exist.

Current state (probed 2026-10-26 on a fresh scaffold of this tree):

- `_emit_seed_spec` (`skills/scaffold-init/scaffold.py:3275`) copies every
  `templates/docs/specs/seed/**/*.md.template` into a greenfield specs dir.
- A seed renamed to `000-adopt-jig` (ids rewritten to `000-01`) passes
  `scripts/spec_lint.py --all`, renders on `workflow.py status-board`, and the
  next `workflow.py new my-feature --no-push` reserves `001-my-feature`
  (`_next_spec_number`, `workflow.py:3771`, is `max(NNN)+1`).
- Deleting the seed by hand leaves dangling links from `CLAUDE.md`,
  `AGENTS.md` (`templates/{CLAUDE,AGENTS}.md.template:24`) and
  `docs/adoption-readiness.md` (`templates/docs/adoption-readiness.md.template:35`)
  into `specs/001-adopt-jig/`, as `verify_install.py --mode scaffold`'s docs
  check reports. That check, and `check_scaffold_seed_present`
  (`scripts/verify_install.py:581`, which names all three seed files), run only
  at greenfield scaffold completion (`seed_expected`,
  `skills/scaffold-init/scaffold.py:4191`). A `--force` re-scaffold re-renders
  the primers unconditionally (`scaffold.py:3906-3931`) while skipping the
  seed, which would re-introduce the links.
- Shipped `skills/spec-workflow/SKILL.md` names `docs/specs/001-adopt-jig/`
  as the slice exemplar in two places.

Non-goals: renumbering existing projects' specs; deleting anything
automatically; amending the closed 048 record (ADR-0010 / spec 102 need a
separate owner approval for that).

## Assumptions

- No spec-number consumer on the genesis slice's path mishandles `000`. Probed
  for lint, status board, `new`, and the `.jig/spec-ref` stamp
  (`workflow.py:1036` tests the zero-padded string, which is truthy). Claim
  refs and cross-ref reads were not probed: the genesis slice is born `DONE`
  and never transitions.

## Decomposition

**SPIDR axis: Path.** The happy path is a new project getting the genesis
seed and its own `001`; the second path is an existing project (new or legacy
seed shape) shedding the seed. Each path is user-visible on its own.

## Slices

- [121-01 — genesis-seed](slice-01-genesis-seed.md) — scaffold seeds `000-adopt-jig`, no stub; the user's first spec is `001`.
- [121-02 — retire-genesis](slice-02-retire-genesis.md) — one command removes the genesis spec (new or legacy shape) and leaves the project verifying green; a one-line hint when the first own spec lands.
