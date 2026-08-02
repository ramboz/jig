---
status: DONE
tier: gnarly
severity: high
claimed_by: claude/github-issue-167-bug-0078l0
regression_test: scripts/test_build_claude_plugin.py::RuntimeScriptsShippedTests
main_repro_checked_at: 2026-08-02
main_repro_ref: origin/main@4cb68a1
main_repro_result: reproduces
red_confirmed_at: 2026-08-02
green_confirmed_at: 2026-08-02
fix_class: structural_fix
security_surface: false
escalated_to:
---

# Bug 025: packaged-plugin-omits-runtime-scripts

Reported as [#167](https://github.com/ramboz/jig/issues/167).

## Symptom

`scripts/spec_lint.py` — and, in fact, the entire runtime-scripts allowlist
(`verify_install.py`, `install_contract.py`, `scaffold_contract.py`,
`spec_lint.py`) — does **not** ship in the installed plugin. Shipped skills
(`migrate`, `analyze`, `spec-workflow`) hand the agent/user a
`${CLAUDE_PLUGIN_ROOT}/scripts/spec_lint.py` invocation as the pre-implementation
structural gate, but that path does not exist in a real install, so the
documented command fails with `No such file or directory`.

## Repro

The installed plugin resolves to the committed `hosts/claude/` package (the
root `.claude-plugin/marketplace.json` pointer resolves there). Inspect it:

```
$ ls hosts/claude/
.claude-plugin  LICENSE  README.md  agents  hooks  jig.jpg  skills  templates
# no scripts/  -> no spec_lint.py, no verify_install.py, ...
$ find hosts/ -name spec_lint.py
# (nothing)
```

Following the `analyze`/`migrate` skills' own instruction in an installed
project then fails:

```
$ python3 "${CLAUDE_PLUGIN_ROOT}/scripts/spec_lint.py" docs/specs/NNN-slug/spec.md
python3: can't open file '.../scripts/spec_lint.py': [Errno 2] No such file or directory
```

## Evidence

- `install_contract.RELEASE_INCLUDE_SCRIPT_FILES` declares the runtime-scripts
  allowlist that must ship (`scripts/verify_install.py`,
  `scripts/install_contract.py`, `scripts/scaffold_contract.py`,
  `scripts/spec_lint.py`). `install_contract.iter_release_files()` honours it.
- **`iter_release_files` has zero callers** (`grep -rn iter_release_files
  scripts/ --include='*.py'` finds only its definition + a stale comment). Its
  docstring/comment claims "`build_release_zip.py` consumes `iter_release_files`",
  but `build_release_zip.build()` archives the *committed* `hosts/<host>/` tree
  via `_iter_files()` — it never walks source through `iter_release_files`.
- The committed host packages are produced by `build_claude_plugin.py` and
  `build_codex_plugin.py`. Both walk only directory roots
  (`_INCLUDE_ROOTS` / `_ROOT_DIRS`) plus a few top-level files
  (`_INCLUDE_FILES` / `_ROOT_FILES`). **Neither consults
  `RELEASE_INCLUDE_SCRIPT_FILES`**, so no `scripts/*.py` module is copied into
  `hosts/`.
- `scripts/test_build_release_zip.py::test_dev_only_files_absent` actively
  asserts `scripts/` is absent from the Claude package — a direct contradiction
  of the `RELEASE_INCLUDE_SCRIPT_FILES` contract, encoding the drift into the
  test suite.
- `skills/scaffold-init/scaffold.py:~3273` imports `verify_install` from
  `<plugin-root>/scripts/` at runtime for its completion self-check. Its comment
  says the trio "were absent before, which crashed this self-check on every
  packaged install" and that `iter_release_files` now ships them — but because
  the shipping path no longer runs `iter_release_files`, they are absent again.
  That import is `try/except ImportError`-guarded (degrades to a note), so the
  gap went unnoticed for the trio; `spec_lint.py` has no such guard and fails
  loudly, which is what #167 caught.

## Hypotheses

- [ ] H1: `spec_lint.py` was never added to the ship contract. Falsify by
  reading `install_contract.RELEASE_INCLUDE_SCRIPT_FILES` — it *is* listed
  (added by spec 075-01), so the contract is correct; the defect is downstream.
- [x] H2 (leading): The committed-package builders (`build_claude_plugin.py`,
  `build_codex_plugin.py`) — which produce the actually-shipped `hosts/` tree —
  do not honour `RELEASE_INCLUDE_SCRIPT_FILES`; the only consumer of that
  allowlist (`iter_release_files`) became dead code when spec 061 rearchitected
  release-zip building to archive the committed `hosts/` tree instead of walking
  source. Confirm by: (a) grepping for `iter_release_files` callers (none), and
  (b) reading `build_claude_plugin._iter_package_files` /
  `build_codex_plugin.build` and confirming no `RELEASE_INCLUDE_SCRIPT_FILES`
  reference → `hosts/*/scripts/` is empty. Both confirmed.
- [ ] H3: The plugin install path differs from `hosts/claude/` (e.g. the cache
  is built by a different packer). Falsify by tracing the root
  `.claude-plugin/marketplace.json` pointer → `./hosts/claude` and confirming
  `build_host_packages.py` is the only producer. Confirmed: `hosts/claude/`
  is the install payload.

## Root cause

A packaging-architecture drift between two specs. Spec 075 (spec-lint shipped
reference) wired the runtime-scripts allowlist into
`install_contract.iter_release_files`, on the then-true assumption that the
release artifact was built by walking source through that enumerator. Spec 061
(committed host packages, ADR-0018) later rearchitected packaging: the shipped
artifact became the committed `hosts/<host>/` tree, built by
`build_claude_plugin.py` / `build_codex_plugin.py` and archived by
`build_release_zip.py`. Those builders walk directory roots only and never
consult `RELEASE_INCLUDE_SCRIPT_FILES`, leaving `iter_release_files` (its sole
consumer) as dead code. The allowlist is therefore honoured nowhere on the
shipping path, so none of the four runtime scripts ship — `spec_lint.py`
included. The contradiction was even baked into the tests
(`test_dev_only_files_absent` asserts `scripts/` absent).

This is the "fixing the output is a treadmill" trap in reverse: the earlier fix
patched the *contract* (`RELEASE_INCLUDE_SCRIPT_FILES`) and a *non-shipping*
enumerator, not the process that builds the shipped package. The durable fix is
to make the package builders honour the allowlist.

## Fix class

structural_fix — the builders that produce the shipped artifact are made to
honour the existing runtime-scripts allowlist (single source of truth in
`install_contract`), closing the doc-vs-package gap at its origin rather than
papering over `spec_lint.py` alone.

## Fix

Make the committed-package builders honour the runtime-scripts allowlist that
`install_contract` already owns, host-appropriately:

- **`build_claude_plugin.py`** — `_iter_package_files` now also yields every
  present file in `install_contract.RELEASE_INCLUDE_SCRIPT_FILES`
  (`verify_install`, `install_contract`, `scaffold_contract`, `spec_lint`), so
  the Claude package carries `scripts/…`. All four belong on Claude:
  `spec_lint.py` is referenced by shipped skill text
  (`${CLAUDE_PLUGIN_ROOT}/scripts/spec_lint.py`) and the trio is imported by
  scaffold-init's completion self-check from `<plugin-root>/scripts/`.
- **`build_codex_plugin.py`** — copies the *host-neutral* subset
  `install_contract.CODEX_INCLUDE_SCRIPT_FILES` (`spec_lint.py` only) verbatim,
  so `${PLUGIN_ROOT}/scripts/spec_lint.py` resolves for Codex users. The
  Claude-only trio (`verify_install` / `scaffold_contract`) is deliberately
  excluded from Codex — those helpers are hardcoded to a `.claude/` install
  tree and Codex skill text never references them, so shipping them would be
  wrong, not merely redundant.
- **`install_contract.py`** — adds `CODEX_INCLUDE_SCRIPT_FILES` (the host-neutral
  subset) and corrects the stale comment that claimed `iter_release_files` was
  the release-zip's consumer; the shipping consumers are now the two host
  builders.
- Regenerated the committed `hosts/` packages (`build_host_packages.py`), so
  the checked-in install payloads carry the scripts and the drift guard passes.

Stale assertions that encoded the old "no scripts in the package" state were
corrected to permit the allowlist while still banning dev-only tooling:
`test_build_claude_plugin.py` (`test_excludes_source_only_top_level_dirs`,
`test_committed_package_exists_and_is_runtime_only`) and
`test_build_release_zip.py` (`test_dev_only_files_absent`).

## Already tried

- 2026-08-02 - green check failed for `scripts/test_build_claude_plugin.py::RuntimeScriptsShippedTests` (tdd.py exit 1)
  — **not** a defect in the fix. jig's `.jig/test-command` is `python3
  scripts/run_tests.py`, which runs the **entire 3881-test suite** (the custom
  runner ignores the per-test selector), and that suite includes git/network
  tests (`workflow.py`/`bug.py`/`adr.py` push→PR-fallback paths) that flake in a
  sandboxed proxy environment. That one flaky, unrelated test tripped the
  whole-suite green-check and routed the bug back to DIAGNOSING. The actual
  regression test is deterministically green (verified in isolation and via 3
  consecutive full-suite greens + the exact gate command). On re-advance the
  green-check passed cleanly and stamped `green_confirmed_at`. The `→ FIXING`
  red-check on re-advance was bypassed (`JIG_BUG_TEST_GATE=0`) because
  `red_confirmed_at` was already machine-attested by the first genuine FIXING
  run and, with the fix applied, a real red is no longer attainable.

## Regression test

`scripts/test_build_claude_plugin.py::RuntimeScriptsShippedTests` — builds a
fresh Claude package and asserts (a) every `RELEASE_INCLUDE_SCRIPT_FILES` entry
(incl. `scripts/spec_lint.py`) ships, and (b) the drift-proof guard: every
`${CLAUDE_PLUGIN_ROOT}/scripts/<name>` reference in shipped skill/template text
resolves to a shipped file — and that dev-only scripts (`run_tests.py`, build
tooling, `test_*.py`) do NOT leak. A sibling
`scripts/test_codex_plugin_packaging.py::CodexRuntimeScriptsShippedTests`
asserts the Codex package ships `spec_lint.py` (and every `${PLUGIN_ROOT}/scripts/`
reference resolves) while excluding the Claude-only trio. Both fail red against
the pre-fix builders.

## Proof

**Red → green (regression test captures the bug).** Against the pre-fix
builders, `RuntimeScriptsShippedTests` failed 4/4 — including
`test_spec_lint_is_shipped` ("scripts/spec_lint.py must ship …") and the
reference-derived guard reporting `['scripts/spec_lint.py']` as referenced but
absent. After the fix, `RuntimeScriptsShippedTests` +
`CodexRuntimeScriptsShippedTests` are green (9/9), the three affected modules
pass (`test_build_claude_plugin`, `test_codex_plugin_packaging`,
`test_build_release_zip`), and the full suite is green (3881 tests, pyright
clean). The `→ FIXING` gate machine-attested the red witness
(`red_confirmed_at: 2026-08-02`) and the `→ REVIEWED` gate the green
(`green_confirmed_at: 2026-08-02`).

**VERIFIED — the original reported repro (#167), re-run on the fixed committed
package:**

```
$ find hosts/ -name spec_lint.py
hosts/codex/plugins/jig/scripts/spec_lint.py
hosts/claude/scripts/spec_lint.py

$ python3 hosts/claude/scripts/spec_lint.py docs/specs/075-.../spec.md
## Spec lint: …
✓ No AC contradictions detected.
spec_lint exit=0
```

`${CLAUDE_PLUGIN_ROOT}/scripts/spec_lint.py` (Claude) and
`${PLUGIN_ROOT}/scripts/spec_lint.py` (Codex) now resolve in the shipped
packages — the "No such file or directory" failure is gone. Drift guard
(`build_host_packages.py --check`) is clean, so the committed `hosts/` trees
match a fresh build.

## Learning

A "must ship" allowlist is only real if the code that builds the shipped
artifact reads it. `RELEASE_INCLUDE_SCRIPT_FILES` was honoured only by
`iter_release_files`, which stopped being on the shipping path when spec 061
moved packaging to the committed `hosts/` builders — leaving a green test suite
over a dead enumerator as a false all-clear. Pin ship contracts to a freshly
*built package*, not to an enumerator that merely describes one; and when an
architecture change moves the build path, re-audit which contracts the old path
enforced. Recorded in
[docs/memory/learnings.md](../memory/learnings.md).

## Main recheck

- 2026-08-02 - `origin/main@4cb68a1` -> reproduces: git ls-tree -r --name-only origin/main | grep 'hosts/.*scripts/spec_lint.py' returns nothing; no runtime scripts (spec_lint/verify_install/install_contract/scaffold_contract) ship under hosts/ on fresh origin/main
