---
status: DONE
tier: standard
severity: medium
claimed_by: claude/issue-129-bug-review-jsr2cp
regression_test: skills/slice-land/test_land.py::CheckTestsHelperResolutionTests
main_repro_checked_at: 2026-08-02
main_repro_ref: origin/main@2850a09
main_repro_result: reproduces
red_confirmed_at: 2026-08-02
green_confirmed_at: 2026-08-02
fix_class: local_patch
security_surface: false
escalated_to:
---

# Bug 024: slice-land-tests-inert-vendored

Reported as [issue #129](https://github.com/ramboz/jig/issues/129).

## Symptom

`jig:slice-land`'s `land.py prepare` reports a **Tests** readiness row. In a
project where jig is **vendored into `.claude/skills/`** with the marketplace
`jig-` prefix on the skill directories (`jig-slice-land/`, `jig-tdd-loop/`, …)
and `CLAUDE_PLUGIN_ROOT` unset, that row can never say `red`: it always reports
`warning — no test runner detected (slice may be doc-only)`, even on a repo
with a full, green suite. A slice with genuinely failing tests would still pass
the readiness gate. The check meant to block landing on red tests is a no-op in
that layout.

## Repro

1. Vendor jig into a repo's `.claude/skills/` with `jig-`-prefixed dirs
   (`jig-slice-land/`, `jig-tdd-loop/`, plus `_common/`).
2. Add a pytest/vitest suite so `jig-tdd-loop/tdd.py detect .` finds a runner.
3. With `CLAUDE_PLUGIN_ROOT` unset, call `land.check_tests(Path("."))`.
4. Observe it returns `("warn", -1)` (the "helper missing" branch) instead of
   `("green", 0)`, so the Tests row renders the doc-only warning. Break a test
   and it still says the same thing rather than `red`.

Verified in a scratch vendored layout: `tdd.py detect .` prints `pytest`, yet
`check_tests` returns `warn -1`.

## Evidence

`skills/slice-land/land.py`, `check_tests` (pre-fix):

```python
plugin_root = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", "")).resolve() \
    if os.environ.get("CLAUDE_PLUGIN_ROOT") else \
    Path(__file__).resolve().parents[2]
tdd_py = plugin_root / "skills" / "tdd-loop" / "tdd.py"
if not tdd_py.is_file():
    return "warn", -1        # <-- non-blocking; silently disables the check
```

- With `CLAUDE_PLUGIN_ROOT` unset and `land.py` at
  `.claude/skills/jig-slice-land/land.py`, `parents[2]` is `.claude`, so the
  lookup resolves to `.claude/skills/tdd-loop/tdd.py`. The real helper is at
  `.claude/skills/jig-tdd-loop/tdd.py` — the `jig-` prefix is never accounted
  for. The lookup misses.
- The miss returns a **non-blocking** `warn`, indistinguishable in the report
  from the legitimate exit-2 (no runner / doc-only) case, so the failure reads
  as "tests considered, none found" rather than "check could not run".
- Downstream observation in the issue: landing 002-02 in `bouge` landed with
  the Tests row showing the doc-only warning despite 175 passing vitest tests.

## Hypotheses

- [ ] H1: `tdd.py` is genuinely absent from the vendored install, so the
  helper-missing branch is correct. Falsify by confirming
  `.claude/skills/jig-tdd-loop/tdd.py` exists on disk while `check_tests`
  still returns `warn -1`.
- [x] H2 (leading): The `parents[2]` fallback hard-codes the un-prefixed
  `skills/tdd-loop/` layout and does not resolve `land.py`'s own sibling
  directories, so a `jig-`-prefixed sibling is never found and the miss is
  then conflated with the doc-only case. Confirm by pointing the resolver at
  `land.py`'s sibling dirs (name-agnostic) + a `*tdd-loop/` glob and watching
  the vendored repro flip to `green`, and by splitting the report's two `warn`
  causes so a helper-not-found reads distinctly from doc-only.

## Root cause

Two coupled defects, both in `check_tests` / the report renderer:

1. **Path resolution assumes an un-prefixed plugin layout.** The
   `CLAUDE_PLUGIN_ROOT`-unset fallback is `Path(__file__).parents[2] /
   "skills" / "tdd-loop" / "tdd.py"`. That is only correct when the plugin
   root is two levels above the skill dir *and* the sibling is named exactly
   `tdd-loop`. In a vendored install the skills are siblings of `land.py`'s own
   parent (`.claude/skills/jig-slice-land/` → sibling
   `.claude/skills/jig-tdd-loop/`) and carry the `jig-` prefix, so the fixed
   path misses.

2. **A helper that cannot be found is treated as "no tests" (non-blocking).**
   The miss returns the same `warn` used for a real doc-only slice (`tdd.py run`
   exit 2). Conflating "check did not run — environment problem" with "no runner
   detected — legitimately doc-only" is what lets the failure hide: the report
   says the reassuring doc-only sentence instead of surfacing that the gate was
   skipped.

## Fix class

local_patch

## Fix

Resolve `tdd.py` robustly and distinguish the two non-green causes:

- Add a `_resolve_tdd_py()` helper that tries, in order: `CLAUDE_PLUGIN_ROOT`
  (`<root>/skills/tdd-loop/tdd.py`); `land.py`'s own sibling directories
  (`<skills-dir>/*/tdd.py` — works regardless of the parent's name, covering
  both `tdd-loop/` and `jig-tdd-loop/`); and a `*tdd-loop/tdd.py` glob under
  the skills dir as a last resort. Returns the first match, else `None`.
- Introduce a distinct `"not_run"` status for "helper could not be located"
  (env problem), separate from `"warn"` (exit 2, doc-only). `check_tests`
  returns `("not_run", -1)` when the helper is missing.
- Render `not_run` as a loud, non-passing line — `[!] Tests: NOT RUN — could
  not locate tdd.py helper …` — worded so it is not read as a pass. Keep it
  non-gating on the exit code by default (an env problem is not red tests), but
  make it unmistakable in the report so it can no longer hide behind the
  doc-only wording.
- Blast-radius (surfaced by the bug-review pass): extend the 072-02
  `render_servo_suggestion` doc-only guard from `test_status == "warn"` to
  `("warn", "not_run")`. Previously "helper missing" returned `warn` and thus
  suppressed the servo suggestion; the new `not_run` status must preserve that
  silence, since an un-run gate means runner presence is unknown.

Deviation notes for reconciliation:
- `check_tests`'s return contract widened from `'green'|'red'|'warn'` to
  `'green'|'red'|'warn'|'not_run'`; module header + `check_tests` docstring
  updated.
- The `except FileNotFoundError` branch in `check_tests` now returns `not_run`
  rather than the prior `warn` (minor, deliberate — a missing interpreter/helper
  is an env problem, not a doc-only slice).

## Already tried

## Regression test

skills/slice-land/test_land.py::CheckTestsHelperResolutionTests

## Proof

- Red: with the pre-fix `land.py` restored (fix stashed), the full suite runs
  red — `bug.py transition 024 FIXING` stamped `red_confirmed_at: 2026-08-02`.
- Green: with the fix applied, `python3 -m unittest
  skills.slice-land.test_land.CheckTestsHelperResolutionTests` passes (5 tests,
  1 skipped where pytest is not importable in the sandbox).
- End-to-end: in a scratch vendored layout (`.claude/skills/jig-slice-land` +
  `jig-tdd-loop`, `CLAUDE_PLUGIN_ROOT` unset), the fixed `_resolve_tdd_py()`
  resolves `.../jig-tdd-loop/tdd.py` (pre-fix: `None`, so `check_tests`
  returned `('warn', -1)` regardless of suite state).

## Learning

A safety gate that fails "open" is indistinguishable from a gate that passed.
Resolve sibling helpers by content (glob `*tdd-loop/tdd.py` off `land.py`'s own
directory), not by a hard-coded parent name that breaks under a vendored /
`jig-`-prefixed layout. And keep "the check could not run" (`not_run`, loud)
separate from "there was nothing to check" (`warn`, doc-only) — collapsing them
is what let the no-op hide. When widening a status enum, re-audit every consumer
(the servo-suggestion doc-only guard keyed on `== "warn"` had to learn
`not_run` too). Full note in `docs/memory/learnings.md`.

## Main recheck

- 2026-08-02 - `origin/main@2850a09` -> reproduces: Vendored layout (.claude/skills/jig-slice-land + jig-tdd-loop, CLAUDE_PLUGIN_ROOT unset): origin/main land.py check_tests(Path('.')) returns ('warn', -1) despite jig-tdd-loop/tdd.py present and tdd.py detect finding pytest.
