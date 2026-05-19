---
status: DONE
dependencies: [031-01]
last_verified: 2026-05-19
arch_review: true
---

## Slice 031-02 — arch-review-trigger

**Goal:** Add an on-demand `arch-review` pass to the post-implementation
workflow, gated by a new `arch_review:` boolean field in slice
frontmatter. When the field is `true` on a slice, the orchestrator runs
an architecture-review pass after the compliance + craft passes.
Reuses slice 031-01's three-pass plumbing. End-to-end value in a single
slice: slices that touch module boundaries or public contracts get an
arch-review pass automatically without the user remembering to invoke
it.

**DoR:**

- ✅ Slice 031-01 has landed: `review.py pr-review` mode exists and
  `skills/spec-workflow/SKILL.md` documents the three-pass flow.
- ✅ `jig:arch-review` skill exists with the description-based
  deferral pattern (slice 014-01).
- ✅ Slice frontmatter parsing is established (slice 015-01) — adding
  a new boolean field follows the same shape.

**Acceptance Criteria:**

1. **Slice frontmatter `arch_review:` field** — new optional boolean,
   defaulting to `false`. Slice authors set `arch_review: true` when
   the slice changes module boundaries, public contracts, or
   architecture-shaped concerns. `templates/docs/specs/slice-template.md`
   ships the field commented out with a one-line guide:
   ```yaml
   ---
   status: DRAFT
   dependencies: []
   last_verified:
   # arch_review: true  # set to true when this slice changes module
   #                    # boundaries, public contracts, or architecture-
   #                    # shaped concerns (triggers arch-review pass).
   ---
   ```
   Existing slices without the field are unaffected (default `false`).

2. **`review.py arch-review`** — new subcommand mirroring `pr-review`:
   ```bash
   review.py arch-review <spec.md> <slice-fragment> <deliverable-path-1> [...]
   ```
   Builds a prompt that:
   - Cites the deliverable paths.
   - Instructs the reviewer to apply the arch concerns from the
     most-specific `arch-review` SKILL.md reachable (user > project >
     `jig:arch-review`).
   - Output buckets per `jig:arch-review`'s canonical shape:
     summary / strengths / concerns / open questions.
   - Same verdict-envelope wrapping as `pr-review`.

3. **`review.py subagent-type arch-review`** — same precedence pattern
   as `pr-review`'s subagent-type subcommand.

4. **`workflow.py` exposes the frontmatter flag.** Add a helper
   (e.g., `slice_needs_arch_review(spec_md, slice_fragment) -> bool`)
   that parses the slice's frontmatter and returns the
   `arch_review:` value, defaulting to `false` when the field is
   absent. SKILL.md instructs the orchestrator to call this before
   deciding whether to spawn the arch-review pass.

5. **`skills/spec-workflow/SKILL.md` § "After implementation"** is
   updated to include the conditional third pass:
   1. Compliance pass via `jig:independent-review` (always).
   2. Craft pass via `pr-review` (always).
   3. Arch pass via `arch-review` (only when slice frontmatter has
      `arch_review: true`).
   Block rule extends: arch pass `fail` blocks the REVIEWED
   transition; `needs-changes` becomes a reconciliation-log entry.

6. **Tests added.**
   - `skills/independent-review/test_review.py`: 4+ surface tests
     mirroring slice 031-01's pr-review test set (prompt shape, no
     AC re-evaluation, output bucket names, verdict envelope).
   - `skills/spec-workflow/test_workflow.py`: 3+ tests on the new
     `slice_needs_arch_review` helper — defaults to false, reads
     true when frontmatter sets it, returns false when frontmatter
     is missing entirely.
   - At least 1 SKILL.md surface test asserting the conditional
     third-pass instruction is documented.
   - `templates/docs/specs/slice-template.md` surface test asserting
     the `arch_review:` commented hint is present.

7. **Dogfood.** This slice itself sets `arch_review: true` in its own
   frontmatter — the spec ships a workflow-shape change (the
   three-pass extension affects how every slice is reviewed going
   forward), which is architecturally interesting. The deviation log
   captures the verdict from the arch-review pass on this slice.

**DoD:**

- [x] All ACs pass; full test suite green (no regressions).
- [x] Implementer test coverage exercises each AC. The
      `slice_needs_arch_review` helper and the
      `arch_review:`-missing-default-false case are covered explicitly.
- [x] Reviewed by `reviewer` subagent (compliance pass).
- [x] Reviewed by `pr-review` skill (craft pass via 031-01).
- [x] Reviewed by `arch-review` skill via the new `review.py arch-review`
      pass (THIS slice's dogfood — first arch-review pass in the
      workflow).
- [x] Implementation review passed.
- [x] Deviation log produced under this slice heading.
- [x] Reconciliation review passed.
- [x] `docs/refinement-todo.md` updated if any decisions were
      deferred during implementation. (No deferrals; the spec's open
      questions were resolved inline — see deviation log.)

### Close-out (post-DONE)

These items can only be ticked AFTER the final `RECONCILED → DONE`
transition. Slice-land's `check_dod` (slice 009-01) excludes them
from the count.

- [x] `docs/specs/README.md` regenerated by `workflow.py status-board`.
      Notes column for 031-02 carries the load-bearing invariant
      (`arch_review:` field shape + conditional trigger + arch-pass
      block rule).
- [x] `CLAUDE.md` hygiene per spec 025-01 rule: spec 031 doesn't
      introduce a new skill. Active-specs entry compressed on close-out
      if any was added (lean: none).
- [x] `skills/independent-review/SKILL.md` and
      `skills/spec-workflow/SKILL.md` reference the
      `arch_review:` field shape so future agents authoring slices
      know to set it when relevant.

**Anti-horizontal-phasing check:** After this slice lands, slices
that declare `arch_review: true` get an automatic arch-review pass —
the first time jig's workflow has touched architecture review at all.
For users with a richer installed `arch-review` skill, the pass
routes there; for jig-only users, `jig:arch-review`'s baseline fires.
End-to-end signal: the user-observable verdict shows up at the same
point as the compliance + craft passes.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

**Implementation summary.** Added `review.py arch-review` subcommand
mirroring `pr-review` (spec + slice + deliverables → prompt) with a
new `build_arch_review_prompt()` that swaps the bucket names to match
`jig:arch-review`'s canonical shape (summary / strengths / concerns /
open questions) while reusing slice 031-01's `_PR_REVIEW_OUTPUT_FORMAT`
(same `[blocker]`/`[nit]`/`[strength]` tagging + verdict envelope) so
workflow consumption stays uniform across all three passes. Added
`arch-review` choice to `subagent-type`. Added `slice_needs_arch_review`
helper + `arch-review-needed` CLI subcommand to `workflow.py`. Added
the `arch_review:` commented hint to the slice template's frontmatter
block. Reshaped `skills/spec-workflow/SKILL.md` § "After implementation"
to document the conditional third pass + the extended block rule; added
the matching recipe section to `skills/independent-review/SKILL.md`.

**+27 tests; 1083 → 1110 green.** This slice adds 12
`ArchReviewPromptTests` + 3 `ArchReviewSubagentTypeTests` + 2
extensions to `SpecWorkflowSkillThreePassTests` (conditional arch pass
documented + arch-after-craft ordering) + 7 `SliceNeedsArchReviewTests`
(including the embedded-with-frontmatter case added during reconciliation)
+ 3 `SliceTemplateArchReviewHintTests`. Tests exceed AC #6 minimums
(4+ surface tests on arch-review mode, 3+ helper tests, 1+ SKILL.md
surface test, 1+ slice-template surface test).

**Dogfood verdict (AC #7).** This slice declared `arch_review: true`
on its own frontmatter and ran all three passes against itself.
- **Compliance pass** (`jig:independent-review`): VERDICT pass.
  Surfaced two nits: (1) the bash recipe captured the helper's stdout
  without checking exit code (a slice-lookup failure would silently
  skip the arch pass); (2) `slice_needs_arch_review` bypassed the
  layout-aware `_slice_frontmatter` helper, so legacy embedded slices
  with post-heading frontmatter couldn't opt in. Both addressed
  inline before reconciliation — see below.
- **Craft pass** (`pr-review` dogfood): VERDICT pass. Echoed the same
  consistency nit on `_slice_frontmatter`; added a docstring
  contract nit on `_ARCH_REVIEW_TRUTHY` accepting tokens beyond `true`
  (addressed: the constant now documents the YAML-permissive set
  explicitly). Three `[strength]` callouts: the documented absence
  of `_principles_check_block()`, the policy/mechanism separation
  on `_ARCH_REVIEW_TRUTHY`, and the cross-skill prose tests catching
  drift between SKILL.md files.
- **Arch pass** (`arch-review` dogfood, first ever in the workflow):
  VERDICT pass. Confirmed module boundaries preserved (frontmatter
  parsing lives in `workflow.py`, prompt building lives in
  `review.py`, orchestrator dispatches via SKILL.md prose). Echoed
  the same two actionable nits (bash recipe exit-code check,
  `_slice_frontmatter` consistency). Captured the
  `_principles_check_block()` omission as architecturally subtle but
  defensible.

**Fixes applied inline before reconciliation.**
1. `slice_needs_arch_review` now calls `_slice_frontmatter` (instead
   of raw `parse_frontmatter`), making it layout-aware. Adds the
   legacy-embedded-with-frontmatter case to the supported shapes; a
   new test (`test_returns_true_for_embedded_slice_with_post_heading_frontmatter`)
   locks the new behavior.
2. Both SKILL.md bash recipes now wrap the `arch-review-needed`
   invocation in `if ! NEED_ARCH=$(...); then echo ... >&2; exit 2; fi`
   so a slice-lookup failure surfaces as an abort rather than silently
   degrading to "no arch pass."
3. `_ARCH_REVIEW_TRUTHY`'s comment and the docstring on
   `slice_needs_arch_review` now explicitly name the four accepted
   tokens (`true | yes | on | 1`) so the YAML-permissive expansion is
   contract-visible.

**Constitution-gate decision (load-bearing).** Like
`build_pr_review_prompt`, `build_arch_review_prompt` deliberately does
NOT append `_principles_check_block()`. The docstring NOTE on
`build_arch_review_prompt` calls this out: constitution-adherence is
the compliance + reconciliation pass's job, and re-running the seven
principles check on every pass would duplicate work and conflict with
the four-bucket framing. A future contributor wanting to "fix" this
should read the docstring first; the omission is documented, not
accidental.

**Tag taxonomy reuse.** Arch pass shares the
`[blocker]`/`[nit]`/`[strength]` tagging with craft pass — same block
rule (only `[blocker]` gates the REVIEWED transition; `[nit]` and
`needs-changes` become reconciliation-log items). The "strength" tag
maps awkwardly to "concerns"/"open questions" semantically but
correctly to "what the change gets right" buckets, and the workflow
only cares about block / no-block.

**`subagent-type` extension.** Added `arch-review` to the
`subagent-type` mode choices — reuses `detect_subagent_type()` with
identical precedence as `implementation` / `reconciliation` /
`pr-review`. Preserves the "three subagents, no more" principle —
the arch pass uses the existing `reviewer` agent role, not a new
`arch-reviewer` agent.
