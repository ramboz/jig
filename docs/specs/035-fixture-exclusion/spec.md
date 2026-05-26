---
status: DONE
skill: scaffold-init
tier: (none — dev infrastructure)
---

# Spec 035: Exclude test fixtures from scaffold and release artifacts

## Overview

`skills/migrate/fixtures/` is pytest test data (four subtree shapes:
`greenfield/`, `partial/`, `conflict/`, `tiny-validator/`) that ships to
end users by **two independent paths**:

- **Scaffold mode** — `scaffold.py:_copy_skill_dir` mirrors every file
  under each skill dir except `__pycache__` and `test_*.py`. `fixtures/`
  is not excluded, so a `scaffold-init` run drops the entire fixtures
  tree into `.claude/skills/jig-migrate/fixtures/`.
- **Release zip** — `scripts/build_release_zip.py:_iter_files` excludes
  `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.pyc`, `.DS_Store`,
  and `test_*.py`. `fixtures/` is not excluded, so every plugin install
  from `jig-vX.Y.Z.zip` carries the same payload under
  `${CLAUDE_PLUGIN_ROOT}/skills/migrate/fixtures/`.

Same root cause in two places. End-user impact per project is small
(~232 KB) but the **shape is wrong**: a runtime install of a skill
should not contain that skill's test corpus. If another skill grows
test fixtures later, this bug recurs by default.

## Why now

- **Cleanly verifiable.** Verification on 2026-05-26 confirmed both
  code paths still have the gap (see Current state below).
- **Smallest brief in the external-review batch.** Recommended as the
  Phase 1 loop-validation spec — confirms the brief → spec → slice →
  implement → review loop works on this material before committing to
  the larger work.
- **Fixes both paths symmetrically.** A single rule ("`fixtures/` dirs
  are test data, never runtime") covers both install surfaces.

## Goals

1. **Exclude `fixtures/` directories from both copy paths.** Match the
   existing `__pycache__` semantics: a `fixtures/` dir anywhere in the
   skill subtree is skipped.
2. **Generalize so future skills inherit the protection.** A skill that
   later grows `fixtures/` for tests is protected by default — no
   per-skill opt-in.
3. **Pin with regression tests on both surfaces.** A `fixtures/` dir
   present in the source must be absent in the output on both
   scaffold copy and release zip.

## Non-goals

- **No restructuring** of where fixtures live. They stay at
  `skills/migrate/fixtures/`; only the *copy* paths change.
- **No allowlist redesign.** Just extend the existing deny lists.
- **No audit of other skills' non-runtime artifacts.** Worked-example
  `.md` files (`skills/contracts/worked-example-*.md`,
  `skills/analyze/worked-example-jig.md`) are docs and belong in the
  install. Only `fixtures/` is in scope. If a sibling skill later
  grows a `test_fixtures/` dir, same exclusion rule applies — but no
  preemptive change.

## Current state (verified 2026-05-26)

| Surface | Code location | Excludes today | `fixtures/`? |
|---|---|---|---|
| Scaffold copy | `_copy_skill_dir` at `skills/scaffold-init/scaffold.py:549` | `__pycache__`, `test_*.py` | ❌ |
| Release zip | `_EXCLUDE_DIR_NAMES` at `scripts/build_release_zip.py:57` | `__pycache__`, `.pytest_cache`, `.mypy_cache` (+ `.pyc`, `.DS_Store`, `test_*.py` as file patterns) | ❌ |

Confirmed:

```
$ ls skills/migrate/fixtures/
conflict greenfield partial tiny-validator
```

## Decomposition

**Suggested SPIDR axis: I (Interface)** — two install surfaces, each its
own "interface" the fix has to land on. Lean **single-slice (Option A)**
unless `/jig:clarify` surfaces a reason to split.

### Slices (TBD until clarify runs)

- **Option A (preferred)** — one slice: `035-01
  exclude-fixtures-from-installs`. Add `fixtures` to both deny lists;
  add a regression test on each surface. Single commit, single review
  pass.
- **Option B** — split by interface: `035-01 exclude-from-scaffold-copy`,
  `035-02 exclude-from-release-zip`. Two slices, two reviews. Only
  worth the overhead if reviewers prefer separation.

## Open questions for `/jig:clarify`

- **Q1.** Should the exclusion apply to *any* dir named `fixtures`
  anywhere in the skill subtree, or only at the skill root? Lean:
  anywhere — matches existing `__pycache__` semantics.
- **Q2.** Single slice (Option A) or split by interface (Option B)?
  Lean A. Brief explicitly defers this to clarify.
- **Q3.** DoR signal — confirm no skill currently *needs* a `fixtures/`
  dir at install time. As of 2026-05-23 audit: only `migrate` uses the
  name, and only for tests. Worth re-confirming when this slice picks
  up.

## Dependencies / coordination

- **None.** Can run in parallel with anything else.
- No conflict with spec 036 (drift policy) — different files.
- Would benefit from a shared `_common/install_excludes.py` if 038
  (tier reconciliation) introduces one for tier-related copy logic,
  but not required and not blocking.

## References

- External review brief: [`brief-02-fixture-exclusion.md`](../../external-review/brief-02-fixture-exclusion.md)
- Verification 2026-05-26: both deny lists still lack `fixtures`.

## Clarifications

### Q1: Should the exclusion match any dir named `fixtures/` anywhere in the skill subtree, or only at the skill root level?
_(category: Edge Cases & Failure Modes)_

Anywhere in subtree. Matches existing `__pycache__` semantics — any directory named `fixtures/` at any depth under a skill dir is skipped. Future-proof if a skill grows nested test trees.

### Q2: Single slice (Option A) or split by interface (Option B: one slice per copy surface)?
_(category: Scope & Boundaries)_

Option A: single slice. One slice `035-01 exclude-fixtures-from-installs`. Add `fixtures` to both deny lists + regression test on each surface. Single commit, single review.

### Q3: Backwards-compat: existing installs already have a stale `fixtures/` tree from prior scaffold-init runs. What should this slice do about them?
_(category: Non-functional Requirements)_

Fix forward only. New scaffolds + new zip installs are clean. Existing stale `fixtures/` dirs persist until the user re-runs scaffold or reinstalls. Simplest — no cleanup logic needed.

### Q4: What if a future skill legitimately needs a `fixtures/` directory at install time (e.g., as runtime sample data, not test data)?
_(category: Edge Cases & Failure Modes)_

Cross that bridge later. Treat `fixtures/` as a reserved name meaning "test data, never runtime". If a future skill needs runtime sample data, use a different dir name (`samples/`, `examples/`, `data/`). No escape hatch in this slice.

### Q5: DoR signal (spec's open Q3): should slice 035-01 require an explicit re-verification at pickup that no skill currently needs `fixtures/` at install time, or is the 2026-05-23 audit sufficient?
_(category: Dependencies & Blockers)_

Re-verify at pickup. DoR includes a 1-command re-check: `find skills -type d -name fixtures` must show only `skills/migrate/fixtures/`. Cheap insurance against drift between audit and pickup.

### Coverage summary

| Category | Status |
|---|---|
| Scope & Boundaries | Resolved |
| Acceptance Criteria Testability | Clear |
| Dependencies & Blockers | Resolved |
| Non-functional Requirements | Resolved |
| Edge Cases & Failure Modes | Resolved |
| Terminology Consistency | Clear |
