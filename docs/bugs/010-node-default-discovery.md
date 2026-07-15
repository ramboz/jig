---
status: DONE
tier: standard
severity: medium
claimed_by: codex/issue-100-node-default-discovery
regression_test: skills/tdd-loop/test_tdd.py::TargetedRunTests::test_node_default_run_uses_builtin_discovery
main_repro_checked_at: 2026-07-14
main_repro_ref: origin/main@7d538ea068db8cd8f1a1d381abf8935b516df8c7
main_repro_result: reproduces
red_confirmed_at: 2026-07-14
green_confirmed_at: 2026-07-14
fix_class: local_patch
security_surface: false
escalated_to:
---

# Bug 010: node-default-discovery

## Symptom

For a project whose `package.json` test script is the bare `node --test`,
`tdd.py run` reports red even when Node's default-discovered suite is green.
That false negative propagates into `slice-land prepare` as a tests blocker.

## Repro

1. Create a Node project with `scripts.test: "node --test"` and tests under
   Node's default discovery paths.
2. Run `python3 skills/tdd-loop/tdd.py run <project>`.
3. Observe that jig invokes `node --test <absolute-project-directory>`, which
   exits 1 with `MODULE_NOT_FOUND`; running `node --test` from the project
   directory instead discovers and passes the suite.

## Evidence

- `cmd_run()` calls `_build_command(runner, test_path or target, selector)`, so
  `_build_command()` cannot distinguish an explicit `--test-path` from the
  fallback target directory.
- The Node branch unconditionally appends `selector_path or str(path)`, making
  an unfiltered suite command `node --test <target-directory>`.
- A local Node 22.16.0 repro (showing this is not limited to Node 24) treats the
  jig worktree directory as a module entry point and exits 1 with
  `MODULE_NOT_FOUND`.
- Direct command-builder inspection returns
  `['node', '--test', '/tmp/example-project']` for an unfiltered run, while a
  path-and-name selector is ordered correctly.

## Hypotheses

- [x] **The Node command builder confuses the fallback target with an explicit
  test path (leading).** Confirmed by direct `_build_command()` inspection and
  the live Node failure above; targeted file/name construction remains valid.
- [ ] **Node 24 changed positional-directory semantics.** Falsified by the same
  `MODULE_NOT_FOUND` result on local Node 22.16.0; the faulty argv, rather than
  a Node 24-only change, creates the failure.
- [ ] **`slice-land` misclassifies a successful test command.** Falsified
  upstream: `tdd.py run` itself receives Node's genuine exit 1 from the
  malformed command, so slice-land is correctly relaying the normalized red
  status it receives.

## Root cause

Bug 003 added Node's built-in runner but modeled its default command after
runners that accept a directory as a search root. Node's bare `--test` already
uses cwd-based default discovery; a positional directory is executed as a
module instead. Because `cmd_run()` collapses both the default target and an
explicit `--test-path` into one `path` argument, the Node builder always emits
that positional directory and cannot select the correct default-discovery
form.

## Fix class

local_patch

## Fix

Teach `_build_command()` whether the supplied path came from an explicit
`--test-path`. The Node branch now omits the fallback project directory for an
unfiltered suite (and for a name-only selector), allowing cwd-based default
discovery; it still appends an explicit test path or selector path. Update the
tdd-loop skill contract and regenerate both host packages from the canonical
source.

## Already tried

- 2026-07-14 - green check failed for
  `skills/tdd-loop/test_tdd.py::TargetedRunTests::test_node_default_run_uses_builtin_discovery`
  (tdd.py exit 1).
- 2026-07-14 - the first green gate ran all 3,461 tests successfully but the
  sandboxed pyright step could not read `/Users/ramboz/.cache/uv/...` and made
  the configured test wrapper exit 1. The identical suite passed with pyright
  clean when rerun with cache access. Re-enter FIXING with
  `JIG_BUG_TEST_GATE=0` because the original red gate is already stamped.
## Regression test

`skills/tdd-loop/test_tdd.py::TargetedRunTests::test_node_default_run_uses_builtin_discovery`

## Proof

- Red gate: `bug.py transition 010 FIXING` ran the configured repository test
  command and stamped `red_confirmed_at` with the untouched implementation.
- Focused green: three Node command-construction tests pass, covering default
  discovery, explicit `--test-path`, and file/name selector ordering.
- Adjacent green: `python3 -m unittest discover -s skills/tdd-loop -p
  'test_*.py'` passes 133 tests with 5 skips.
- Original live fixture: the fixed `tdd.py run` invokes Node default discovery,
  passes 1/1 tests, and exits 0.
- Packaging: `python3 scripts/build_host_packages.py` regenerated the Claude and
  Codex host payloads from the canonical sources.
- Full green: `python3 scripts/run_tests.py` passes 3,461 tests (6 skipped) and
  pyright clean when run with access to its existing uv cache.

## Learning

See `docs/memory/learnings.md` -> "Bug 010: Node default discovery needs no
directory operand."

## Main recheck

- 2026-07-14 - `origin/main@7d538ea068db8cd8f1a1d381abf8935b516df8c7` -> reproduces: node --test passes 1/1 in fixture; fresh-main tdd.py run exits 1 with MODULE_NOT_FOUND after invoking the project directory
