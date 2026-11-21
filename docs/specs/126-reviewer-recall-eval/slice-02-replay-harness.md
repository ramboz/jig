---
status: DRAFT
dependencies: [126-01, adr-0071]
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

## Slice 126-02 — replay-harness

**Goal:** one dev-time command replays each selected code-reviewing pass,
using today's baseline prompt, against each case's state at review time. A
blind judge credits findings against the answer key, and a person audits
the credits on the test set. The command prints `k/n` recall at each stage
and the control flag rate.

**Decision:** spec 126 D3 (replayed passes, baseline prompt only) and D4
(stages). ADR-0071 rules 3–5 and 8.

**DoR:**
- ✅ 126-01 DONE, and `reviewer_recall.py extract` reports `power: ok`. Below
  the floor this slice does not start (ADR-0071 kill criterion).
- ✅ Spec A4 probed and the flags recorded in this slice. A headless host run
  in a scratch directory must:
  - (a) be limited to Read/Glob/Grep;
  - (b) leave out user-global config, plugins and hooks;
  - (c) run on a pinned model;
  - (d) report usage and cost as JSON.

  If (a) or (b) fails, stop: the replay would not be a faithful reviewer run.

**Assumptions:** spec A1, A2, A4.

**Acceptance Criteria:**

1. **Each case gets a fresh, leak-free scratch repo.** For each case, `run`
   builds a new two-commit git repo in a temp directory:
   - commit 1 is `base_commit`'s tree, on branch `main`;
   - commit 2 is `case_commit`'s tree, on `HEAD`, with a neutral message.

   Commit 2 has the review-time artifacts stripped:
   - the case slice's `reviews/slice-NN-*.md`, or for a bug case its
     `docs/bugs/reviews/` records;
   - the slice file's text from `### Deviation log` on;
   - the slice's `status:` reset to `IN_PROGRESS` (`FIXING` for a bug), with
     its DoD boxes unticked;
   - any `review.*_skill` config.

   Observable: a test inspects a built repo. It has exactly two commits and
   none of the stripped artifacts, and `git merge-base main HEAD` returns
   commit 1 (spec A2).
2. **Prompts are today's baseline, built by today's code.** The harness
   imports the eval checkout's `review.py` builders and calls them on the
   scratch repo with `richer_skill=None` and `non_interactive=True`. The
   deliverables are the files changed `base..case`, capped at 50 as
   `_touched_files_block` does.
   - **Code-health** gets a `health.py` summary from the scratch repo when a
     linter resolves. Otherwise it gets the builder's no-summary prompt
     (`review.py:2374`). Which one it got is recorded.
   - **Applicability:** compliance, craft, arch and code-health run on every
     slice case; bug-review runs on `bug-NNN` cases only. Each run records
     the review flags the slice set at `case_commit`, for 126-03's
     as-configured view.
   - **Build failure:** a case the builder cannot build is recorded as
     `inconclusive (build: <error>)`, never as a miss.
3. **Reviewer runs are read-only and recorded.** Each (case, pass, repeat)
   is one headless run with the scratch repo as its working directory,
   Read/Glob/Grep as its only tools, and the model from the required
   `--model` flag. The raw envelope and the host-reported usage go to
   `.jig/reviewer-recall/runs/<run-id>/`, which is added to `.gitignore`.
   An unparseable envelope, a timeout or an auth failure is reported as
   `inconclusive`, never as a miss. This is the same rule
   `orchestrator_selection_probe.py` follows.
4. **The judge credits only findings that describe the bug.** Each bug-case
   run gets one tool-less judge call. The judge receives the answer key and
   the run's numbered `SPECIFIC ISSUES` entries. It does not see the pass
   name, prompt, verdict or split. For each entry it returns `credited` and
   a verbatim quote. A credit whose quote is not a substring of the entry
   is dropped and counted as a judge error. Controls get no judge call:
   a control is flagged if it has any `[blocker]` entry or a non-`pass`
   verdict.
5. **A human audit bounds the judge on the test set.**
   `reviewer_recall.py audit <run-id>` shows every judge-credited entry that
   has no cached label, plus a seeded sample of up to 20 uncredited
   bug-case entries. The person answers yes or no to each.
   - **Storage:** labels go to `evals/reviewer-recall/labels.json`, keyed by
     sha256 of the answer key plus the entry text, with the entry text
     stored alongside. A human label overrides the judge, and later runs
     reuse cached labels.
   - **Result states:** a test-set result stays `unaudited` until every
     credit is labelled. The audit prints the sampled judge miss rate. Above
     0.2 the result is marked `unverified` (ADR-0071 kill criterion).
6. **Scoring prints `k/n` by stage.** For each pass, `run` prints:
   - `found`, `blocking` and `stopped` as `k/n` over applicable bug cases
     (spec D4), with a percentage only when `n ≥ 10`;
   - the control flag rate as `k/n`;
   - the inconclusive count, the split and the audit state;
   - the summed host-reported tokens and cost.

   `audit` prints the same once it finishes. `--repeats K` (default 1) runs
   each case K times and reports the fraction of runs that hit, per case.
7. **Cost is planned before it is spent.** `run --plan` prints the number of
   reviewer runs (cases × applicable passes × repeats) and judge calls, and
   makes no model call. `run` refuses to start when the planned total
   exceeds `--max-runs` (default 100) unless the cap is raised. Tokens and
   cost are summed from what the host reports for each run. The script has
   no price table (spec 056).
8. **Nothing calls a model in CI.** No CI step and no `run_tests.py` test
   makes a model call. `scripts/test_reviewer_recall.py` covers AC1–AC7 with
   injected reviewer and judge runners, the
   `orchestrator_selection_probe.py` pattern.

**Edge cases to cover explicitly:**
- An inconclusive run is excluded from `n`, never counted as a miss.
- A judge credit with a forged or paraphrased quote is dropped.
- A cached human `no` overrides a judge credit, and a cached `yes`
  overrides a judge miss.
- A control with a `[blocker]` entry under a `pass` verdict counts as
  flagged. That verdict contradicts the tag, and the run is noted.
- A pre-spec-018 case whose slice is an embedded `## Slice` section builds
  through `_slice_source`, or is inconclusive. It never crashes the run.

### Verification scenario

**Preconditions:** host CLI authenticated; 126-01's corpus committed; no
secrets in fixtures.

**Invocation:** `python3 scripts/reviewer_recall.py run --split tuning
--pass compliance --pass craft --limit 2 --model <id>`, then `audit` on the
printed run id. `--limit 2` selects 2 bug cases and their 2 matched
controls.

**Preserved behavior:** `python3 scripts/run_tests.py` stays model-free, and
`skill_routing.py` and the CI workflow are unchanged.

**Code revision / dirty-change identity:** _record the eval checkout commit
and the run id._

| Step | AC | Expected | Observed | Outcome | Evidence |
|------|----|----------|----------|---------|----------|
| 1 | AC7 | `--plan` prints 8 reviewer runs + 4 judge calls (2 bug cases + 2 controls, 2 passes), no model call | _TBD_ | not-run | _run log_ |
| 2 | AC1–AC4, AC6 | `k/n` lines per pass, cost summed, envelopes under `.jig/reviewer-recall/runs/` | _TBD_ | not-run | _run dir_ |
| 3 | AC5 | audit lists every credit; labels written; result state printed | _TBD_ | not-run | `labels.json` diff |

**DoD:**
- [ ] All ACs pass; full test suite green (no regressions).
- [ ] Implementer test coverage exercises each AC with at least one
      fixture. Edge cases listed in the slice are covered explicitly.
- [ ] Each new test has been shown to fail when its feature is removed —
      the test is capable of failing, not vacuously green (mutate the
      feature, watch the test go red, restore).
- [ ] Verification scenario run once live; outcomes recorded.
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

**Anti-horizontal-phasing check:** after this slice a developer changing a
reviewer prompt runs one command and sees, on the fixed test set, how many
known defects each pass finds, flags as blocking, and stops on, and how
often it flags clean work.

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
| `docs/product-vision.md` | `no-op` | _TODO: checked for behavior / scope drift (principle 3: no new subagent shape)._ |
| `docs/architecture.md` | `no-op` | _TODO: checked for module-boundary drift (repo-only script importing `review.py` builders)._ |
| Primer surfaces: `CLAUDE.md` / `AGENTS.md` / scaffold templates | `no-op` | _TODO: primer hygiene checked; note compression or template updates if any._ |
| `docs/inbox.md` | `no-op` | _TODO: checked for items resolved by this slice._ |
| `docs/refinement-todo.md` | `no-op` | _TODO: checked for resolved items or new deferred decisions._ |
| `docs/memory/**` | `no-op` | _TODO: note memory-sync result or why nothing was worth capturing._ |
| `docs/decisions/README.md` / ADR index | `no-op` | _TODO: use `updated` when the slice touched ADRs; otherwise mark checked._ |
| `.gitignore` / `evals/README.md` | `updated` | _TODO: run directory ignored; harness usage documented._ |
