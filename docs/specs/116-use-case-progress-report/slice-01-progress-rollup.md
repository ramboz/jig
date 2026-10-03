---
status: READY_FOR_IMPLEMENTATION
dependencies: [adr-0025, adr-0064, 068-03]
last_verified:
frame_review: true
# arch_review: true  # set to true when this slice changes module
#                    # boundaries, public contracts, or architecture-
#                    # shaped concerns (triggers arch-review pass).
# design_review: true  # set true when this slice's fidelity must be a HARD
#                      # gate: extract the mockup's design values (colours,
#                      # spacing, sizes, layout rules) into this slice's ACs,
#                      # then wire a servo `design-eval` as the done-condition
#                      # (attest-only at REVIEWED; ADR-0014, ADR-0022,
#                      # ADR-0049).
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon).
     See docs/workflow.md "Self-defining vocabulary". -->

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation,
     else mark them as assumptions in the spec's `## Assumptions` section —
     never assert an unverified claim as fact. -->

## Slice 116-01 — progress-rollup

**Goal:** `workflow.py progress [--project-dir DIR]` prints, for each use case
in the vision, the specs that cite it and how many of their slices are done,
followed by the specs that cite no use case — so the owner sees in one report
how far along each intended behavior's known work is, which specs are still
open under it, and which work cites no behavior at all.

**DoR:**
- ✅ 068-03 DONE — `coverage`, the spec-level `use_cases:` trace links, and
  `parse_use_cases` / `resolve_use_cases` exist
  ([skills/_common/use_cases.py](../../../skills/_common/use_cases.py)).
- ✅ jig's own repo carries a `## Use cases` section and backfilled trace links
  (commit `4cdbf6f1`) — the dogfood corpus.
- ✅ The owner ruling that places this report in jig is recorded as a decision
  record (spec OQ1) —
  [ADR-0064](../../decisions/adr-0064-use-case-progress-rollup-in-jig.md).

**Acceptance Criteria:**

1. **Rollup by use case.** On a project whose vision has a `## Use cases`
   section, the output lists every use case in vision order as its `UC-N` id,
   goal text, and `D/K slices done`; under each, every spec citing it as spec
   directory name, spec status (the `compute_spec_status` value), and `d/k`.
   Observable: a fixture with two use cases and three specs in known slice
   states prints exactly the expected counts.
2. **The counting rule mirrors the spec rollup.** A slice counts toward K unless
   its status is `DEFERRED` or `ABANDONED` — the exclusions `compute_spec_status`
   applies — and toward D only when its status is `DONE`. Deferred slices are
   shown as a separate `(+N deferred)` suffix, never inside K. Slices are read
   in both layouts (file-per-slice and legacy embedded `## Slice` sections).
   Observable: a fixture spec with 2 `DONE` + 1 `DRAFT` + 1 `DEFERRED` + 1
   `ABANDONED` slice prints `2/3 (+1 deferred)`; a legacy-layout fixture spec is
   counted the same way.
3. **Unanchored bucket.** Specs that cite no resolvable use case — an empty or
   absent `use_cases:`, or only ids absent from the vision — are listed under a
   final `Unanchored` heading with the same per-spec line and a bucket total. A
   spec citing an unknown id names that id on its line. Observable: a fixture
   with one orphan spec and one spec citing only `UC-99` shows both there;
   neither is dropped.
4. **A use case with no spec is still listed.** It appears in vision order,
   marked `no spec yet`. Observable on a fixture with one uncited use case.
5. **Multi-cited specs.** A spec citing two use cases appears under both and
   counts toward both use-case totals; the closing summary line counts each spec
   and each slice **once**, and says so. Observable: on a fixture with one
   doubly-cited spec, the summary total is smaller than the sum of the
   per-use-case totals.
6. **Counts, not percentages.** No percentage appears anywhere in the output.
   Observable: no `%` character in the output of any fixture.
7. **Read-only, advisory, silent when not adopted.** `progress` always exits 0
   and writes nothing. With no `product-vision.md` it prints a one-line
   `skipped` note; with a vision that has no `## Use cases` section it prints a
   one-line `no-op` note and **no** rollup — the same two states `coverage`
   has. Observable: both fixtures; a before/after snapshot of the fixture tree
   is identical.
8. **Documented beside its sibling.** The "What this skill does" list in
   [skills/spec-workflow/SKILL.md](../../../skills/spec-workflow/SKILL.md) gains
   a `progress` bullet next to `coverage`, and the host packages are
   regenerated. Observable: `scripts/build_host_packages.py --check` exits 0.
9. **The vision's out-of-scope line is squared with the ruling.** The "Project
   management surface" bullet in [docs/product-vision.md](../../product-vision.md)
   names the read-only use-case progress rollup as the bounded exception. The
   wording is **proposed to the owner and written only after the owner approves
   it**. Observable: the approved wording is in the vision and the approval is
   noted in the deviation log.
10. **The stale "jig's own repo" example is gone from live text.** jig adopted
    the use-case layer on 2026-10-03, so live text may no longer cite jig's own
    repo as an example of a project that has not. Known sites: the `coverage`
    no-op message and docstring in `workflow.py`, the module docstring of
    `use_cases.py`, and the "no-section no-op" paragraph of the spec-workflow
    `SKILL.md`. Closed records (spec 068's slices, ADR-0025) are left as written
    (ADR-0010). Observable: a search of `skills/` for the phrase returns no hit
    that presents jig's own repo as not adopted.

**DoD:**
- [ ] All ACs pass; full test suite green (no regressions).
- [ ] Implementer test coverage exercises each AC with at least one
      fixture. Edge cases listed in the slice are covered explicitly.
- [ ] Each new test has been shown to fail when its feature is removed —
      the test is capable of failing, not vacuously green (mutate the
      feature, watch the test go red, restore).
- [ ] Reviewed by `reviewer` subagent. Reviewer prompt built by
      `review.py`.
- [ ] Implementation review passed.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation sweep produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were
      deferred during implementation.

### Close-out (post-DONE)

These items can only be ticked AFTER the final `RECONCILED → DONE`
transition. Slice-land's `check_dod` (slice 009-01) excludes them
from the count.

- [ ] `docs/specs/README.md` regenerated by `workflow.py status-board`.
      Notes column receives any load-bearing per-slice invariant
      (it's preserved across regen).
- [ ] Primer hygiene per spec 025-01 rule: **if this slice closes the
      spec** (all non-deferred slices DONE), check `CLAUDE.md`,
      `AGENTS.md`, and scaffold templates when present, then **compress**
      the spec's Active-specs entry — drop facts derivable from the
      spec dir + status board, migrate load-bearing per-slice
      invariants to the status board Notes column, keep at most a
      one-liner only for cross-cutting facts. If the spec is still
      in flight (other slices DRAFT / READY / IN_PROGRESS), leave
      the entry. If this slice introduces a new skill, add or
      update its row in the Skills table.

**Anti-horizontal-phasing check:** After this slice, the owner runs one command
in jig's own repo and reads progress per use case plus the unanchored bucket —
end to end, on real data.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

_TODO: numbered sections covering deviations from the planned shape,
reviewer findings folded back in, doc updates, plan adherence._

### Reconciliation sweep

Record the drift-prone surfaces checked during reconciliation. The transition
gate only requires this subsection to exist; the reconciliation reviewer judges
whether coverage and rationales are honest.

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `README.md` | `no-op` | _TODO: why this slice did not affect the project front door, or summarize the update._ |
| `docs/specs/README.md` | `updated` | _TODO: regenerated by `workflow.py status-board`, or explain why deferred._ |
| `docs/product-vision.md` | `no-op` | _TODO: checked for behavior / scope drift._ |
| `docs/architecture.md` | `no-op` | _TODO: checked for module-boundary / public-contract drift._ |
| Primer surfaces: `CLAUDE.md` / `AGENTS.md` / scaffold templates | `no-op` | _TODO: primer hygiene checked; note compression or template updates if any._ |
| `docs/inbox.md` | `no-op` | _TODO: checked for items resolved by this slice._ |
| `docs/refinement-todo.md` | `no-op` | _TODO: checked for resolved items or new deferred decisions._ |
| `docs/memory/**` | `no-op` | _TODO: note memory-sync result or why nothing was worth capturing._ |
| `docs/decisions/README.md` / ADR index | `no-op` | _TODO: use `updated` when the slice touched ADRs; otherwise mark checked._ |
| Additional live prose / generated templates touched by this slice | `deferred` | _TODO: name owner or trigger when real cleanup remains; otherwise replace with `no-op`._ |
