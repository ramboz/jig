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

1. **Three stderr lines, not one.** The no-runner output is: the existing
   `no test runner detected at <target>` line; a line naming the built-in
   list and the recipes document's resolved path; and the one-line hint
   (290 characters, under `bug.py`'s 300-character quote). The resolved path
   is kept off the last line because an absolute path does not fit the
   budget. The hint was shortened twice to stay under 300.
2. **The hint carries the build-failure caveat and names the recipes
   document** (frame critique, round 2): the actor who hits this dead end is
   usually an agent inside `bug.py transition … FIXING`, and the obvious
   reading of "create `.jig/test-command`" on Gradle is the unsound bare
   command. `skills/bug-fix/SKILL.md` now links the contract and the recipes
   document at the gate and in its gotchas.
3. **The wrapper's red signal changed twice.** First draft: `grep` for
   `<failure`/`<error` anywhere in the report. Frame critique round 3 showed a
   passing test that prints such text would be read as red, so the wrapper
   reads the `<testsuite>` header counts (`tests=`, `failures=`, `errors=`).
   The compliance review then showed `grep -o` over the whole file still
   picks up a `<testsuite …>` tag inside captured output, so it now reads
   only the first `<testsuite` tag of each file. The noisy stub case prints a
   full `<testsuite tests="9" failures="3">` tag in captured output; reading
   every match instead of the first turns it red (mutation-checked).
4. **Staleness mechanism pinned** (frame critique, round 1): the wrapper
   deletes the task's `TEST-*.xml` before calling Gradle. That this also
   stops Gradle skipping the task as up to date is recorded as an unprobed
   assumption that fails closed (no report → exit 2), and the recipe names
   the `clean<TaskName>` rule as the fallback.
5. **Recipe shape beyond the ACs.** The wrapper reads `JIG_GRADLE_TASK`,
   `JIG_GRADLE_RESULTS` and `JIG_GRADLEW` (with defaults), so a project sets
   its Android variant task and report directory without editing the
   script. The document also covers what the ACs did not ask for but the
   contract needs: crash-class regression tests (map the crash to 1),
   runners whose failing-test status is not 1 (`cargo test`, `make`),
   wrapper crashes, and skipped tests counting as green.
6. **ADR links.** The recipes document links ADR-0068 by GitHub URL, since
   `docs/` does not ship in the host packages. The SKILL.md files keep the
   repository-relative link used by every other ADR reference in skill
   prose; a dangling link there is an existing pattern, not new here.
7. **Review findings folded in.** Compliance (`pass`): the `<testsuite>`
   capture (item 3); "the list is closed" added to `adoption-readiness.md`
   and its template; the end-to-end test now filters `JIG_GRADLE*` /
   `STUB_*`. Craft (`pass`) nits: the hint said "line 1" (now "first
   non-comment line"); the skip guard uses `shutil.which("sh")`; the
   near-vacuous `assertNotIn` on old wording was replaced; a long line in
   `skills/bug-fix/SKILL.md` was split.
8. **Red before green.** The no-runner hint tests and the `bug.py` no-runner
   gate test failed before `_report_no_runner` existed (3 failures). The
   recipe tests were written with the recipe; five targeted mutations of the
   wrapper (no stale delete, trust Gradle's exit, no ran-check, final exit 1,
   unmapped selector) each turned at least one recipe test red.
9. **No real Gradle.** jig has no Gradle; the recipe is tested against a stub
   `gradlew` only, and both the recipe and ADR-0068 say so.

### Reconciliation sweep

Record the drift-prone surfaces checked during reconciliation. The transition
gate only requires this subsection to exist; the reconciliation reviewer judges
whether coverage and rationales are honest.

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `README.md` | `no-op` | Checked: the front door names `tdd-loop` but states no runner list or exit contract. |
| `docs/specs/README.md` | `updated` | Regenerated by `workflow.py status-board`. |
| `docs/architecture.md` | `no-op` | Checked: lists `tdd.py` / `land.py` as helpers only; no exit contract or runner list to correct. Module boundaries unchanged. |
| Primer surfaces: `CLAUDE.md` / `AGENTS.md` / scaffold templates | `no-op` | `CLAUDE.md` is left alone to keep the primer byte budget (spec 122-03 precedent); the per-slice invariants go to the status-board Notes column. The scaffold template change is in 123-02's row. |
| `docs/inbox.md` | `no-op` | Checked: no parked item about runners or the test command. |
| `docs/memory/**` | `no-op` | Checked: the glossary has no runner-list entry. The durable facts live in ADR-0068 and the tdd-loop SKILL.md. |
| `docs/decisions/README.md` / ADR index | `updated` | ADR-0068 added and accepted; index regenerated by `adr.py index`, `check-index` clean. |
| `docs/bugs/**` | `updated` | Bugs 042 (built-in runners read a load failure as red) and 043 (`REVIEWED` reopens on an environment error) filed; board regenerated, `check-board` clean. |
| Generated host packages (`hosts/**`) | `updated` | Rebuilt by `scripts/build_host_packages.py`; `--check` clean. |
| `docs/product-vision.md` | `updated` | The "polyglot runner support … add others when a real project hits the gap" out-of-scope line now states the closed list and the command contract. |
| `docs/adoption-readiness.md` + `templates/docs/adoption-readiness.md.template` | `updated` | Test-command item names the four built-ins, says the list is closed, and states the exit contract. |
| `docs/refinement-todo.md` | `updated` | New demand-gated entry: a generic JUnit-XML report reader (ADR-0068 Option C), with its trigger. |
| `skills/tdd-loop/SKILL.md`, `skills/bug-fix/SKILL.md`, `skills/tdd-loop/test-command-recipes.md` | `updated` | Policy, contract, dead-end guidance and the Gradle recipe. |
