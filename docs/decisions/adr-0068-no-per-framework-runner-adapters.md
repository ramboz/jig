---
status: Proposed
dependencies: []
last_verified: 2026-11-20
frame_review: true
---

# ADR-0068: The custom test command is the runner extension point

## Status

Proposed (2026-11-20)

## Context

jig does not add a built-in test-runner adapter for Gradle or for any other
framework it does not use itself; a project on another stack connects its
tests through `.jig/test-command`, and that command's exit code now follows
the same three-state contract as `tdd.py`.

`skills/tdd-loop/tdd.py` drives the test runner for `tdd-loop` and for the
bug-fix gates: `bug.py` shells to `tdd.py run --test <selector>` and needs a
witnessed red (exit 1) to enter `FIXING` and a witnessed green (exit 0) to
enter `REVIEWED`. `detect_runner` knows four built-in runners (pytest, vitest,
jest, `node --test`) plus the custom command file `.jig/test-command`
(slice 006-05), whose `{test}` placeholder marks where a selector goes
(bug 021).

[Issue 250](https://github.com/ramboz/jig/issues/250) reports that on an
Android/Kotlin Gradle project `tdd.py detect` finds nothing, so the bug-fix
gates cannot run, and asks for a Gradle adapter. The request is reasonable for
one project, and it is the first of many: Maven, `go test`, `cargo test`,
RSpec, PHPUnit, `dotnet test`, Bazel and others have the same standing.
`docs/product-vision.md` already listed polyglot runner support as out of
scope, with "add others when a real project hits the gap". A real project has
now hit the gap, so that sentence has to be decided one way or the other.

Two facts about the existing custom-command path make it unfit as the answer
today (both read from `tdd.py` at `87610a93`):

1. `cmd_run` returns `0 if returncode == 0 else 1` for a custom command, in
   both the selector branch and the whole-suite branch. Any non-zero exit is
   red. Gradle exits 1 for a compile failure, so a regression test that never
   compiled would be accepted as a witnessed failing test at `FIXING`. A
   project wrapper script has no way to say "I could not run the tests".
2. When no runner is detected, the message is `no test runner detected at
   <target>` and nothing else. Neither it nor the `bug.py` gate error names
   `.jig/test-command`, so the user is not told the way out.

The owner's direction (2026-11-20, in the session that drafted this ADR): no
Gradle adapter, no adapter per framework, and a minimal change that does not
invite a request per framework.

## Decision Options Considered

### Option A: Add a built-in Gradle adapter (what issue 250 asks for)
- **Pros:** Works with no project setup on the commonest JVM build tool.
- **Cons:** Gradle exits 1 for compile failures, failing tests and unmatched
  filters alike, so a sound adapter has to read JUnit XML reports, know the
  task names (`test`, `testDebugUnitTest`, per-module tasks), map selectors to
  `--tests`, and decide what to do about instrumented tests that need a
  device. jig's own suite cannot exercise any of it (no JVM project, no
  Gradle in CI), so it would ship untested against the real tool, the same
  position the vitest/jest paths are already in. And it sets the precedent:
  every other framework has the same claim.

### Option B: No new adapters; make the custom command a sound contract
Keep the built-in runners at the ones jig dogfoods or already ships. Give a
custom command three exit states, tell the user about the file when detection
finds nothing, and ship one worked recipe.
- **Pros:** One small, stable interface instead of N adapters. The project
  that knows its build tool writes the ten-line mapping, in its own repo,
  where it can test it. jig's gates become sound for every stack at once.
- **Cons:** A Gradle project has to write (or copy) a wrapper before the
  bug-fix gates work. Exit 2 changes meaning for existing custom commands (see
  Consequences).

### Option C: A generic JUnit-XML reader in jig
jig runs the project's command, then reads JUnit XML reports to decide
green / red / nothing ran.
- **Pros:** Covers Gradle, Maven and several others with one mechanism.
- **Cons:** Still needs per-tool knowledge of where reports land and how to
  clear stale ones; a second result channel beside the exit code; nobody has
  asked for it beyond this one issue. Recorded in `docs/refinement-todo.md` as
  demand-gated.

### Option D: Opt-in three-state contract (a marker in `.jig/test-command`)
Keep "any non-zero is red" by default; a marker line switches a command to the
0/1/2 contract.
- **Pros:** No behaviour change for any existing command.
- **Cons:** The default stays unsound, two contracts have to be documented
  and tested, and the dead-end message has to explain both. The behaviour
  change it avoids fails closed and names its own fix (see Consequences).

### Option E: Status quo plus documentation only
- **Pros:** No code change.
- **Cons:** Leaves fact 1: the documented extension point accepts a build
  failure as a failing test.

## Recommended Decision

**Option B.**

1. **No per-framework adapters.** The built-in runners are pytest, vitest,
   jest and `node --test`, and the list is closed: pytest (through jig's own
   `scripts/run_tests.py` custom command and the `tdd.py` subprocess test) is
   the one jig dogfoods; the three JavaScript runners shipped before this
   decision and stay as they are. A request to add a runner is answered with
   the command contract, not with an adapter.
2. **`.jig/test-command` is the extension point, with the same exit contract
   as `tdd.py run`:**
   - `0` — the tests ran and passed (green).
   - `1` — the tests ran and at least one failed (red).
   - `2` — the tests could not be run: build or compile failure, missing
     tool, no test matched. `tdd.py run` reports exit 2 (environment error)
     and says the command exited 2. It is not evidence of red.
   - any other non-zero status (including death by signal) — red, as today.
     Runners that use their own failure codes (for example `cargo test`'s 101)
     keep working unchanged.
   This applies to both the selector branch and the whole-suite branch.
3. **The dead end names the way out.** When no runner is detected,
   `tdd.py detect` / `run` (and so the `bug.py` gate error, which quotes the
   last line) name `.jig/test-command`, the `{test}` placeholder and the
   0/1/2 contract.
4. **One recipe, not runtime code.** A recipes document shipped beside the
   skill carries one worked example: a Gradle JVM-unit-test wrapper script
   that lives in the consuming project. jig does not ship or run the wrapper.
   Android instrumented tests (device or emulator) are out of scope for jig;
   a project wires them through the same contract if it wants them gated.

## Consequences

**Becomes easier:**
- Any stack can make the bug-fix gates sound with a small script it owns.
- A runner request has one answer, and `detect` prints it.
- A wrapper can refuse to vouch for a run (exit 2), so `FIXING` cannot be
  entered on a test that never executed.

**Becomes harder:**
- **Existing custom commands that exit 2 when tests fail change from red to
  environment error.** Probed 2026-11-20: GNU `make` exits 2 when a recipe
  fails, so `make test` is affected; runners that exit with the count of
  failed tests (mocha does, by design) are affected when exactly two tests
  fail. The change fails closed: `FIXING` refuses instead of accepting, the
  `REVIEWED` green check refuses as before, and the message names the fix
  (wrap the command so a test failure exits 1, e.g.
  `sh -c "make test || exit 1"`). Codes that already mean "could not run" are
  now read correctly: pytest exits 2 on a collection error, `sh` exits 2 on a
  syntax error, `argparse` exits 2 on a usage error (all probed). jig's own
  command, `python3 scripts/run_tests.py {test}`, exits only 0 or 1 from its
  result paths.
- A Gradle (or Maven, Go, Rust…) project has a setup step before the bug-fix
  gates work.
- A wrapper that exits 1 for everything is as unsound as before; the contract
  is only as good as the wrapper. The recipe shows the report check.

## Assumptions

- **mocha's exit status is its failure count (not probed here).** Taken from
  mocha's documented behaviour; mocha is not installed in this environment.
  Used only as an example of an affected command, not as a basis for the
  decision.
- **The Gradle recipe is not run against real Gradle here.** No Gradle is
  installed in jig's environment. The recipe's exit-code logic is exercised
  against a stub `gradlew`; its fit to a real Android project is for the
  consuming project to confirm.

## Kill criteria

- Several unrelated projects ship near-identical wrappers for the same tool
  and still get the exit mapping wrong. That is the demand signal for Option C
  (a generic report reader), not for per-framework adapters.
- The exit-2 change breaks existing users in a way the message does not let
  them fix in one step.

## Open questions

None.
