---
status: DONE
skill: tdd-loop
use_cases: [UC-5, UC-8]
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 123: Custom-test-command contract

> Reserved on 2026-11-20 via `workflow.py new --no-push` (local provisional — the
> number is not yet on `origin/main`).

## Overview

[Issue 250](https://github.com/ramboz/jig/issues/250) reports that
`tdd.py detect` finds no runner on an Android/Kotlin Gradle project, which
blocks the bug-fix gates (`bug.py` needs `tdd.py` to witness the regression
test red at `FIXING` and green at `REVIEWED`), and asks for a Gradle adapter.

[ADR-0068](../../decisions/adr-0068-no-per-framework-runner-adapters.md)
decides against a Gradle adapter and against any adapter per framework. The
custom command file `.jig/test-command` is the extension point. This spec
makes that extension point sound and findable:

1. **Contract.** Today any non-zero exit from a custom command is read as red,
   so a wrapper cannot report "I could not run the tests", and a missing
   tool inside a shell wrapper (exit 127) is a witnessed failing test. Now
   only exit 1 is red; every other non-zero status is an environment error.
   `slice-land` reads the same exit code, so it is taught to block on "could
   not run" instead of showing its doc-only warning.
2. **Dead end.** When no runner is detected, the message names the file, the
   `{test}` placeholder and the exit contract.
3. **Policy and recipe.** The docs state the closed built-in list and carry
   one worked Gradle wrapper for the consuming project to copy.

No new built-in runner, no Maven, no JUnit-XML reader in jig.

## Decisions

- **D1 — only exit 1 is red; every other non-zero status is "could not
  run".** ADR-0068 §2 (Option F, "other non-zero stays red", was rejected
  after the ADR's frame critique). Commands whose failing-test status is not
  1 (`make`, `cargo test`, failure-count runners) change from red to
  environment error; the change fails closed at `FIXING`, and the message
  names the status and the contract. The contract makes a sound command
  possible, not automatic: a bare build-tool command that exits 1 on a
  compile failure is still read as red.
- **D4 — `slice-land` blocks when a detected runner could not run.**
  `land.py check_tests` maps every `tdd.py run` exit 2 to `warn` ("no test
  runner detected (slice may be doc-only)"), which does not block. Before
  this spec a custom command's exit 2 reached it as red. To keep the land
  gate closed, exit 2 is split with `tdd.py detect`: no runner → `warn` as
  today; a runner was detected but could not run → a new blocking status.
  This also covers the built-in cases that already exit 2 with a runner
  present (pytest module missing, runner binary missing, unresolved
  selector), which were shown as the doc-only warning until now.
- **D2 — the hint is the last stderr line and fits `bug.py`'s quote.**
  `bug.py` quotes the last non-blank stderr line of a failed `tdd.py` run, up
  to 300 characters (`_tdd_failure_detail`). Keeping the guidance on one last
  line of at most 300 characters carries it into the gate error with no
  change to `bug.py`.
- **D3 — the recipe ships beside the skill, as a document.** Skill
  directories ship whole in the host packages (minus `test_*.py`), so
  `skills/tdd-loop/test-command-recipes.md` reaches a consuming project's
  agent. The wrapper script inside it is documentation; a jig test runs it
  against a stub `gradlew` so the documented logic cannot rot.

## Assumptions

- **A1 — the built-in pytest / vitest / jest / node paths are not changed
  here.** They read a test file that cannot be loaded as red (node probed;
  pytest on a whole-suite run; vitest and jest not probed). Filed as
  [bug 043](../../bugs/043-builtin-runners-read-load-failure-as-red.md), not
  fixed in this spec (owner's instruction).
- **A3 — the `REVIEWED` green check is not changed here.** It routes any
  non-zero `tdd.py` exit, including an environment error, back to
  `DIAGNOSING`. Filed as
  [bug 044](../../bugs/044-reviewed-gate-env-error-reopens-bug.md): the
  back-edge is bug-lifecycle behaviour (ADR-0016) pinned by a bug 021 test.
- **A2 — the recipe is not run against real Gradle.** No Gradle is installed
  in jig's development or CI environment. The stub-`gradlew` test covers the
  wrapper's own logic (exit mapping, report reading, selector mapping), not
  Gradle's behaviour.

## Decomposition

SPIDR: split by **Rules** then **Interfaces**.

- **123-01 (Rules):** the exit rule on the custom-command path, both
  branches, `tdd.py`'s own failure paths, and two of the three places the
  exit code is read: the bug-fix `FIXING` gate refuses it and `slice-land`
  blocks on it. The third, the `REVIEWED` green check, is bug 044.
- **123-02 (Interfaces):** what the user sees and reads — the no-runner
  message, the policy in the docs, the recipes document.

No spike: the code paths and exit codes were read and probed while drafting
ADR-0068.

## Slices

- [123-01 — exit-contract](slice-01-exit-contract.md)
- [123-02 — dead-end-policy-recipe](slice-02-dead-end-policy-recipe.md)
