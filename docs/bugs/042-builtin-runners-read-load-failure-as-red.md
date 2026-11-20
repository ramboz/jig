---
status: REPORTED
tier:
severity: medium
claimed_by:
regression_test:
main_repro_checked_at:
main_repro_ref:
main_repro_result:
red_confirmed_at:
green_confirmed_at:
fix_class:
security_surface: false
escalated_to:
closure_schema: 1
---

# Bug 042: builtin-runners-read-load-failure-as-red

Reported: found while implementing spec 123 (issue 250), 2026-11-20. Not fixed there by the owner's instruction.

## Symptom

On the built-in runner paths `tdd.py run` reports exit 1 (red) for a test
file that could not be loaded (syntax error, missing import), so the bug-fix
`→ FIXING` gate can stamp `red_confirmed_at` on a regression test that never
ran. Spec 123 / ADR-0068 closed this for custom commands (only exit 1 is red,
and a wrapper can exit 2); the built-in paths still use
`return 0 if returncode == 0 else 1` (`_run_command`).

## Repro

Probed 2026-11-20 on the spec 123 branch (Node v22.23.5):

```bash
mkdir p && cd p && echo '{"scripts":{"test":"node --test"}}' > package.json
printf "import { test } from 'node:test';\nimport './missing-module.mjs';\ntest('x', () => {});\n" > a.test.mjs
python3 <jig>/skills/tdd-loop/tdd.py run . --test "a.test.mjs::x"; echo $?   # 1 (red)
```

The same exit 1 comes from a test file with a syntax error, with and without
`--test`.

## Evidence

- **node (`node --test`): confirmed** by the probe above. Node reports the
  unloadable file as one failed test (`# fail 1`), exit 1.
- **pytest, whole-suite run: by code reading plus a pytest probe.** pytest
  exits 2 on a collection error (probed with `uvx pytest`); `_run_command`
  maps every non-zero status to 1, and `_selector_missed` only diverts 4/5
  on a targeted run. A targeted run on a file with a collection error did
  exit 2 through `tdd.py` (probed: pytest answered 4), so the `FIXING` gate,
  which always passes a selector, is not affected on pytest in that case.
- **vitest / jest: not probed** (not installed here). Same `_run_command`
  mapping, so the same behaviour is expected.
- **jig's own custom command.** `scripts/run_tests.py` turns a test-module
  import failure into a synthetic failing test and exits 1, and exits 1 when
  no type checker is found. Both are "exit 1 without a test that ran and
  failed" under the ADR-0068 contract jig now documents for custom commands.
- Whether an import error counts as a legitimate red in test-first work (the
  function under test does not exist yet) is the judgement this bug needs;
  it is why spec 123 did not change the built-in paths.

## Hypotheses

<!-- Anti-anchoring: >=2 candidates, mark the leading one. Any Markdown
     list works (-, *, +, or 1.); the gate counts top-level items only
     (indented sub-bullets are notes, not hypotheses). -->
- [ ] H1: <alternative explanation>, falsify by <check>
- [x] H2 (leading): <leading explanation>, confirm by <check>

## Root cause

## Repository closure inventory

<!-- Spec 091 / ADR-0037: pre-fix repository closure. Standard & gnarly
     bugs gate ROOT_CAUSED -> FIXING on substantive answers below. This
     is an effort-and-protocol standard, NOT a completeness proof: show
     the search you actually ran. A bare "none found" fails; record
     residual uncertainty as an assumption WITH the protocol behind it,
     applying the same enumeration standard as `## Root cause` (ADR-0052).
     Prefer a configured semantic index; the portable floor is targeted
     search + `git log`/`git blame`. -->

**Equivalent / convergent logic searched:**

**Relevant history inspected:**

**Affected call sites:**

**Reuse decision:**

## Fix class

## Fix

## Call-site closure

<!-- Spec 091 / ADR-0037: before REVIEWED, account for every site named
     in the inventory above as changed, tested, or intentionally left
     alone. Accounting, not mandatory widening. -->

**Disposition per affected site:**

## Already tried

## Regression test

## Proof

## Learning
