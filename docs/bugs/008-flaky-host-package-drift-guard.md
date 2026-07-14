---
status: DIAGNOSING
tier: gnarly
severity: medium
claimed_by: detached
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

# Bug 008: flaky-host-package-drift-guard

## Symptom

[`python3 scripts/run_tests.py`](../../scripts/run_tests.py) intermittently
fails
`scripts/test_build_host_packages.py::DriftCheckTests::test_check_passes_when_in_sync`.
The seed build and the in-process drift-check rebuild both use the repository
root as source, but `_diff_packages` reports only
`claude/.claude-plugin/plugin.json` as different. Standalone drift checks and
repeated warm builds pass. External discussion and the original report live in
[GitHub issue #95](https://github.com/ramboz/jig/issues/95).

## Repro

Run the full suite strictly sequentially from a clean checkout:

```bash
JIG_HOST_DRIFT_DIAGNOSTICS=1 python3 scripts/run_tests.py
```

The failure is low-frequency. Do not run concurrent suite processes: several
tests exercise git worktree and reservation locks and concurrent runs can
deadlock for reasons unrelated to this bug. When this specific in-sync test
fails under diagnostic mode it also opts into
`JIG_HOST_DRIFT_PRESERVE_SCRATCH=1`, so its scratch tree survives for
inspection; intentional negative drift tests continue to clean up.

## Evidence

- The focused host-package and Claude-builder modules pass 34/34 under both
  CPython 3.14.0 and 3.13.13 with diagnostics enabled.
- A sequential full unit pass on 2026-07-14 passed 3,455 tests with six skips;
  the wrapper's later pyright invocation was blocked by the local sandbox and
  is unrelated.
- After instrumentation, sequential full unit passes remained clean on
  CPython 3.14.0 (3,456 tests, six skips) and CPython 3.13.13 (3,457 tests, six
  skips). One clean sample per interpreter does not falsify H4.
- `.claude-plugin/plugin.json` and
  `hosts/claude/.claude-plugin/plugin.json` had matching SHA-256 hashes before
  the run.
- `build_claude_plugin.build()` verifies the source manifest exists, then
  independently discovers package entries with `Path.rglob()`. Python's glob
  traversal suppresses filesystem-scanning `OSError`s, so a transient scan
  failure can theoretically omit a required file without failing the build.
- The active interpreter is CPython 3.14.0 with the GIL enabled. CPython fixed
  a separate 3.14 `pathlib` race in later maintenance releases
  ([python/cpython#139001](https://github.com/python/cpython/issues/139001));
  relevance is unproven and must be partitioned by interpreter version.

## Hypotheses

<!-- Anti-anchoring: >=2 candidates, mark the leading one. Any Markdown
     list works (-, *, +, or 1.); the gate counts top-level items only
     (indented sub-bullets are notes, not hypotheses). -->
- [x] H1 (leading): `Path.rglob()` transiently omits the mandatory Claude
  manifest during one of the two builds, and the builder silently succeeds
  with a presence difference. Confirm by capturing entry-list membership plus
  source/seed/scratch presence and hashes on the next failing run; falsify if
  both outputs contain the manifest with different bytes.
- [ ] H2: another process mutates the source manifest between the seed and
  scratch reads. Confirm with before/between/after source stat and SHA-256 plus
  a child-process-aware filesystem trace; falsify if the source remains stable
  and one output is absent.
- [ ] H3: shared in-process module or predicate state changes Claude package
  enumeration between calls. Confirm by capturing `_INCLUDE_ROOTS`, predicate
  module origins, and entry membership for both builds; falsify if these are
  stable while the source or filesystem observation changes.
- [ ] H4: CPython 3.14.0 runtime behavior contributes to the traversal flake.
  Confirm with a materially different failure rate in sequential cold-copy
  sweeps on 3.14.0 versus a current 3.14 patch release and 3.13; falsify if the
  same evidence reproduces across versions.

## Root cause

## Fix class

## Fix

## Already tried

- Standalone `python3 scripts/build_host_packages.py --check`: passes.
- Repeated warm `build_all` comparisons: byte-identical.
- Fixed `PYTHONHASHSEED` sweeps: passed for the values recorded in issue #95.
- Parent-process filesystem tracing on passing runs: no source manifest writes,
  deletes, or renames observed.
- Static search found leaked `CLAUDE_PLUGIN_ROOT` test state, but neither host
  package builder reads that variable; treat it as separate isolation debt.
- A deterministic diagnostic test forces `_iter_package_files()` to omit the
  Claude manifest. The report correctly records stable source/committed hashes,
  `scratch: absent`, and `claude-manifest-enumerated: no`, and preserves the
  scratch tree only when separately requested.

## Regression test

## Proof

- `python3 -m unittest scripts.test_build_host_packages scripts.test_build_claude_plugin -v`
  — 34 tests pass.
- `JIG_HOST_DRIFT_DIAGNOSTICS=1 python3.13 -m unittest scripts.test_build_host_packages scripts.test_build_claude_plugin`
  — 34 tests pass.
- Sequential `scripts/run_tests.py` unit suites pass on CPython 3.14.0 and
  3.13.13 with diagnostics enabled; the subsequent pyright gate cannot access
  the sandboxed uv cache in this environment.
- Repository-pinned Ruff 0.15.16 passes on all three changed Python files.
- `python3 scripts/build_host_packages.py --check` remains clean.

## Learning
