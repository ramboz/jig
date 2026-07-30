---
status: DONE
tier: standard
severity: medium
claimed_by: claude/github-issue-134-0c6fb4
regression_test: skills/independent-review/test_review.py::FilePerSliceReviewTargetTests
main_repro_checked_at: 2026-07-30
main_repro_ref: origin/main@00c3333
main_repro_result: reproduces
red_confirmed_at: 2026-07-30
green_confirmed_at: 2026-07-30
fix_class: structural_fix
security_surface: false
escalated_to:
---

# Bug 019: review-prompt-hardcodes-spec-md

## Symptom

Reported as [issue #134](https://github.com/ramboz/jig/issues/134).

`review.py`'s reviewer prompts send the read-only reviewer to `spec.md` for the
slice's content. In a **file-per-slice** project the slice does not live in
`spec.md` — it lives in a sibling `slice-NN-<short>.md` — so the reviewer is
pointed at a file that contains none of the artifacts it is being asked to
verify.

Worst on `reconciliation`, which names two subsections by title:

> 1. `docs/specs/008-visual-reframe/spec.md` — focus on the Slice 008-17 section,
>    especially the "Deviation log (after reconciliation)" and "Reconciliation
>    sweep" subsections.

The reviewer is explicitly instructed *not* to assume context beyond the files
it is pointed at, so the mistake is not self-correcting. An interactive driver
notices and rewrites the path by hand; an unattended run returns a verdict
grounded in nothing.

All seven spec+slice prompt builders share the defect: `implementation`,
`pr-review`, `arch-review`, `code-health`, `frame-critique`, `design-review`,
`reconciliation`. (`bug-review` is unaffected — it takes a bug record, not a
spec.)

## Repro

```bash
python3 skills/independent-review/review.py reconciliation \
  docs/specs/087-narrow-first-review/spec.md 087-01
```

Observed: the prompt's "What to read" points at
`docs/specs/087-narrow-first-review/spec.md`.

Expected: it points at
`docs/specs/087-narrow-first-review/slice-01-investigation-guidance.md`, which
is where the deviation log and reconciliation sweep actually are.

## Evidence

- `grep -c "Deviation log\|Reconciliation sweep"` → `spec.md: 0`,
  `slice-01-investigation-guidance.md: 4`. The prompt names the file with none
  of them.
- The slice **label** resolves correctly in both layouts (spec 018-02's
  `MixedLayoutResolutionTests` cover it), so the dual-layout loader itself is
  sound — only the emitted path is wrong.
- `find_slice_label` (review.py:75) calls `_common.parsing.load_slice`, which
  returns a `SliceLocation` carrying the resolved `path`, then returns
  `loc.label` and drops `loc.path` on the floor.
- Every builder's f-string interpolates `{spec_path}` at the point where it
  means "the file holding this slice".

## Hypotheses

- [ ] H1: the dual-layout loader fails to resolve slices in file-per-slice
      layout, so `review.py` falls back to `spec.md`. **Falsify by** running
      the repro against a file-per-slice spec and checking whether the slice
      *label* resolves — if the label is right, the loader worked and the
      fallback theory is dead.
- [x] H2 (leading): the loader is consulted for the **label only**; the
      resolved slice-file path is discarded, and the prompt templates
      interpolate `spec_path` wherever they mean "the file containing the
      slice". **Confirm by** reading `find_slice_label`'s return statement and
      the `## What to read` blocks of the seven builders.

H1 is falsified: the repro prints the correct label
(`087-01 — investigation guidance in code-review prompts + reviewer agent`)
while pointing at the wrong file. H2 confirmed by inspection.

## Root cause

`find_slice_label()` resolves the slice through the shared dual-layout loader
and then throws away the half of the answer that matters. `SliceLocation` knows
*which file* the slice was found in; `review.py` keeps only `.label`.

With the path gone, each prompt builder has nothing left to name but
`spec_path`, so the templates hardcode it. In the embedded layout the two
coincide and the prompt is accidentally correct; in the file-per-slice layout —
the layout `workflow.py new` actually emits — they diverge and the prompt is
silently wrong.

So this is a **process** defect, not an output one: the layout knowledge was
computed and then dropped at the boundary, and nothing downstream could
recover it.

## Fix class

`structural_fix`. The half-answer is restored at its source rather than patched
at each of the seven call sites: the resolver now returns *where* the slice
lives alongside *what* it is called, and the builders name that file. A
per-prompt string edit would have been a `local_patch` that the eighth builder
reintroduces.

## Fix

1. `find_slice_target(spec_path, fragment) -> (label, path)` keeps the
   `SliceLocation.path` the shared loader already resolved.
   `find_slice_label()` stays as a thin wrapper over it, so existing callers
   are untouched.
2. `_slice_source(spec_path, slice_path) -> (noun, phrase)` renders the
   reading target once: `The spec` / `` `spec.md` `` in the embedded layout,
   `The slice` / `` `slice-NN-x.md` (spec overview: `spec.md`) `` in
   file-per-slice. One renderer, so the two layouts cannot drift apart per
   builder.
3. All seven spec+slice builders take `slice_path=` and interpolate the
   rendered phrase in their `## What to read` list. The default (`None` →
   `spec_path`) preserves the embedded layout and the ADR `frame-critique`
   target, which genuinely has no slice file.
4. `main()` resolves label and path together and hands both down.

Post-review adjustments (craft pass, all nits — no blockers from either pass):

- The reconciliation entry now reads `The slice — <path>. Focus on the Slice X
  section there…`. Without the noun prefix, "the Slice X section" could bind to
  the nearer `spec.md` in the trailing overview reference — an ambiguity in the
  one prompt this bug was reported against.
- The five identical per-builder docstring notes collapsed to a pointer at
  `_slice_source`; only the frame-critique and reconciliation variants say
  anything the renderer's own docstring doesn't.
- `-> tuple` widened to `tuple[str, Path]` / `tuple[str, str]` — the dropped
  second element *was* the bug, so the signature should name it.
- `frame-critique` takes `_slice_source(...)[1]` rather than binding an unused
  noun; it supplies its own ("The artifact under critique").
- Mixed-layout test added (see Regression test).
- `skills/independent-review/SKILL.md`: the "keep passing `spec.md`" note was
  hoisted out of the reconciliation recipe to cover all seven, since the
  contract is not reconciliation-specific.

Not changed: `find_slice_label` is retained — `record_review` still needs the
label alone. `hosts/claude/` and `hosts/codex/` are regenerated build output,
not hand edits; `test_review.py` is not mirrored (host packages ship no tests).

## Already tried

## Regression test

`skills/independent-review/test_review.py::FilePerSliceReviewTargetTests` —
builds a real file-per-slice spec dir (overview-only `spec.md` +
`slice-01-alpha.md` holding the ACs, deviation log, and sweep) and asserts,
for all seven modes, that the `## What to read` list names the slice file and
names it *before* the overview. Two extra tests pin the semantics that made
this worth fixing: the "Deviation log / Reconciliation sweep" instruction and
the "Focus on Slice X only" instruction must each hang off the slice file.

`EmbeddedLayoutReviewTargetTests` is the overcorrection guard, in two shapes.
The pure embedded dir pins that nothing invents a `slice-` path. The MIXED dir
is the one that can actually go wrong: a sibling slice file exists but the
requested fragment lives in `spec.md`, so a fix that reasoned "this spec dir
has slice files → point at one" would send the reviewer to a DIFFERENT slice's
file — worse than the original bug. Added after the craft pass observed the
first shape was satisfied by construction.

## Proof

Not gated at this tier (`## Proof` attestation is a `→ VERIFIED` requirement,
gnarly/security only). Recorded anyway, since the original repro is cheap:

- **Original repro, re-run on the fix.** `review.py reconciliation
  docs/specs/087-narrow-first-review/spec.md 087-01` now emits
  `1. The slice — .../slice-01-investigation-guidance.md (spec overview:
  .../spec.md). Focus on the Slice 087-01 … section there, especially its
  "Deviation log (after reconciliation)" and "Reconciliation sweep"
  subsections.` — the file that actually holds all four occurrences.
- **Red → green witnessed by the gate**, not claimed: `red_confirmed_at:
  2026-07-30` stamped by `→ FIXING` (test failed without the fix),
  `green_confirmed_at: 2026-07-30` stamped by `→ REVIEWED`.
- **ADR path unaffected.** `review.py frame-critique
  docs/decisions/adr-0037-*.md` still names the ADR itself — no slice file, no
  phantom overview reference.
- **Full suite green**: 3695 tests, `OK (skipped=4)`, exit 0. Host-package
  drift guard: `OK: committed host packages are in sync with source`. Pinned
  ruff 0.15.16 clean across the repo.

## Learning

**A resolver that returns half its answer makes every caller guess the rest.**
`load_slice` knew both what the slice is called and which file holds it;
`find_slice_label` kept the name and dropped the location, so seven prompt
builders re-invented the missing half as `spec_path`. Return the whole answer,
or the abstraction is a lie by omission.

Two corollaries:

- **A defect a human driver silently corrects is a defect only unattended runs
  pay for.** Interactively you notice the path is wrong and retype it; nothing
  gets filed. Wherever a human routinely patches output by hand, put a test —
  the loop is hiding the bug, not fixing it.
- **Asserting the right thing was FOUND is not asserting the right thing was
  REPORTED.** `MixedLayoutResolutionTests` proved the *label* resolved in both
  layouts and read as coverage of dual-layout support. It never looked at the
  path the prompt emitted.

And on the fix itself: when two layouts coexist, render the difference in
exactly one place. Seven independently-worded `## What to read` entries were
seven chances to get it wrong; `_slice_source` makes the eighth builder correct
by default.

Full entry: [docs/memory/learnings.md](../memory/learnings.md) § Bug 019.

## Main recheck

- 2026-07-30 - `origin/main@00c3333` -> reproduces: review.py reconciliation docs/specs/087-narrow-first-review/spec.md 087-01, run from a detached worktree at origin/main@00c3333: the 'What to read' block still names spec.md, while the deviation log and reconciliation sweep live in slice-01-investigation-guidance.md (grep count: spec.md=0, slice file=4).
