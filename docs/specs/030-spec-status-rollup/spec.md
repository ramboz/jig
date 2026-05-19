---
status: DONE
skill: spec-workflow
tier: (none — dev infrastructure)
---

# Spec 030: spec.md status rollup

## Overview

Every `docs/specs/NNN-<slug>/spec.md` carries a frontmatter `status:`
field. The field was introduced in slice 015-01 (structured-lifecycle-
metadata), when a spec.md typically *contained* its slices and the
field doubled as the slice's status. Slice 018-03 moved slices into
sibling `slice-NN-*.md` files; spec.md became an overview/index. The
field stayed in the template (`_render_stub_spec` writes
`status: DRAFT` on `workflow.py new`) but **no helper ever updates
it** — `transition` only touches slice files / embedded sections, and
`status-board` reads slice statuses but doesn't write back to spec.md.

The result, as of 2026-05-18: all 28 spec.md files show
`status: DRAFT` regardless of actual state. Specs whose every
non-DEFERRED slice is DONE (001 — 025) read identically to specs
just reserved this week (026 — 029). Anyone reading a spec.md
without cross-referencing `docs/specs/README.md` sees the wrong
signal.

This spec wires the rollup. `workflow.py` gains a
`compute_spec_status(spec_path)` function that derives the spec-level
status from its slices; both `transition` (after the slice mutation)
and `status-board` (during regen) call it and write the result back
to spec.md's frontmatter. A backfill sweep against the current jig
repo flips the 25-ish completed specs to DONE in one pass.

## Why now

- **Visibly wrong signal.** 28/28 spec.md files report DRAFT. The
  user noticed mid-session ("most of those should be probably DONE")
  — the field has stopped being trustworthy.
- **The fix sits inside the existing helper.** `workflow.py` already
  walks slices in `collect_slices` / `iter_slices`; deriving the
  rollup is one pass over the same data. No new artifact, no new
  state machine — extend an existing call path.
- **Two write triggers are already in place.** `transition` already
  writes to spec files; `status-board` already regenerates a sibling
  artifact. Both are natural homes for the rollup write.
- **User picked the rollup option** (over field-removal) on
  2026-05-18 after the gap was diagnosed.

## Goals

1. **`compute_spec_status(spec_path)` exists** in
   `skills/spec-workflow/workflow.py` as a pure function returning one
   of `DRAFT | IN_PROGRESS | DONE`. Reuses `iter_slices` from
   `_common/parsing.py`; reads slice status from frontmatter or
   `**STATUS:**` prose (dual-layout per slice 018-02).

2. **`workflow.py transition`** computes and writes the rollup to
   spec.md's frontmatter `status:` field **after** the slice mutation
   succeeds. Idempotent — no write when the value would be unchanged.

3. **`workflow.py status-board`** computes and writes the rollup for
   every spec it walks, as a side-effect of regenerating the board.
   Same idempotence rule. This is the path that backfills existing
   stale spec.md files.

4. **Rollup rule (three states):**
   - **`DRAFT`** — no slices yet, OR every non-DEFERRED slice is
     DRAFT, OR every slice is DEFERRED (no live work).
   - **`DONE`** — at least one non-DEFERRED slice exists AND every
     non-DEFERRED slice has status `DONE`.
   - **`IN_PROGRESS`** — everything else (any slice in
     `READY_FOR_REVIEW` / `READY_FOR_IMPLEMENTATION` / `IN_PROGRESS` /
     `REVIEWED` / `RECONCILED`, OR a mix of DONE and DRAFT slices).

5. **Backfill.** Running `workflow.py status-board <jig-root>` after
   this slice lands flips every spec whose non-DEFERRED slices are
   all DONE today to `status: DONE`. The deviation log records the
   before/after counts.

6. **Spec.md without frontmatter** (defensive — none exist today,
   but legacy specs *could* drop the block) is left untouched. No
   frontmatter insertion. Lazy-migration consistent with slice
   015-01's policy.

## Non-goals

- **No new lifecycle states for specs.** The rollup uses the
  existing `VALID_STATUSES`. We don't add `SPEC_DONE` or similar.
- **No status-board column for spec-level status.** The board is a
  per-slice table; spec-level rollup lives in spec.md frontmatter
  only.
- **No `transition` command for spec-level status.** Spec status is
  *derived*, never set explicitly. There's no
  `workflow.py transition <spec.md> spec DONE` — that would
  re-create the drift problem.
- **No CLAUDE.md hygiene changes.** Spec 025 owns the close-out
  compression rule. This spec only touches the frontmatter field.
- **No retroactive slice rewrites.** Slice statuses are correct as
  they stand; backfill only updates spec.md, never slice files.
- **No ADR.** The rollup rule is a localized convention, not a
  hard-to-reverse decision. If the rule turns out wrong, edit it.

## Decomposition

One slice; rollup function + both write paths + backfill in a
single vertical. SPIDR-split:

| Technique | Question | Outline |
|---|---|---|
| **S** — Spike | Spike on "what if a spec has zero slices in iter_slices but exists?" Or "what shape should the rule take?" | **No spike needed.** Both questions resolve by reading: (a) `iter_slices` returns `[]` deterministically for a spec dir with no slice files and no embedded sections (rule: → DRAFT); (b) the three-state rule above is judgment, not research. |
| **P** — Path | Wire `transition` first and `status-board` second? Or both at once? | **Both in one slice.** They share `compute_spec_status` and the frontmatter writer; splitting horizontally ships dead code for a release. The backfill is also coupled — it IS the dogfood for `status-board`'s write path. |
| **I** — Interface | Where does the rollup live — in `workflow.py` or `_common/parsing.py`? | **`workflow.py`.** It's lifecycle-aware (knows VALID_STATUSES, the DEFERRED rule). `_common/parsing.py` is layout-only (where the slice text lives). Keeping the policy in `workflow.py` matches the existing split. |
| **D** — Data | What's the input shape? What's the write shape? | Input: `iter_slices(spec_path)` → list of `SliceLocation`s; status read via the existing `_slice_frontmatter` + `**STATUS:**` regex pattern already used in `collect_slices`. Write: `set_frontmatter_field(spec_text, "status", new_value)` — the same helper used for slice frontmatter writes. |
| **R** — Rules | What governs the three-state mapping? | Per Goal #4. The trickiest edge — a spec with one DONE slice and one DRAFT slice — maps to IN_PROGRESS (work has begun), not DONE. The trickiest other edge — every slice DEFERRED — maps to DRAFT (no live work), not DONE. |

### Slices

- [030-01 — rollup-on-transition-and-regen](slice-01-rollup-on-transition-and-regen.md) — DRAFT

## Out of scope for spec 030 (any slice)

- **`workflow.py audit-spec-status` standalone command.** The
  rollup is implicit (writes during transition + regen); a separate
  audit command isn't justified until / unless the implicit writes
  prove insufficient.
- **Status-board "Spec" column showing rollup.** The board is
  slice-shaped. The user reads spec.md frontmatter when they want
  the rollup; the board when they want per-slice detail.
- **Frontmatter `last_verified` for spec.md.** The field is
  slice-shaped (one per slice, set on `RECONCILED`). Adding it at
  spec level would invent a new ceremony.
- **`tier:` or `skill:` field maintenance.** Those are author-set
  on spec creation; this spec doesn't touch them.

## References

- **Originating conversation:** 2026-05-18 — user asked "specs are
  mostly DRAFT but they should be DONE; are we missing a step?"
  Diagnosis surfaced the stranded-field gap; user picked option
  #2 (auto-rollup) over option #1 (drop the field).
- **Slice 015-01 — frontmatter-parsing-and-templates:** introduced
  the spec.md frontmatter `status:` field. Spec 030 wires the
  update path that 015-01 left implicit.
- **Slice 018-03 — scaffold-new-specs-as-file-per-slice:**
  established the file-per-slice layout that made spec.md an
  overview file rather than a slice carrier. The rollup gap is a
  direct downstream of this layout shift.
- **`iter_slices`** (`skills/_common/parsing.py:174`) — the
  authoritative walker over both layouts. Reused here.
- **`collect_slices`** (`skills/spec-workflow/workflow.py:383`) —
  already reads slice status across both layouts; the rollup
  function reuses the same status-read pattern.
