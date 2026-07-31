---
status: REPORTED
tier: standard
severity: medium
claimed_by: claude/bug-021-tdd-selector-gate
regression_test:
main_repro_checked_at:
main_repro_ref:
main_repro_result:
red_confirmed_at:
green_confirmed_at:
fix_class:
security_surface: false
escalated_to:
---

# Bug 021: custom-test-command-drops-selector

> Filed from a side-observation while fixing
> [bug 020](020-adr-index-summary-degradation.md) /
> [issue #140](https://github.com/ramboz/jig/issues/140). Record only — not
> diagnosed, not fixed.

## Symptom

`tdd.py run <target> --test <selector>` silently runs the **whole suite** when
the project uses a custom `.jig/test-command` whose command does not accept a
selector argument — which is jig's own configuration. Nothing reports that the
selector was dropped.

`bug.py transition <id> FIXING` then reads that whole-suite exit code as a
statement about the named regression test:

- **Red gate (`FIXING`)** — "the regression test fails without a fix, so it
  captures the bug". In fact **any** failure anywhere in the suite satisfies
  it. The gate stamps `red_confirmed_at` on evidence that may have nothing to
  do with the test.
- **Green gate (`REVIEWED`)** — requires the *whole suite* to pass. Stricter
  than intended, so not unsafe, but it makes the gate fail for unrelated
  reasons and pushes sessions toward the `JIG_BUG_TEST_GATE=0` escape.

Observed live on 2026-07-30 during bug 020: the FIXING transition passed while
the named regression test was already **green** (the fix was in place). The
non-zero exit came from `uvx pyright` flagging type errors in the new code.
The record was stamped with a red that the gate had not actually witnessed.

## Repro

In the jig repo itself (`.jig/test-command` is `python3 scripts/run_tests.py`):

```bash
# Pick any single passing test class. The selector is ignored — this runs all
# ~3700 tests, takes ~2 minutes, and never mentions the selector.
python3 skills/tdd-loop/tdd.py run . --test "skills/adr-workflow/test_adr.py::SomeClass" < /dev/null

# Confirm what actually got spawned (from another shell while it runs):
ps -o command= -p $(pgrep -f run_tests.py | head -1)
# → python3 scripts/run_tests.py skills/adr-workflow/test_adr.py::SomeClass
#   ...the argument is present and ignored.
```

Gate consequence: with a green regression test and any unrelated failure in the
suite, `bug.py transition <id> FIXING` succeeds and stamps `red_confirmed_at`.

## Evidence

Three sites, verified on `origin/main@af8184c`:

- `skills/tdd-loop/tdd.py:363` — the custom-command branch appends the selector
  unconditionally: `argv = [*argv, test_selector]`. There is no check that the
  command supports one, and no warning when it cannot be honored.
- `scripts/run_tests.py:162` — `main()` takes no arguments and never reads
  `sys.argv`; it always builds the full suite. The appended selector is
  discarded without an error.
- `skills/bug-fix/bug.py:582` (`_run_tdd`) and `:690` — the transition gates
  interpret the resulting exit code as a verdict on the *named* test.

`skills/tdd-loop/SKILL.md` documents `.jig/test-command` as "the exact command
to run" and names `python3 scripts/run_tests.py` (jig itself) as the example.
It never states that the command must also accept a trailing selector, so this
is an undocumented requirement rather than a mis-configuration — every
downstream project whose custom command is a whole-suite script inherits the
same hole.

**Observed twice before and never recorded as a defect:**

- `docs/bugs/004-terminal-status-legibility.md:181` — Learning section, tooling
  note: "the `.jig/test-command` runner ignores the appended selector and runs
  the full suite + `uvx pyright`, so the red→green gate here is repo-wide."
- `docs/bugs/007-unregistered-plugin-skill-contract.md:102` — that session
  reached `REVIEWED` via the deliberate `JIG_BUG_TEST_GATE=0` escape because the
  whole-suite command failed for an unrelated reason (`uvx` sandbox).

## Hypotheses

<!-- Anti-anchoring: >=2 candidates, mark the leading one. -->
- [ ] H1: this is a configuration problem in jig's own repo, not a jig defect —
      `.jig/test-command` should point at a selector-aware command and the
      helpers are fine. Weak: it does not explain downstream projects, since
      `tdd.py` appends a selector to *any* custom command and `SKILL.md` never
      requires the command to accept one. Falsify by scaffolding a project whose
      custom command is a whole-suite script and checking whether anything warns.
- [x] H2 (leading): the defect is a missing signal, not a missing feature —
      `tdd.py` returns an exit code that cannot distinguish "the named test is
      red" from "the runner could not target and something else is red", and
      `bug.py` consumes it as though it could. Confirm by checking whether any
      code path reports targeted-vs-full-suite; if none exists, the gate has
      never been able to make the distinction it claims.

## Root cause

_Not yet diagnosed — filed as a record. See Hypotheses._

## Fix class

_TBD. Likely `structural_fix` (the runner must report whether it targeted) plus
a `local_patch` letting `scripts/run_tests.py` accept an optional selector._

## Fix

_Not written._ Direction, for whoever picks this up: teaching
`scripts/run_tests.py` to honor a selector fixes jig's own repo but not the
general case. The load-bearing change is that `tdd.py` must be able to say "I
could not target this test", and `bug.py`'s red gate must refuse that answer as
evidence rather than reading the exit code as a verdict on one test.

## Already tried

Nothing — filed on first observation.

## Regression test

_None yet._ A regression test should cover both halves: a custom command that
ignores the selector is reported rather than silently accepted, and the FIXING
gate refuses to stamp `red_confirmed_at` from an untargeted run.

## Proof

_N/A — no fix yet._ Symptom evidence is in ## Evidence and ## Repro above.

## Learning

_Pending diagnosis._ Provisional: a gate that consumes a process exit code
inherits every assumption that code makes. `tdd.py`'s exit code answers "did
the command succeed?", while the bug lifecycle asks "did this named test fail?"
— two different questions with the same numeric answer, which is how a
teeth-not-trust gate ended up attesting something it never checked.
