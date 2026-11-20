---
status: IN_PROGRESS
dependencies: [123-01]
last_verified: 2026-11-20
kind: feature
# arch_review: true  # set to true when this slice changes module
#                    # boundaries, public contracts, or architecture-
#                    # shaped concerns (triggers arch-review pass).
# design_review: true  # set true when this slice's fidelity must be a HARD
#                      # gate: extract the mockup's design values (colours,
#                      # spacing, sizes, layout rules) into this slice's ACs,
#                      # then wire a servo `design-eval` as the done-condition
#                      # (attest-only at REVIEWED; ADR-0014, ADR-0022,
#                      # ADR-0049).
claimed_by: claude/xenodochial-tu-c3ef9e
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon).
     See docs/workflow.md "Self-defining vocabulary". -->

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation,
     else mark them as assumptions in the spec's `## Assumptions` section —
     never assert an unverified claim as fact. -->

## Slice 123-02 — dead-end-policy-recipe

**Goal:** a user whose project has no built-in runner is told what to do by the tool itself, the docs state that jig adds no per-framework adapters, and a Gradle project has one worked wrapper to copy.

**Decision:** [ADR-0068](../../decisions/adr-0068-no-per-framework-runner-adapters.md) §1, §3, §4.

**DoR:**
- ✅ Slice 123-01 fixes the contract this slice's messages and recipe describe.
- ✅ Skill directories ship whole in the host packages except `test_*.py` (`scripts/build_codex_plugin.py`; existing `worked-example-*.md` siblings ship today), so a document beside `SKILL.md` reaches consumers.

**Assumptions:** None beyond the spec's.

**Acceptance Criteria:**

1. **`detect` names the way out.** With no runner, `tdd.py detect` exits 2; the first stderr line is still `no test runner detected at <target>`. The last stderr line is a single line of at most 300 characters (the length `bug.py` quotes untruncated) that names `.jig/test-command` and the `{test}` placeholder, states the exit contract (0 passed, 1 a test ran and failed, anything else could not run), says a build failure must not exit 1 and that a build tool needs a wrapper, and names `test-command-recipes.md`. A line before it prints the recipes document's resolved path (the file beside `tdd.py`), kept off the last line because an absolute path may not fit the 300 characters.
2. **`run` does the same**, with and without `--test`.
3. **The bug-fix gate carries it.** `bug.py transition <id> FIXING` on a project with no runner fails with an error that names `.jig/test-command`, `{test}`, the exit contract, the build-failure caveat and `test-command-recipes.md`. Runs the real `tdd.py`. `skills/bug-fix/SKILL.md` (the skill an agent is working from when it hits this gate) links the contract and the recipes document where it describes the red/green gates.
4. **`SKILL.md` states the policy.** `skills/tdd-loop/SKILL.md` says the built-in runner list is closed (pytest, vitest, jest, `node --test`), that every other stack uses the command contract, links ADR-0068 and the recipes document, and no longer lists rspec / `go test` / `cargo test` detection as merely deferred.
5. **A recipes document ships with the skill.** `skills/tdd-loop/test-command-recipes.md` states the contract, says a bare build-tool command that exits 1 on a compile failure is not sound, and gives one worked example: a Gradle JVM-unit-test wrapper script that lives in the consuming project. The wrapper maps a selector to `--tests`, exits 1 only when a JUnit XML report from this run counts a failure or an error in its `<testsuite>` header (not by searching the body, which holds the tests' captured output), and exits 2 when the build failed or no test ran. It says: the script has not been run against real Gradle by jig; the Gradle task and the report location are settings the project must check (an Android module's task is per variant, for example `:app:testDebugUnitTest`, and in a multi-module build the task must name the module); Android instrumented tests are out of scope for jig and are the project's to wire through the same contract; jig does not ship or run the wrapper; the document is one example, not a catalogue.
6. **The recipe's script is exercised against a stub `gradlew`** (a test extracts the wrapper from the document). The staleness mechanism is fixed: the wrapper deletes the task's existing report files before it calls Gradle, so an earlier run's reports cannot reach the verdict. That deleting a task's outputs also makes Gradle re-run it instead of skipping it as up to date is an **assumption** about Gradle (not probed; the stub cannot falsify it). If it is wrong the wrapper fails closed (no report → exit 2), and the recipe says so and names Gradle's `clean<TaskName>` rule as the alternative. Cases: tests pass → 0; a report counting a failure → 1; a report counting an error → 1; a passing report whose captured output contains `<failure …>` text → 0; `gradlew` fails and writes no report → 2; `gradlew` fails with reports that hold no failure → 2; `gradlew` exits 0 and writes no report (the task was skipped or filtered to nothing) → 2; `gradlew` exits 0 with a report holding no test case → 2; a selector `pkg.Class::method` reaches `gradlew` as `--tests pkg.Class.method`; a failing report left by an earlier run is deleted before the run and does not turn a passing run red; `gradlew` missing → 2.
7. **Other live docs agree.** `docs/product-vision.md`'s out-of-scope line, `docs/adoption-readiness.md` and its scaffold template describe the closed list and the command contract; `docs/refinement-todo.md` records a generic JUnit-XML reader as a demand-gated option.
8. **Host packages are regenerated** and `scripts/build_host_packages.py --check` is clean.

**Edge cases to cover explicitly:**
- The dead-end line must stay one line: `bug.py` quotes only the last stderr line.
- The recipe test needs only `sh`; it is skipped where `sh` is absent.

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

**Anti-horizontal-phasing check:** after this slice a Gradle user who runs `tdd.py detect` reads what file to create and what its command must return, and finds a wrapper to adapt (task name and report location are theirs to set and verify).

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
