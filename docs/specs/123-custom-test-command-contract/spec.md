---
status: DRAFT
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
   so a Gradle compile failure (exit 1 from Gradle, but any wrapper has the
   same problem) would be accepted as a witnessed failing test, and a wrapper
   cannot report "I could not run the tests". A custom command that exits 2
   is now an environment error.
2. **Dead end.** When no runner is detected, the message names the file, the
   `{test}` placeholder and the exit contract.
3. **Policy and recipe.** The docs state the closed built-in list and carry
   one worked Gradle wrapper for the consuming project to copy.

No new built-in runner, no Maven, no JUnit-XML reader in jig.

## Decisions

- **D1 — exit 2 is "could not run"; every other non-zero code stays red.**
  ADR-0068 §2. Commands that exit 2 for failing tests (`make`, and runners
  that exit with a failure count) change from red to environment error; the
  change fails closed and the message names the one-line fix.
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

- **A1 — the built-in vitest / jest / node paths are not changed here.**
  Whether they read a compile or syntax failure as red is checked during
  implementation and, if real, filed on the bug board, not fixed in this spec.
- **A2 — the recipe is not run against real Gradle.** No Gradle is installed
  in jig's development or CI environment. The stub-`gradlew` test covers the
  wrapper's own logic (exit mapping, report reading, selector mapping), not
  Gradle's behaviour.

## Decomposition

SPIDR: split by **Rules** then **Interfaces**.

- **123-01 (Rules):** the exit-2 rule on the custom-command path, both
  branches, and proof that the bug-fix `FIXING` gate refuses it.
- **123-02 (Interfaces):** what the user sees and reads — the no-runner
  message, the policy in the docs, the recipes document.

No spike: the code paths and exit codes were read and probed while drafting
ADR-0068.

## Slices

- [123-01 — exit-contract](slice-01-exit-contract.md)
- [123-02 — dead-end-policy-recipe](slice-02-dead-end-policy-recipe.md)
