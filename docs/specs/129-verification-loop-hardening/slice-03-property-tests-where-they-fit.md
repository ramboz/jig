---
status: DRAFT
dependencies: []
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

## Slice 129-03 — property-tests-where-they-fit

**Goal:** tdd-loop suggests a property test when the code under test has a
round-trip, invariant, idempotency or equivalence shape, and jig ships its
first property test, on status-board regeneration.

**Decision:** extends tdd-loop's contract (`skills/tdd-loop/SKILL.md`) with
judgment only. A property test checks a rule over many generated inputs
instead of a few hand-picked ones, so its cases are not chosen by the same
agent that wrote the code (R-002 mechanism 3).

**DoR:**
- ✅ jig's runner is stdlib `unittest` on Python 3.9 and 3.12 with nothing
  installed (spec A5), so jig's own test uses a seeded `random.Random`
  generator, not Hypothesis.
- ✅ The board's behaviour to pin: `regenerate_status_board` keeps the
  preamble and the curated Notes column
  (`skills/spec-workflow/workflow.py:2796`), keyed by `(spec_dir, label)` in
  `parse_existing_notes` (`workflow.py:2428`). Notes must not hold a raw `|`
  or a newline; the documented escape is `&#124;`
  (`skills/spec-workflow/SKILL.md:1088`).

**Acceptance Criteria:**

1. **The nudge.** tdd-loop SKILL.md gains a short section, "When a property
   test fits", naming the four shapes with one example each: round-trip
   (parse then render gives the input back), invariant (a rule that holds
   after every operation), idempotency (running twice equals running once),
   equivalence (a new path agrees with an old or simple one). It says to use a
   property library only when the project already depends on one (Hypothesis,
   fast-check, proptest); otherwise to write a seeded loop over generated
   inputs in the project's existing test framework; never to add a test
   dependency without the user's say-so; and to keep any failing generated
   case as a fixed example test.
2. **No helper change.** `tdd.py detect` and `tdd.py run` behave and print
   exactly as before; nothing detects property libraries.
3. **jig's first property test.** A new stdlib-only test generates project
   fixtures from fixed seeds — spec folders, slices in every status including
   `DEFERRED`, `ABANDONED` and blocked, and curated Notes drawn from the
   documented Notes alphabet (`&#124;` included, raw `|` and newlines
   excluded) — and asserts for every case: regenerating twice gives the same
   board as regenerating once; every curated Note on a row whose slice still
   exists survives byte for byte; the main status table has exactly one row
   per slice.
   It runs at least 200 generated cases in under 5 seconds on the CI runner,
   on both Python versions.
4. **Failures can be replayed.** A failing case prints its seed and the
   generated fixture's file list and Notes, and a documented one-line
   invocation re-runs that seed alone.
5. **Capable of failing.** Making `parse_existing_notes` drop the last note
   it reads, and making `render_status_table` emit a second row for a blocked
   slice, each turn the test red; both mutations are witnessed and recorded in
   the deviation log.
6. **A real counterexample is a bug, not a filter.** If the generator finds a
   defect in jig, it is filed through `bug-fix` with the generated case as its
   regression test. The generator's input range is not narrowed to make the
   test pass.

**Edge cases to cover explicitly:**
- A board whose Notes column is empty everywhere.
- A slice removed between two regenerations: its row and Note go; other Notes
  stay.
- A spike-marked row (`🔬`), whose Note is keyed without the marker
  (`workflow.py:2466`).

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
      spec**, check `CLAUDE.md`, `AGENTS.md`, and scaffold templates, then
      compress the spec's Active-specs entry.

**Anti-horizontal-phasing check:** after this slice, an agent test-driving a
parser, formatter or regeneration step is prompted to add a property test, and
jig's own board regeneration is checked against hundreds of generated boards
instead of four hand-written ones.

### Deviation log (after reconciliation)

The original slice is preserved above. Implementation notes:

_TODO: numbered sections covering deviations from the planned shape,
reviewer findings folded back in, doc updates, plan adherence._

### Reconciliation sweep

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `README.md` | `no-op` | _TODO_ |
| `docs/specs/README.md` | `updated` | _TODO_ |
| `docs/product-vision.md` | `no-op` | _TODO_ |
| `docs/architecture.md` | `no-op` | _TODO_ |
| Primer surfaces: `CLAUDE.md` / `AGENTS.md` / scaffold templates | `no-op` | _TODO_ |
| `docs/inbox.md` | `no-op` | _TODO_ |
| `docs/refinement-todo.md` | `no-op` | _TODO_ |
| `docs/memory/**` | `no-op` | _TODO: a learnings entry if the generator finds something._ |
| `docs/decisions/README.md` / ADR index | `no-op` | _TODO_ |
| Additional live prose / generated templates touched by this slice | `deferred` | _TODO_ |
