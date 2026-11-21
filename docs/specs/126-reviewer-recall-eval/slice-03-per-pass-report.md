---
status: DRAFT
dependencies: [126-02]
last_verified: 2026-11-21
kind: feature
frame_review: true
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon).
     See docs/workflow.md "Self-defining vocabulary". -->

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation,
     else mark them as assumptions in the spec's `## Assumptions` section —
     never assert an unverified claim as fact. -->

## Slice 126-03 — per-pass-report

**Goal:** every audited run leaves a per-pass result tied to a fingerprint
of the prompt it scored. One report compares the passes: which defects only
one pass catches, what a flag left off costs, how tuning and test compare,
and the cost per run. An advisory notice says when a pass's prompt has
changed since its last result.

**Decision:** ADR-0071 rules 5–7. The report shows numbers and never
recommends cutting a pass.

**DoR:**
- ✅ 126-02 DONE, with at least one audited test-set run for compliance and
  craft.
- ✅ A pinned fingerprint fixture (a minimal spec, slice and bug record) is
  agreed for `evals/reviewer-recall/fixture/`.

**Assumptions:** None beyond spec A1–A2.

**Acceptance Criteria:**

1. **Each pass has a prompt fingerprint.** `reviewer_recall.py fingerprint`
   prints one fingerprint per replayed pass and, separately, one for the
   judge prompt. A pass's fingerprint is a sha256 over two inputs:
   - the prompt its builder produces for the pinned fixture. The fixture is
     built as a two-commit repo the same way as 126-02 AC1, with its
     absolute path normalised;
   - `agents/reviewer.md`.

   Two invocations print identical output. A one-character edit to
   `_PR_REVIEW_OUTPUT_FORMAT` changes the craft, arch and code-health
   fingerprints and leaves compliance and bug-review alone. An edit to
   `_INVESTIGATION` changes all five, because it is shared by every
   code-review builder (`review.py:225`).
2. **Each result records what it measured.** A finished run writes
   `evals/reviewer-recall/results/<split>/<pass>.json`. A newer run of the
   same pass and split replaces it; git keeps the history. The file holds:
   - **identity:** the prompt and judge fingerprints, the model id, the
     eval checkout commit, `test_set_version`, and `repeats`;
   - **numbers:** stage `k/n`, control-flag `k/n`, the inconclusive count,
     the bug ids only this pass caught, and the summed host-reported tokens
     and cost;
   - **audit:** the audit state, the sampled judge miss rate, and the date.

   A test-set run that is still `unaudited` writes no result. It stays under
   `.jig/`.
3. **The report compares passes like with like.** `reviewer_recall.py report`
   prints one table over the test-set results, with one row per pass:
   - found, blocking and stopped as `k/n`;
   - the control-flag `k/n`;
   - unique catches;
   - mean cost per run;
   - fingerprint status, `current` or `stale`.

   Below the table it prints two pipeline lines:
   - **as-configured** recall counts a case as stopped when a pass the
     slice's flags would have run stopped it;
   - **all-on** recall counts a case as stopped when any replayed pass did.

   It then lists the bug ids caught all-on but not as-configured as
   "missed because a flag was off". Results that differ in model id, judge
   fingerprint or `test_set_version` go into separate tables and are never
   mixed.
4. **Tuning and test sit side by side.** When both splits have a result for
   a pass under the same prompt fingerprint, the report prints tuning and
   test `stopped` recall next to each other, and the gap between them. It
   gives no verdict on overfitting; the gap is for the person tuning.
5. **A changed prompt gets an advisory re-score nudge.**
   `reviewer_recall.py fingerprint --check` compares each pass's current
   fingerprint with `results/test/<pass>.json`. For each mismatch it prints
   `reviewer prompt for <pass> changed since its last recall result (<date>);
   re-score: reviewer_recall.py run --split test --pass <pass> --model <id>`.
   A judge-fingerprint mismatch gets its own line. The command always exits
   0. A CI step runs it as a non-failing annotation, so it never blocks a
   merge.
6. **The report states numbers only.** Its only advisory line is the stale
   notice from AC5. It never suggests removing, disabling or adding a pass
   ("measure, don't cut", ADR-0071 rule 7). Observable: a snapshot test of
   the report output on fixture results.
7. **No model call.** `scripts/test_reviewer_recall.py` covers AC1–AC6 from
   fixture results and fixture prompts, without calling a model.
   `evals/README.md` documents `report` and `fingerprint --check`.

**Edge cases to cover explicitly:**
- A pass with no result shows `no result` in the report and `never scored`
  in `--check`.
- A pass with no applicable cases prints `0/0`, with no percentage. This can
  happen to bug-review when no test case came from a bug fix.
- Results from two models print as two tables.

**Sibling hooks, not dependencies.** If spec 125 (off / observe / enforce)
lands, the CI notice can register as an observe-mode check instead of a bare
annotation. If spec 127 (diff-triggered review rules) lands, "this diff
touches a reviewer prompt block, so re-score" can become one of its rules.
This slice needs neither.

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
      the spec's Active-specs entry. If this slice introduces a new skill,
      add or update its row in the Skills table.

**Anti-horizontal-phasing check:** after this slice the owner can answer
"which review passes earn their cost?" and "did my prompt edit help?" from
one report. Any edit to a reviewer prompt shows up as a stale result until
someone re-scores it.

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
| Primer surfaces: `CLAUDE.md` / `AGENTS.md` / scaffold templates | `no-op` | _TODO: primer hygiene checked; spec closes here — compress the Active-specs entry if one was added._ |
| `docs/inbox.md` | `no-op` | _TODO: checked for items resolved by this slice._ |
| `docs/refinement-todo.md` | `no-op` | _TODO: checked for resolved items or new deferred decisions (e.g. whether data now fires the `security_review` promotion trigger)._ |
| `docs/memory/**` | `no-op` | _TODO: note memory-sync result or why nothing was worth capturing._ |
| `docs/decisions/README.md` / ADR index | `no-op` | _TODO: use `updated` when the slice touched ADRs; otherwise mark checked._ |
| `.github/workflows/ci.yml` / `scripts/ci_check.py` | `updated` | _TODO: non-failing fingerprint notice step added; both runners kept in the same order._ |
