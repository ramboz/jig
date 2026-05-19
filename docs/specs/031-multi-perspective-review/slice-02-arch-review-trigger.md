---
status: DRAFT
dependencies: [031-01]
last_verified:
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

- [ ] All ACs pass; full test suite green (no regressions).
- [ ] Implementer test coverage exercises each AC. The
      `slice_needs_arch_review` helper and the
      `arch_review:`-missing-default-false case are covered explicitly.
- [ ] Reviewed by `reviewer` subagent (compliance pass).
- [ ] Reviewed by `pr-review` skill (craft pass via 031-01).
- [ ] Reviewed by `arch-review` skill via the new `review.py arch-review`
      pass (THIS slice's dogfood — first arch-review pass in the
      workflow).
- [ ] Implementation review passed.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were
      deferred during implementation.

### Close-out (post-DONE)

These items can only be ticked AFTER the final `RECONCILED → DONE`
transition. Slice-land's `check_dod` (slice 009-01) excludes them
from the count.

- [ ] `docs/specs/README.md` regenerated by `workflow.py status-board`.
      Notes column for 031-02 carries the load-bearing invariant
      (`arch_review:` field shape + conditional trigger + arch-pass
      block rule).
- [ ] `CLAUDE.md` hygiene per spec 025-01 rule: spec 031 doesn't
      introduce a new skill. Active-specs entry compressed on close-out
      if any was added (lean: none).
- [ ] `skills/independent-review/SKILL.md` and
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

_TBD — populated during reconciliation._
