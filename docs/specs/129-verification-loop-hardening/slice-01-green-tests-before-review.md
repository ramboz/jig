---
status: DRAFT
dependencies: [adr-0070, 125-01]
last_verified: 2026-11-21
kind: feature
arch_review: true
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon).
     See docs/workflow.md "Self-defining vocabulary". -->

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation,
     else mark them as assumptions in the spec's `## Assumptions` section —
     never assert an unverified claim as fact. -->

## Slice 129-01 — green-tests-before-review

**Goal:** before a reviewer subagent is spent on a slice, jig checks that the
full suite was green for the code about to be reviewed; in observe mode (the
default) it says what it would have refused and lets the work go on.

**Decision:** spec 129, "Which decision each slice extends" — a new gate on
spec 125's resolver, born `observe` (ADR-0070 §3). ADR-0014 §5's `REVIEWED`
set is unchanged unless the gate is later promoted (ADR-0070 §5).

**DoR:**
- ⬜ ADR-0070 Accepted and 125-01 DONE (resolver, registry, `would block`
  note, `gate_would_block` event).
- ✅ The green-tests check today runs only at landing
  (`skills/slice-land/land.py:309-339`), and the compliance pass is the first
  post-implementation prompt (`skills/spec-workflow/SKILL.md:490-494`,
  `review.py implementation`).
- ✅ `tdd.py run` records nothing (spec A1); a custom command's `{test}`
  token is dropped on a full run (`skills/tdd-loop/tdd.py:392`).

**Acceptance Criteria:**

1. **A full run is recorded.** `tdd.py run <dir>` with no `--test` and no
   `--test-path`, where `<dir>` is the project root, writes
   `.jig/last-test-run.json` there: the exit code, the code identity captured
   before the run started, and the finish time. A targeted run writes nothing.
   A failed write never changes tdd.py's output or exit code. The path joins
   the scaffold's runtime-state ignore block
   (`skills/scaffold-init/scaffold.py:3455` and neighbours) and jig's own
   `.gitignore`.
2. **Code identity.** `HEAD` plus a sha256 over `git diff HEAD --binary` and
   the paths and contents of untracked, non-ignored files, leaving out the
   specs record tree (`project_layout.specs_dir`,
   `skills/_common/project_layout.py:144`), so that recording verdicts and the
   review flow's own slice edits do not make a green run stale. This is
   129-01's own working-tree digest, not 124-02's deliverable-manifest helper:
   it identifies the tree a test run saw, not a set of named deliverables
   (spec A2).
3. **One check, six results.** A shared `_common` predicate returns:
   `green` (record for the current identity, exit 0); `red` (current
   identity, exit 1); `stale` (the latest record is for another identity);
   `missing` (no record); `no-runner` (no matching green or red record and
   `tdd.py detect` finds no runner — a docs-only change, treated like
   land.py's `warn`); `unknown` (identity cannot be computed, e.g. not a git
   checkout, or the tdd helper cannot be located — treated like land.py's
   `not_run`, `land.py:315-320`).
4. **A registered gate at two points.** The gate is registered on 125-01's
   resolver as `tests-before-review`, env var `JIG_TESTS_BEFORE_REVIEW_GATE`,
   default `observe`, rule "spec 129-01". `review.py implementation` calls it
   before printing the prompt, and `workflow.py transition … REVIEWED` calls it
   before the status write. No other prompt builder or transition calls it.
5. **Observe (default).** For `red`, `stale` or `missing`, one `would block`
   note on stderr names the result and the fix (`tdd.py run .`), a
   `gate_would_block` event is recorded, and the command's output and exit
   code are unchanged. `green` and `no-runner` are silent. `unknown` prints one
   note and records no event.
6. **Enforce and off.** In `enforce`, `review.py implementation` exits 2
   without printing a prompt, and `transition` refuses with 125-01's header
   line, the result and the fix; spec 125-03's reasoned `--override` passes a
   single transition when it exists. In `off`, nothing is checked and a
   `gate_bypassed` event is recorded (ADR-0070 §1).
7. **Docs.** spec-workflow SKILL.md "After implementation" says to run the
   full suite green before building the compliance prompt and names the gate
   and its mode; tdd-loop SKILL.md says a full run is recorded and why;
   slice-land SKILL.md says its own run stays the merge-time check;
   `docs/workflow.md` and `templates/docs/workflow.md.template` say the same
   in one line each.

**Edge cases to cover explicitly:**
- Green full run, then a source edit: `stale`.
- Green full run, then `record-review` writes verdicts under the spec's
  `reviews/`: still `green`.
- A targeted green run after a full red run: still `red`.
- A record whose run started before an edit made during the run: `stale`
  (identity is captured at the start).
- Two worktrees of one repository: each has its own `.jig/` record, as with
  `.jig/spec-ref`.

### Behavioral rules (optional)

| Rule | Operation/control | Actor | State/precondition | Outcome | Rationale | AC |
|------|-------------------|-------|--------------------|---------|-----------|----|
| BR-1 | Build compliance prompt / `→ REVIEWED` | Orchestrator | Result `green` or `no-runner` | Proceeds, silent | Nothing cheap is left to run | 3, 5 |
| BR-2 | Same | Orchestrator | `red` / `stale` / `missing`, mode `observe` | Proceeds; one note; `gate_would_block` | Learn the false-positive rate before refusing (ADR-0070) | 5 |
| BR-3 | Same | Orchestrator | `red` / `stale` / `missing`, mode `enforce` | Refused (exit 2) with result and fix | Cheap checks before paid review | 6 |
| BR-4 | Same | Orchestrator | `unknown` | Proceeds; one note | A check that could not run is not evidence of red (land.py precedent) | 3, 5 |

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

**Anti-horizontal-phasing check:** after this slice, an agent that asks for a
compliance review without a green run of the current code sees a one-line
`would block` note naming the fix, and `gate-stats` shows how often that
happens before anyone decides to enforce it.

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
| `docs/architecture.md` | `no-op` | _TODO: likely `updated` — new gate in the inventory._ |
| Primer surfaces: `CLAUDE.md` / `AGENTS.md` / scaffold templates | `no-op` | _TODO_ |
| `docs/inbox.md` | `no-op` | _TODO_ |
| `docs/refinement-todo.md` | `no-op` | _TODO: 006-03's trigger unchanged._ |
| `docs/memory/**` | `no-op` | _TODO_ |
| `docs/decisions/README.md` / ADR index | `no-op` | _TODO_ |
| Additional live prose / generated templates touched by this slice | `deferred` | _TODO_ |
