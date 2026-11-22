---
status: DRAFT
dependencies: [adr-0069]
last_verified: 2026-11-21
kind: feature
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon).
     See docs/workflow.md "Self-defining vocabulary". -->

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation,
     else mark them as assumptions in the spec's `## Assumptions` section —
     never assert an unverified claim as fact. -->

## Slice 124-01 — honest-test-plan

**Goal:** the `## Test plan` section of a slice-land PR body states what was
actually checked: the test run and the commit it ran on, each required review
verdict as recorded, and the verification scenario's outcomes. Anything not
checked says so, and no row is ticked by default.

**Decision:** spec 124 D1 / ADR-0069 decision 3.

**DoR:**
- ✅ `check_tests` already yields `green` / `red` / `warn` / `not_run`
  (`skills/slice-land/land.py:309-339`) and the readiness report renders each
  (`land.py:516-532`).
- ✅ Verdict paths and parsing are shared: `evidence_path`,
  `parse_verdict_file`, `required_passes`
  (`skills/_common/review_evidence.py:245`, `:382`, `:261`).
- ✅ Spec 118's scenario table has a closed Outcome vocabulary: `pass`, `fail`,
  `not-run`, `environment-error` (`templates/docs/specs/slice-template.md:76`).
- ⬜ ADR-0069 Accepted.

**Acceptance Criteria:**

1. **No fixed ticks.** `render_pr_body` no longer emits the three fixed lines
   (`land.py:704-707`). Every Test plan row is built from evidence passed in.
   A fixture whose test check is `not_run` yields a body whose tests row
   contains `NOT RUN` and no `[x]`.
2. **The tests row names its commit.** The row matches the readiness result
   (`green` → `[x]`, `red` → `[ ]`, `warn` → `[?]` no runner, `not_run` →
   `[!] NOT RUN`) and adds the short HEAD SHA the run used and whether the
   working tree was clean (`git status --porcelain` empty). A green run on a
   dirty tree renders `[?] Tests: green on uncommitted changes at <sha> — not
   evidence for the pushed commits`. The readiness report's tests row shows
   the same dirty note; its blockers and exit code don't change.
3. **One row per required review pass.** For each pass in
   `required_passes("REVIEWED", <slice flags>)` plus `reconciliation`, the
   body has a row read from the recorded verdict file:
   `[x] <pass>: pass (<reviewed_at>, <record path>)` when it clears;
   `[ ] <pass>: <verdict>` when it doesn't; `[ ] <pass>: NOT RECORDED` when the
   file is missing; `[ ] <pass>: unreadable record (<problem>)` when it doesn't
   parse. `land.py` uses the `_common/review_evidence` functions and doesn't
   re-implement them.
4. **Scenario row.** If the slice has a `### Verification scenario` section
   whose table has an `Outcome` column, the row is `[x]` only when at least one
   step is present and every step is `pass`; otherwise `[ ]` with a count per
   outcome. The template placeholder `_not-run_` counts as `not-run`. A
   section without a readable table renders `[?] Verification scenario:
   present, outcomes not parsed — see slice`. No section renders
   `- Verification scenario: none declared` with no checkbox. The scenario's
   own recorded revision is not checked against HEAD.
5. **Both PR paths agree.** `prepare --mode pr` and `execute --mode pr` write
   the same Test plan section for the same tree and records. `execute` reuses
   its readiness checks instead of rebuilding the body without them
   (`land.py:1531-1537`).
6. **Docs say what the rows mean.** The slice-land SKILL.md gotcha that calls
   the lines placeholders (`skills/slice-land/SKILL.md:255-259`) is replaced
   with a short description of the rows and their markers. Readiness checks,
   blockers and exit codes are unchanged.

**Edge cases to cover explicitly:**
- A doc-only slice (`warn`) renders `[?]`, not `[x]`.
- An `arch_review: true` slice gets an `arch` row; a `design_review: true`
  slice gets a `design-review` row; an unflagged slice gets neither.
- A slice taken to `DONE` with `JIG_REVIEW_EVIDENCE_GATE=0` and no records
  renders `NOT RECORDED` rows. It is not an error.
- A `needs-changes` record renders `[ ]`, even when the slice is `DONE`.
- A scenario table with a mix of `pass` and `not-run` renders `[ ]` with both
  counts.

**Reading spec 118's table.** Spec 118 kept "parser" out of its own pilot. This
slice reads one column of that table, with its closed vocabulary, for display
only. It never gates, and anything it can't read is reported as "not parsed".

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
- [ ] Primer hygiene per spec 025-01 rule: if this slice closes the spec,
      compress the Active-specs entry; otherwise leave it.

**Anti-horizontal-phasing check:** after this slice, a PR opened with
slice-land tells a reviewer which checks ran, on which commit, and which
didn't, instead of three ticks that are always there.

### Deviation log (after reconciliation)

The original slice is preserved above. Implementation notes:

_TBD — not yet implemented (recorded, not built)._

### Reconciliation sweep

Record the drift-prone surfaces checked during reconciliation. The transition
gate only requires this subsection to exist; the reconciliation reviewer judges
whether coverage and rationales are honest.

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `skills/slice-land/SKILL.md` | `updated` | _TBD — gotcha replaced (AC6)._ |
| `docs/specs/README.md` | `updated` | _TBD — regenerate by `workflow.py status-board` at close._ |
| Host packages (`build_host_packages.py`) | `updated` | _TBD — regenerate after the SKILL.md edit._ |
| `docs/architecture.md` | `no-op` | _TBD — check whether the slice-land → `_common/review_evidence` import needs a line._ |
| Primer surfaces: `CLAUDE.md` / `AGENTS.md` / scaffold templates | `no-op` | _TBD at close._ |
