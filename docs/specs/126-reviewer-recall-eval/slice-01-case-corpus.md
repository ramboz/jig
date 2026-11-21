---
status: DRAFT
dependencies: [adr-0071]
last_verified: 2026-11-21
kind: feature
frame_review: true
arch_review: true
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon).
     See docs/workflow.md "Self-defining vocabulary". -->

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation,
     else mark them as assumptions in the spec's `## Assumptions` section —
     never assert an unverified claim as fact. -->

## Slice 126-01 — case-corpus

**Goal:** a committed, validated corpus of reviewer-recall cases in
`evals/reviewer-recall/`. It holds bug cases (each with the change that
introduced it, the commit where that change landed, and a one-sentence
answer key), plus size-matched clean controls and a frozen tuning/test
split. It comes with an `extract` command that reports whether the corpus
clears ADR-0071's size floor. New bug records capture `introduced_by:`.

**Decision:** spec 126 D1 (backfill in the case file, closed records
untouched) and D2 (only `introduced_by:` on the record).

**DoR:**
- ✅ [ADR-0071](../../decisions/adr-0071-reviewer-recall-eval.md) Accepted.
- ✅ The extractor runs on a clone with full history. The drafting clone was
  shallow (64 commits), so the introducing commits named by bugs 029 and 039
  (`a247f76`, `31cbcb4e`) could not be resolved there.
- ✅ The owner has agreed who writes answer keys. Proposed: the owner writes
  or approves each one. Test-set keys freeze with the test-set version.
- ✅ The bug record template is `_record_text` in `skills/bug-fix/bug.py:223`.
  Its closure inventory already asks for "Relevant history inspected"
  (`:279`).

**Assumptions:** None beyond spec A3 and A5.

**Acceptance Criteria:**

1. **The case file has a checked shape.** `evals/reviewer-recall/cases.json`
   holds:
   - a `test_set_version`;
   - `bug_cases[]`, each with `bug` (id), `introduced_by` (`NNN-NN` slice,
     `bug-NNN`, or a commit SHA), `case_commit` (the commit that landed the
     introducing change on `main`), `base_commit`, `answer_key` and `split`
     (`tuning` | `test`);
   - `control_cases[]`, each with `slice`, `case_commit`, `base_commit`,
     `matched_to` (a bug id) and `changed_lines`.

   `scripts/reviewer_recall.py validate` exits non-zero and names the case
   and field for any of:
   - a missing field;
   - an id that resolves to no bug record or slice file;
   - a commit not in history;
   - a `base_commit` that is not `case_commit`'s first parent;
   - an answer key that is more than one sentence or over 300 characters;
   - a control slice that some bug case names as `introduced_by`;
   - a bug case whose `case_commit` tree already contains that bug's own
     record file. That check is a leak guard: the case would postdate the
     report.
2. **The extractor proposes cases; a person confirms them.**
   `reviewer_recall.py extract` reads DONE bug records and prints, for each,
   introducing-change candidates in this order:
   1. the record's `introduced_by:` if set;
   2. slice ids, `bug NNN` references and short SHAs found in its
      `## Root cause` section and "Relevant history inspected" block;
   3. blame candidates: the commits that last touched the non-doc lines that
      the landing commit of the bug's fix changed. That landing commit is the
      one that set the record's `status: DONE`.

   `--json` gives the same output in machine-readable form. It never writes
   `cases.json` or any bug record.
3. **The power check is the headline.** `extract` ends with a summary block:
   - DONE bugs;
   - bugs with at least one candidate;
   - bugs whose `introduced_by:` is `external`;
   - confirmed cases in `cases.json` by split;
   - one line, `power: ok (test n=N)` or `power: below floor (test n=N < 10)`,
     using ADR-0071's floor.

   Exit 0 either way: it reports and does not gate.
4. **Controls are stable and size-matched, and the draw is reproducible.**
   `extract --controls` proposes one control per confirmed bug case. A
   control is a DONE slice that:
   - landed at least 90 days before the run date;
   - is named by no bug case's `introduced_by`;
   - has a `git diff --shortstat base..case` line count within ±50% of the
     bug case's (the nearest one if none is that close).

   The draw is seeded by the bug id, so a rerun on the same history proposes
   the same controls.
5. **The split is assigned once and frozen.** `extract` proposes `split` by
   `int(sha256(bug_id), 16) % 3 == 0` → `tuning`, else `test`.
   `evals/reviewer-recall/test_set.lock` stores `{test_set_version, digest}`,
   where the digest is over the canonical test-set entries. `validate` fails
   with "test set changed without a version bump" when the digest differs
   and the version does not. This covers a new `test` case, an edited key,
   and a moved commit. `validate --relock` rewrites the lock only when the
   version was bumped.
6. **New bug records capture `introduced_by:`.** `bug.py new` emits a blank
   `introduced_by:` in frontmatter. `skills/bug-fix/SKILL.md` says to fill it
   at `ROOT_CAUSED`, when the history search finds the source, with a slice
   id, `bug-NNN`, a commit SHA, or `external` (no jig change introduced it);
   otherwise leave it blank. No transition gate reads it: `bug.py` gate tests
   pass unchanged, and existing bug records are not edited. Host packages are
   rebuilt and `build_host_packages.py --check` passes.
7. **CI checks the corpus without a model.** `scripts/test_reviewer_recall.py`
   (auto-discovered by `scripts/run_tests.py`) runs `validate` on the
   committed corpus and covers each AC1/AC5 refusal with a fixture.
   `evals/README.md` gains a short "Reviewer-recall corpus" section covering
   what a case is, who confirms it, and how the split freezes.

**Edge cases to cover explicitly:**
- The introducing change is another bug's fix (bug 010 ← bug 003). The case
  records `introduced_by: bug-003`, and 126-02 replays bug-review for it.
- One squash commit landed several slices (spec 113, PR #219).
  `introduced_by` names the slice, and `case_commit` is the squash.
- A bug marked `external` (e.g. bug 035's missing Copilot marketplace
  descriptor) is counted in the summary and never proposed as a case.
- A control's landing commit is younger than 90 days: it is not eligible.

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
- [ ] Primer hygiene per spec 025-01 rule (only if this slice closes the
      spec).

**Anti-horizontal-phasing check:** after this slice a maintainer runs one
command and learns whether jig's bug history can support a reviewer eval
(`power: ok` or `below floor`), with a validated, frozen corpus to replay if
it can. That answer decides whether 126-02 is worth building.

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
| `docs/architecture.md` | `no-op` | _TODO: checked for module-boundary / public-contract drift (bug-record frontmatter gains `introduced_by:`)._ |
| Primer surfaces: `CLAUDE.md` / `AGENTS.md` / scaffold templates | `no-op` | _TODO: primer hygiene checked; note compression or template updates if any._ |
| `docs/inbox.md` | `no-op` | _TODO: checked for items resolved by this slice._ |
| `docs/refinement-todo.md` | `no-op` | _TODO: checked for resolved items or new deferred decisions._ |
| `docs/memory/**` | `no-op` | _TODO: note memory-sync result or why nothing was worth capturing._ |
| `docs/decisions/README.md` / ADR index | `no-op` | _TODO: use `updated` when the slice touched ADRs; otherwise mark checked._ |
| Generated host packages (`hosts/**`) | `updated` | _TODO: rebuilt for the `bug.py` / `bug-fix/SKILL.md` change; `--check` clean._ |
