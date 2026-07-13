---
status: DONE
tier: standard
severity: medium
claimed_by: codex/issue-86-status-rollup
regression_test: skills/spec-workflow/test_workflow.py::TransitionTests::test_slice_path_transition_is_not_overwritten_by_spec_rollup
main_repro_checked_at: 2026-07-12
main_repro_ref: origin/main@0c57970111d4c5ba94c0f35ba7bb2c0feeadb0f2
main_repro_result: reproduces
red_confirmed_at: 2026-07-12
green_confirmed_at: 2026-07-12
fix_class: structural_fix
security_surface: false
escalated_to:
---

# Bug 006: slice-path-status-rollup

## Symptom

When `workflow.py transition` receives a file-per-slice `slice-*.md` path as
its first positional argument, transitions to `REVIEWED`, `RECONCILED`, and
`DONE` print success and exit 0, but the slice's frontmatter `status:` remains
`IN_PROGRESS`. A `RECONCILED` transition still stamps `last_verified`, and the
status board subsequently reports the stale state. Reported in GitHub issue
[#86](https://github.com/ramboz/jig/issues/86).

## Repro

Create a file-per-slice spec with two slices: target `002-01` at
`IN_PROGRESS`, and sibling `002-02` at `DRAFT`. Invoke the transition helper
with the target slice file, rather than the overview:

```text
workflow.py transition docs/specs/002-song-library/slice-01-add-and-view.md 002-01 REVIEWED
workflow.py transition docs/specs/002-song-library/slice-01-add-and-view.md 002-01 RECONCILED
workflow.py transition docs/specs/002-song-library/slice-01-add-and-view.md 002-01 DONE
```

Each command exits 0 and reports `IN_PROGRESS → <target>`, while
`grep '^status:' slice-01-add-and-view.md` remains `status: IN_PROGRESS`.
Using `docs/specs/002-song-library/spec.md` as the first argument advances all
three states correctly.

## Evidence

- Minimal reproduction against current `main` (`0c57970`) produced the exact
  three silent no-ops above; `last_verified: 2026-07-12` survived the
  `RECONCILED` attempt.
- `transition()` writes the requested status to `loc.path`, then calls
  `_write_spec_rollup(spec_md)` (`skills/spec-workflow/workflow.py:1304-1406`).
- `load_slice()` accepts a slice path because it searches
  `spec_path.parent` for matching `slice-*.md` siblings
  (`skills/_common/parsing.py:233-263`).
- The relevant transition/write code is unchanged between tag `v2.2.0` and
  current `main`; all generated host copies match the canonical source.

## Hypotheses

<!-- Anti-anchoring: >=2 candidates, mark the leading one. Any Markdown
     list works (-, *, +, or 1.); the gate counts top-level items only
     (indented sub-bullets are notes, not hypotheses). -->
- [ ] H1: the file-per-slice frontmatter writer is missing or silently
  failing. Falsified because the same writer persists `last_verified`, the
  focused frontmatter unit tests pass, and using `spec.md` persists every
  requested status.
- [ ] H2: the 2.2.0 generated package drifted from canonical source. Falsified
  by comparing the tagged implementation with current source and the generated
  host copies; the relevant write sequence is identical.
- [x] H3 (leading): the slice status is written correctly and then overwritten
  by the spec-rollup step because the caller-supplied slice path is reused as
  `spec_md`. Confirmed by the minimal reproduction: using the slice path
  reproduces, while changing only the first argument to sibling `spec.md`
  persists `REVIEWED → RECONCILED → DONE`.

## Root cause

The transition CLI documents its first argument as `path to spec.md`, but the
shared slice loader permissively accepts a `slice-*.md` path. `transition()`
therefore resolves and writes the intended slice successfully. It then passes
the original caller argument to `_write_spec_rollup()`. When that argument is
the slice file, the rollup treats the slice as the overview, computes the
spec-level state from the directory's slices, and overwrites the same slice's
frontmatter `status:`. With another unfinished sibling, that computed rollup is
`IN_PROGRESS`; `last_verified` is not a rollup field and remains visible.

This is an input-normalization defect at the transition boundary, not a failed
frontmatter write. The structural repair is to canonicalize a supplied sibling
slice path to its overview `spec.md` before any transition concern consumes the
path.

## Fix class

`structural_fix` — canonicalize the transition's overview path once at the
boundary so every downstream concern receives the same path identity.

## Fix

- Added `_canonical_transition_spec_path()` at the `transition()` boundary.
  A `slice-*.md` input now resolves to its sibling `spec.md`; a malformed
  slice layout without the supplied slice file or its overview fails before
  mutation.
- All existing transition concerns therefore receive the canonical overview
  path, including evidence gates, dependency checks, project-root lookup,
  spec-rollup, and usage attribution.
- Clarified CLI help to accept `spec.md` or a sibling `slice-*.md` file.
- Regenerated the Claude and Codex host packages from canonical source.

## Already tried

- A focused `tdd.py` invocation under `skills/spec-workflow/` could not start
  because pytest is not installed (exit 2). The repo-root canonical
  `.jig/test-command` uses unittest plus pyright and witnessed both red and
  green instead.
- The first full canonical run passed all tests but the sandbox blocked uvx's
  pyright cache. Re-running with approved cache access produced a clean
  pyright result.
- The first bug-review and craft-review passes found that normalization checked
  the overview before checking the caller-supplied slice file. A mistyped
  `slice-*.md` path could therefore resolve by fragment and mutate a real
  sibling. A second red→green regression now pins fail-before-mutation.

## Regression test

`skills/spec-workflow/test_workflow.py::TransitionTests::test_slice_path_transition_is_not_overwritten_by_spec_rollup`
uses the reported slice-file argument with an unfinished sibling and asserts
the persisted target state after each transition, the overview rollup, the
surviving `last_verified` stamp, and the untouched sibling.

`TransitionTests::test_missing_slice_path_is_rejected_before_fragment_lookup`
asserts a mistyped slice path fails without mutating a real sibling selected by
the supplied fragment.

## Proof

- Bug gate witnessed the regression test red on 2026-07-12 before the fix.
- Focused regression: 1 test green.
- Transition suite after review correction: 10 tests green.
- Transition/frontmatter neighborhood before review: 15 tests green.
- Final canonical suite after the reviewer correction: 3,452 tests green,
  6 skipped; pyright clean.
- `scripts/build_host_packages.py` regenerated both committed host payloads.

## Learning

When a command accepts a canonical overview path but a permissive child lookup
also makes a child-file path appear valid, normalize the path once at the
command boundary before any downstream writes. Preserve validation of the
original caller-supplied path before normalization: otherwise a typo can be
silently reinterpreted and mutate a different artifact selected by a secondary
fragment argument. Regression coverage needs both the successful alias and the
fail-before-mutation typo case.

## Main recheck

- 2026-07-12 - `origin/main@0c57970111d4c5ba94c0f35ba7bb2c0feeadb0f2` -> reproduces: Minimal two-slice transition repro using slice-01 path: REVIEWED, RECONCILED, and DONE each exit 0 while status remains IN_PROGRESS; relevant workflow/parsing code is byte-identical to fetched origin/main.
