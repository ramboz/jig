---
status: IN_PROGRESS
skill:
use_cases: []
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 075: Spec-lint-shipped-reference leak

> Reserved on 2026-06-19 via `workflow.py new`.

## Overview

Several **shipped** skills instruct the agent to run
`scripts/spec_lint.py`, but that script does **not** ship to consuming
projects. In the jig source repo `spec_lint.py` lives at `scripts/`, a
dev-only directory that `scripts/install_contract.py` excludes from the
release zip (only the allowlist `RELEASE_INCLUDE_SCRIPT_FILES` —
`verify_install.py`, `install_contract.py`, `scaffold_contract.py` — is
re-included). Neither `scaffold-init` nor `copy-machinery` copies
`scripts/` into a target; they copy `hooks/scripts/` only. So no
scaffolded/installed project ever gets the file.

Yet the installed plugin tells the agent to use it. The reference is in
two shapes:

- **Runnable instructions** (the agent literally tries to execute):
  - [`skills/migrate/SKILL.md:415`](../../../skills/migrate/SKILL.md) —
    `python3 scripts/spec_lint.py docs/specs/NNN-mM-slug/spec.md`
  - [`skills/migrate/worked-example-slice-to-spec.md:152`](../../../skills/migrate/worked-example-slice-to-spec.md)
  - [`skills/analyze/SKILL.md:70,88`](../../../skills/analyze/SKILL.md) —
    "run `scripts/spec_lint.py` first…"
- **Descriptive references** (send the agent looking for a file the
  project lacks):
  - [`skills/analyze/SKILL.md:12,65,370`](../../../skills/analyze/SKILL.md)
  - [`skills/spec-workflow/SKILL.md:68,80,90`](../../../skills/spec-workflow/SKILL.md)
  - [`templates/docs/specs/slice-template.md:72`](../../../templates/docs/specs/slice-template.md)
  - [`skills/analyze/worked-example-jig.md:142`](../../../skills/analyze/worked-example-jig.md)

The observed failure: a session in a *consuming* project (not the jig
source repo) was told by a skill to run `spec_lint.py`, found nothing,
and concluded "isn't shipped, so I'll skip lint." The check was silently
dropped. (`docs/specs/**` and `scripts/test_*` hits are repo-internal —
they don't ship — so they're out of scope.)

**Decision — ship it, don't scrub it.** The references encode a real
intent: structural spec-linting is part of jig's spec-driven workflow,
and `migrate`/`analyze` actively call for it. Removing the references
would delete a genuinely useful validator. Shipping makes the references
true.

### Current state (verified 2026-06-19)

- **`spec_lint.py` is pure-stdlib** — `import argparse, re, sys` and
  `from pathlib import Path` only; no `_common`, no third-party
  (`grep -nE '^(import|from)' scripts/spec_lint.py`). It ships with zero
  dependency drag — strictly simpler than the three scripts already in
  `RELEASE_INCLUDE_SCRIPT_FILES`, which pull in `_common`.
- The release-inclusion mechanism is **already proven** by those three
  sibling `scripts/*.py` files: they ship under their original `scripts/`
  path so import resolution works at `${CLAUDE_PLUGIN_ROOT}/scripts/`.
  Adding `spec_lint.py` is identical in kind — a one-line tuple addition.
- Shipped runnable references currently use a bare relative
  `scripts/spec_lint.py` (correct only when CWD is the jig repo root). In
  a consuming project, CWD is the project and that path does not exist;
  the resolvable path is `${CLAUDE_PLUGIN_ROOT}/scripts/spec_lint.py`
  (the form sibling skills already use for `workflow.py`/`review.py`).
- `skills/analyze/test_analyze_skill_surface.py` asserts the current
  reference text (`use \`scripts/spec_lint.py\` instead`, and the bare
  `scripts/spec_lint.py` string) — those assertions move with the prose.

## Assumptions

None.

_The shippability (pure-stdlib) and release-mechanism (proven by three sibling files) claims are verified in `## Overview` § Current state — not assumed._

## Decomposition

SPIDR — **Interface** axis (split by which consumer surface the fix
reaches), happy-path first:

- **075-01** delivers the core end-to-end fix: ship `spec_lint.py` in the
  release **and** correct the one reference that is actively executed
  (migrate's runnable command), with a regression test that the script is
  in the release artifact. After this slice, a consuming project that
  follows the migrate workflow gets the script *and* a command that
  resolves.
- **075-02** normalizes every remaining reference (analyze + spec-workflow
  SKILLs, slice-template, worked-examples) to the resolvable shipped path,
  and updates the surface tests that pin the old text. Completes
  consistency across all shipped surfaces.

Spike not needed — the unknowns (shippability, mechanism) are already
probe-resolved above.

## Slices

- [075-01 — ship spec_lint and fix the runnable reference](slice-01-ship-and-runnable-ref.md)
- [075-02 — normalize remaining shipped references](slice-02-normalize-references.md)
