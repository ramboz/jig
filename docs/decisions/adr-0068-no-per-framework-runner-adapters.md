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
the same three-state contract as `tdd.py`: only exit 1 is a failing test.

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
  that knows its build tool writes the mapping in its own repo, against the
  real tool, where it can test it. A command *can* now be sound on any stack.
- **Cons:** The cost Option A lists (report reading, task names, stale
  reports) does not go away; it moves to each consuming project. A Gradle
  project has to write (or copy and adapt) a wrapper before the bug-fix gates
  work. Soundness is per command, not automatic: a bare build-tool command
  that exits 1 for a compile failure is still read as red. Statuses other
  than 0 and 1 change meaning for existing custom commands (see
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

### Option F: Three states, but every unlisted non-zero status stays red
Add exit 2 = "could not run" and keep reading 3, 101, 126, 127 and signal
deaths as red, for backward compatibility.
- **Pros:** Runners with their own failure codes (`cargo test` exits 101)
  keep working with no wrapper.
- **Cons:** The conventional "could not run" statuses stay red: a shell
  wrapper exits 127 when a tool is missing and 126 when it is not executable,
  and a killed process returns 137 or a negative status. Every recipe is a
  shell wrapper, so the commonest environment failure would still be a
  witnessed failing test. Each status that stays red fails open at `FIXING`;
  each status moved to "could not run" fails closed. Raised by the frame
  critique of this ADR (2026-11-20) against an earlier draft that chose it.

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
   - `1` — a test ran and failed (red). This is the only status read as red.
   - any other status — the tests could not be run (environment error):
     `tdd.py run` exits 2 and names the status it saw. `2` is the status a
     wrapper should use on purpose for a build or compile failure, a missing
     tool, or a selector that matched no test; 126, 127, a runner-specific
     code and death by signal land in the same place. None of them is
     evidence of red.
   This applies to both the selector branch and the whole-suite branch.
   The contract makes a sound command possible; it does not make every
   command sound. A command is only as good as its exit 1: a build tool that
   exits 1 for a compile failure (Gradle, Maven) needs a wrapper that checks
   a test really ran and failed before it exits 1.
   **Both consumers of the exit code treat "could not run" as a refusal.**
   `bug.py` already refuses a `tdd.py` exit 2 at `FIXING`. `slice-land`
   (`land.py check_tests`) mapped every exit 2 to its non-blocking "no test
   runner detected (slice may be doc-only)" warning; it now asks `tdd.py
   detect` and blocks when a runner exists but could not run. Without that,
   this decision would turn a failing `make test`, or a wrapper correctly
   reporting a broken build, from a land blocker into a soft warning.
3. **The dead end names the way out.** When no runner is detected,
   `tdd.py detect` / `run` (and so the `bug.py` gate error, which quotes the
   last line) name `.jig/test-command`, the `{test}` placeholder and the
   0/1/2 contract.
4. **One recipe, not runtime code.** A recipes document shipped beside the
   skill carries one worked example: a Gradle JVM-unit-test wrapper script
   that lives in the consuming project. jig does not ship or run the wrapper.
   The example shows the shape; the document is not a catalogue, and a
   request to add a recipe per framework is declined the same way an adapter
   is.
   Android instrumented tests (device or emulator) are out of scope for jig;
   a project wires them through the same contract if it wants them gated.

## Consequences

**Becomes easier:**
- Any stack can make the bug-fix gates sound with a small script it owns.
- A runner request has one answer, and `detect` prints it.
- A wrapper can refuse to vouch for a run, and a wrapper that breaks (missing
  tool, killed process) is not mistaken for a failing test.

**Becomes harder:**
- **Existing custom commands whose failing-test status is not 1 change from
  red to environment error.** Known cases: GNU `make` exits 2 when a recipe
  fails (probed 2026-11-20), so `make test` is affected; `cargo test` exits
  101; runners that exit with the count of failed tests (mocha) are affected
  whenever that count is not 1. The change fails closed: `FIXING` refuses
  instead of accepting, the `REVIEWED` green check refuses as before, and the
  message names the status and the contract. The fix is a wrapper that exits
  1 only when a test ran and failed. A blanket `|| exit 1` is **not** the
  fix: it turns a build failure back into red, which is the defect this
  decision removes.
- Statuses that already mean "could not run" are now read correctly: pytest
  exits 2 on a collection error and 4 when nothing matched, `sh` exits 2 on a
  syntax error, `argparse` exits 2 on a usage error (all probed). jig's own
  command, `python3 scripts/run_tests.py {test}`, exits only 0 or 1 from its
  result paths.
- `slice-land` now blocks on any detected runner that could not run. That
  includes built-in cases which exited 2 before this decision and were shown
  as the doc-only warning (pytest module not installed, runner binary
  missing): they were soft warnings and become blockers.
- A Gradle (or Maven, Go, Rust…) project has a setup step before the bug-fix
  gates work, and owns the correctness of its wrapper.
- A bare command that exits 1 for everything is as unsound as before. jig
  cannot detect that; the no-runner message and the recipe say what exit 1
  must mean.

## Assumptions

- **mocha's exit status is its failure count and `cargo test` exits 101 on a
  failing test (not probed here).** Taken from the tools' documented
  behaviour; neither is installed in this environment. Used only as examples
  of affected commands, not as a basis for the decision.
- **The Gradle recipe is not run against real Gradle here.** No Gradle is
  installed in jig's environment. The recipe's exit-code logic is exercised
  against a stub `gradlew`, which encodes the author's reading of Gradle, not
  Gradle. The recipe says so, and names the task and the report location as
  things the project must set. Its fit to a real Android project is for the
  consuming project to confirm.

## Kill criteria

- Several unrelated projects ship near-identical wrappers for the same tool
  and still get the exit mapping wrong. That is the demand signal for Option C
  (a generic report reader), not for per-framework adapters.
- The exit-status change blocks existing users whose runner has no way to
  tell "a test failed" from "could not run" (so no honest wrapper can be
  written for it).
- A false red at `FIXING` is silent, so the first criterion will not trip by
  itself: if a bug record is found whose `red_confirmed_at` was stamped on a
  test that never ran through a custom command, revisit whether exit status
  alone is enough.

## Open questions

None.
