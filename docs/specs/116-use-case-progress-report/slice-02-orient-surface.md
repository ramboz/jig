---
status: READY_FOR_IMPLEMENTATION
dependencies: [116-01]
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

## Slice 116-02 — orient-surface

**Goal:** The `/jig:orient` project briefing carries a short use-case progress
section whenever the project has adopted the use-case layer, so a returning
owner sees the project-wide done/known totals, the goals with nothing done yet,
and the untraced work — with a pointer to the full per-use-case listing —
without knowing `workflow.py progress` exists.
The section is printed by a deterministic `progress --summary` mode, so orient
copies it rather than filtering the full tree by hand.

**DoR:**
- ⬜ 116-01 DONE — `workflow.py progress` exists and is the single source the
  summary is computed from.
- ✅ The briefing's structure is known:
  [skills/orient/SKILL.md](../../../skills/orient/SKILL.md) has a "What it reads
  (the survey)" section and a fixed, numbered output layout whose sections are
  each marked always / usually / "when they exist". Its headline section tells
  the model not to re-derive by hand what a deterministic command already
  computes — the reason the selection below lives in code.

**Acceptance Criteria:**

1. **A deterministic summary mode.** `workflow.py progress --summary` prints
   exactly three things, computed with slice 01's counting rule: the summary
   totals line; the use cases with no done slice or no spec (id, goal text, and
   which of the two); and the Unanchored count with its spec names. Each of
   the two name lists is capped at 10 entries, followed by an `… and N more`
   line when longer — a project that adopts the use-case layer late starts with
   every spec unanchored. It prints no per-spec tree and no percentage, and in the two not-adopted states it
   prints the same one-line `skipped` / `no-op` notes as the full mode. It
   always exits 0 and writes nothing. Observable: fixture tests over the same
   kinds of fixtures as slice 01, each shown to fail when its feature is
   removed.
2. **A named survey source.** The "What it reads (the survey)" section of the
   orient `SKILL.md` names `workflow.py progress --summary` as a read-only
   source, read only when the project's vision has a `## Use cases` section.
   Observable: the skill text names the command and the condition.
3. **One conditional section in the fixed layout.** The output layout gains a
   "Use-case progress" section marked "when the use-case layer is adopted". It
   carries the `--summary` output's three things and no more, copied rather
   than re-derived, plus one line naming `workflow.py progress` for the full
   per-use-case listing. It never reproduces the full tree and never states a
   percentage. Observable: the skill text specifies exactly those contents and
   both exclusions.
4. **Silent when not adopted.** For a project with no `## Use cases` section the
   briefing is unchanged — no section and no mention of use cases. Observable:
   the skill text states the omission rule.
5. **Orient still writes nothing.** The "Orient writes nothing" contract is
   unchanged; the new source is a read-only command. Observable: that section
   of the skill is untouched and the new source is described as read-only.
6. **Pinned and shipped to every host.**
   `skills/orient/test_orient_skill_surface.py` pins the new survey source and
   the new section, the spec-workflow `SKILL.md` bullet for `progress` names
   `--summary`, and the host packages are regenerated. Observable: the pins
   fail when either is removed, and `scripts/build_host_packages.py --check`
   exits 0.

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

**Anti-horizontal-phasing check:** After this slice, a user who asks jig where
the project stands gets the done/known totals, the untouched goals, and the
unanchored work in the same briefing — no extra command, no new knowledge
required.

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
