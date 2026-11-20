# Test-command recipes

How to connect a test runner jig does not auto-detect, using
`.jig/test-command`. Decision record:
[ADR-0068](../../docs/decisions/adr-0068-no-per-framework-runner-adapters.md).

jig auto-detects four runners: pytest, vitest, jest and `node --test`. That
list is closed. Every other stack (Gradle, Maven, Go, Rust, .NET, Ruby…)
uses the command contract below. This document holds **one** worked example to
show the shape. It is not a catalogue: jig does not collect a recipe per
framework, for the same reason it does not ship an adapter per framework.

## The contract

Create `<project>/.jig/test-command`. Its first non-blank, non-comment line is
the command `tdd.py run` executes, from the project root, without a shell
(use `sh -c "..."` or a script if you need one).

- **Selector.** Put `{test}` as its own argument where a single-test selector
  belongs. `tdd.py run --test <selector>` substitutes it; without a selector
  the token is dropped and the whole suite runs. Without a `{test}` token a
  targeted run is refused (jig will not run the whole suite and call it a
  verdict on one test).
- **Exit status.**

  | Exit | Meaning | `tdd.py run` reports |
  |------|---------|----------------------|
  | `0` | the tests ran and passed | 0 (green) |
  | `1` | a test ran and failed | 1 (red) |
  | anything else | the tests could not be run | 2 (environment error) |

  Use `2` on purpose for a build or compile failure, a missing tool, or a
  selector that matched no test. A shell's 126/127 and a killed process land in
  the same place.

**Exit 1 is a claim: "a test ran and failed".** The bug-fix `FIXING` gate
records a witnessed failing test on it. jig cannot check the claim, so the
command has to be honest:

- A build tool that exits 1 for a compile failure (Gradle, Maven) is **not**
  sound as a bare command. `./gradlew test --tests {test}` will report a
  regression test that never compiled as a failing test. Use a wrapper that
  looks at what actually ran.
- Do not "fix" a non-1 failure status with a blanket `|| exit 1`. That turns
  every build failure into a failing test.
- A wrapper that crashes with status 1 (an uncaught exception in a Python or
  Node script, `set -e` in a shell script) makes the same false claim. Catch
  your own failures and exit 2.
- If your runner's failing-test status is not 1 (`cargo test` exits 101, GNU
  `make` exits 2, some runners exit with the failure count), map that one
  status to 1 in a wrapper and let everything else through.

## Worked example: Gradle JVM unit tests

A wrapper script that lives **in your project** (for example
`scripts/jig-gradle-test.sh`). jig does not ship or run it; copy it, adapt it,
and commit it with your code.

`.jig/test-command`:

```text
sh scripts/jig-gradle-test.sh {test}
```

`scripts/jig-gradle-test.sh`:

<!-- recipe:gradle-wrapper -->
```sh
#!/bin/sh
# Run Gradle JVM unit tests under jig's test-command contract.
#   0 = tests ran and passed   1 = a test ran and failed   2 = could not run
# Usage: jig-gradle-test.sh [selector]
#   selector: pkg.Class  or  pkg.Class::method  (passed to --tests)

# --- settings: check these against YOUR build --------------------------------
# The test task. In a multi-module build name the module, and on Android the
# variant, e.g. :app:testDebugUnitTest.
TASK="${JIG_GRADLE_TASK:-test}"
# The directory that task writes its JUnit XML (TEST-*.xml) into,
# e.g. app/build/test-results/testDebugUnitTest.
RESULTS="${JIG_GRADLE_RESULTS:-build/test-results/test}"
GRADLEW="${JIG_GRADLEW:-./gradlew}"
# ------------------------------------------------------------------------------

if [ ! -x "$GRADLEW" ]; then
  echo "jig-gradle-test: $GRADLEW not found or not executable" >&2
  exit 2
fi

# Delete this task's earlier reports, so the verdict below can only come from
# this run. (Removing a task's outputs should also stop Gradle skipping it as
# up to date; if your build still skips it, run the clean<TaskName> rule first.)
if [ -d "$RESULTS" ]; then
  find "$RESULTS" -type f -name 'TEST-*.xml' -exec rm -f {} +
fi

if [ -n "${1:-}" ]; then
  filter=$(printf '%s' "$1" | sed 's/::/./')
  "$GRADLEW" "$TASK" --tests "$filter"
else
  "$GRADLEW" "$TASK"
fi
status=$?

reports=""
if [ -d "$RESULTS" ]; then
  reports=$(find "$RESULTS" -type f -name 'TEST-*.xml')
fi
if [ -z "$reports" ]; then
  echo "jig-gradle-test: no JUnit report in $RESULTS (gradle exit $status):" \
       "the build failed, the task was skipped, or no test matched" >&2
  exit 2
fi

ran=$(find "$RESULTS" -type f -name 'TEST-*.xml' -exec grep -c '<testcase' {} + |
      awk -F: '{ n += $NF } END { print n + 0 }')
if [ "$ran" -eq 0 ]; then
  echo "jig-gradle-test: the reports hold no test case: no test ran" >&2
  exit 2
fi

failed=$(find "$RESULTS" -type f -name 'TEST-*.xml' \
         -exec grep -l -E '<(failure|error)[ >/]' {} +)
if [ -n "$failed" ]; then
  exit 1
fi
if [ "$status" -eq 0 ]; then
  exit 0
fi
echo "jig-gradle-test: gradle exit $status but no test failed:" \
     "a build or configuration error" >&2
exit 2
```

What it does:

- **Selector.** `com.example.FooTest::rejectsEmptyInput` becomes
  `--tests com.example.FooTest.rejectsEmptyInput`; `com.example.FooTest` runs
  the class. Use that form for a bug record's `regression_test:`.
- **Red only on evidence.** It exits 1 only when a JUnit XML report written by
  this run holds a `<failure>` or `<error>` element. Gradle's own exit status
  is not trusted to mean "a test failed".
- **Could not run → 2.** No report (compile failure, skipped task, no match),
  reports with no test case, or a Gradle failure with no failing test.
- **Environment.** `JAVA_HOME`, `ANDROID_HOME` and the rest are inherited from
  the environment `tdd.py` runs in; nothing is hard-coded.

Limits you need to know:

- **jig has not run this against real Gradle.** jig's own test suite runs the
  script against a stub `gradlew`, which checks the script's logic (exit
  mapping, report reading, selector mapping), not Gradle's behaviour. Try it
  on your project: a passing test, a failing test, a test that does not
  compile, and a selector that matches nothing should give 0, 1, 2 and 2.
- **Set `TASK` and `RESULTS` for your build.** The defaults fit a single-module
  JVM project. With the wrong directory the script finds no report and exits 2
  on every run (it fails closed). In a multi-module build a root-level task
  with `--tests` fails in every module that has no match, so name the module's
  task.
- **A test that is skipped** (`@Ignore`, `@Disabled`) counts as a test case
  that did not fail, so a run whose only selected test is skipped is green.
- **Android instrumented tests** (`src/androidTest`, `connected…AndroidTest`,
  needing a device or emulator) are out of scope for jig. If you want them
  behind the bug-fix gates, wire them through the same contract in your own
  wrapper: same three exit meanings, your own way of deciding them.
