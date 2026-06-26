---
status: Accepted
dependencies: []
last_verified: 2026-06-26
frame_review: true
---

# ADR-0030: Minimum supported Python is 3.9

## Status

Accepted (2026-06-26)

## Context

jig is distributed as a Claude Code / Codex plugin, not a pip package, so it
declares no `requires-python`. Its helper scripts (`skills/*/<helper>.py`, the
install trio under `scripts/`, `scaffold.py`) are invoked by the host with
whatever `python3` is on the user's PATH. On a default macOS install that is the
Command Line Tools interpreter — **Python 3.9.6**.

CI, however, only ever ran the test matrix on 3.11 and 3.12. A 3.10+ floor
therefore crept into the shipped code unnoticed: PEP 604 `X | None` unions
(3.10), `zip(..., strict=True)` (3.10), and a latent `@dataclass` +
`importlib`-loaded-module crash that surfaces under string annotations on 3.9
(and 3.14+). The result was that shipped, adopter-facing helpers
(`verify_install.py`, `workflow.py`, `migrate.py`, `scaffold.py`, …) raised on
the *most common* interpreter our adopters actually run. The breakage was
invisible to us because nothing tested it.

This ADR records the supported-floor decision and the mechanism that keeps it
from regressing. It is written *after* the corresponding fix shipped (commit
`fix(python): restore Python 3.9 compatibility + add 3.9.6 to CI matrix`); the
options below are the choices that fix deliberated, not hypothetical ones.

## Decision Options Considered

### Option A: Adopt Python 3.9 as the supported floor (chosen)
Make all shipped helpers run on 3.9.6, prove it with a 3.9.6 CI matrix job, and
pin `ruff` to `target-version = "py39"`. Keep readable PEP 604 annotations via
`from __future__ import annotations`; use `typing.Optional` only where a union
is in a runtime position (type-alias assignments) the future import cannot
defer. Version-gate the few genuinely-3.11 internal tooling tests (`tomllib`).
- **Pros:** Works out-of-the-box on default macOS — no adopter or contributor
  has to install a newer interpreter. Matches reality (3.9.6 is what ships).
  Cheap to hold: the future-import convention keeps modern syntax; the CI job
  is the real guard.
- **Cons:** Cannot use 3.10+ niceties (`match`, bare PEP 604 in runtime
  positions, `zip(strict=)`) without a guard. Internal codex/packaging tooling
  that needs `tomllib` (3.11+) must version-gate rather than run everywhere.

### Option B: Declare 3.10 (or 3.11) the floor; tell users to upgrade
Document a minimum and require contributors/adopters to install a newer Python.
- **Pros:** Free use of 3.10/3.11 syntax and stdlib (`tomllib`, `match`). No
  compatibility shims.
- **Cons:** Breaks the plugin on the default macOS interpreter — every adopter
  on a stock Mac hits import errors until they install and PATH-prioritize a
  newer Python. Pushes setup friction onto users for a tool whose value is
  reducing friction. Silently regressed once already precisely because no one
  verified the floor.

### Option C: Add a `tomli` dependency to backport `tomllib` to 3.9
Take a third-party dep so the TOML-parsing codex tooling runs on 3.9 too.
- **Pros:** The codex packaging tests could run on the 3.9 job.
- **Cons:** jig is deliberately **zero-dependency** (stdlib only) — a core
  positioning property. One dep is a precedent and a supply-chain surface for a
  problem that only affects *internal* dev/CI tooling, which already runs on
  3.11/3.12.

## Recommended Decision

**Adopt Option A: Python 3.9 is jig's minimum supported runtime.**

Concretely:
- **Shipped, adopter-facing code MUST run on 3.9.** This is the code under
  `install_contract.RELEASE_INCLUDE_ROOTS` (`skills/`, `agents/`, `hooks/`,
  `templates/`, the plugin manifests) plus the install trio.
- **Convention for PEP 604 unions:** add `from __future__ import annotations`
  (lazy string annotations) rather than `typing.Optional`. Reserve `Optional`
  for runtime-position unions (type-alias assignments, `Callable[[...], ...]`
  subscripts) that the future import does not defer.
- **No 3.10+ runtime APIs in shipped code** (`zip(strict=)`, `match`, …) without
  a 3.9-safe shim.
- **Dynamic module loading** (`importlib.util.module_from_spec` / `exec_module`)
  MUST register the module in `sys.modules` before `exec_module` — required for
  `@dataclass` modules under string annotations on 3.9 and 3.14+.
- **Internal dev/CI tooling under `scripts/` MAY target 3.11+** (it runs only in
  jig's own CI). Tests that need `tomllib` version-gate via a module-level
  `load_tests` returning an empty suite below 3.11 (works with
  `unittest.discover`; a module-level `raise SkipTest` does not).

Enforcement is two-layer: a **`3.9.6` job in the CI matrix** (the load-bearing
guard — it actually executes the floor) and **`ruff target-version = "py39"`**
(a static signal). jig stays **zero-dependency**.

## Consequences

**Becomes easier:**
- The plugin works on a stock macOS with no interpreter install.
- Regressions are caught mechanically: a new bare `X | None` or `zip(strict=)`
  fails the 3.9.6 CI job immediately.
- The `from __future__ import annotations` convention keeps modern, readable
  type syntax across the codebase.

**Becomes harder:**
- Contributors must remember the future-import convention and avoid 3.10+
  runtime APIs in shipped code (the CI job is the backstop when they forget).
- Internal codex/packaging tooling that depends on `tomllib` carries a small
  version-gate and does not exercise on the 3.9 job (it runs on 3.11/3.12).

## Assumptions

- Default macOS (Command Line Tools) ships Python **3.9.6** — verified by
  running the local interpreter (`python3 --version` → 3.9.6) during the fix.
- The shipped surface is exactly `install_contract.RELEASE_INCLUDE_ROOTS`
  (`.claude-plugin`, `.codex-plugin`, `agents`, `skills`, `hooks`, `templates`)
  + `README`/`LICENSE`; `scripts/` does **not** ship — verified by reading
  `install_contract.py` and confirming the install trio imports clean on 3.9.6.
- The full test suite is green on 3.9.6 (2944 tests) and on 3.13 (3088 tests,
  the delta being the 3.11-gated codex suite) — verified by running
  `scripts/run_tests.py` under both interpreters.
- **The 3.9.6 job is import-coverage + test-exercised coverage, not full
  behavior coverage.** `run_tests.py` discovers `test_*.py` across every skill /
  `scripts/` / `hooks/` dir, and those tests import the shipped helpers, so a
  bare `X | None` / `zip(strict=)` on any *import path* or *test-exercised* line
  fails the job. It does **not** catch a 3.10+ API on a code path that is both
  untested *and* invisible to ruff's version-aware lints. `ruff target-version =
  py39` is the static backstop for some unexercised branches, but the two layers
  together still leave a residual untested-and-unlinted gap — the same class of
  blind spot (untested code) that let the original regression ship. This is a
  bounded, known risk, not an implied guarantee.

## Kill criteria

- The default macOS `python3` moves to ≥3.10 **and** jig's adopter base has
  migrated off older Command Line Tools — at which point the floor can be
  raised (update the CI matrix + `ruff target-version`, drop the future-import
  and `tomllib` guards).
- A shipped feature genuinely requires a 3.10+ runtime capability that cannot be
  shimmed at acceptable cost — would force re-opening this trade-off.
- **A 3.9 break reaches an adopter despite a green 3.9.6 CI job** — this would
  signal the import-coverage proxy is too weak, and the response is to add a
  smoke-import test that loads *every shipped module* on 3.9 regardless of test
  coverage (closing the untested-path gap named in Assumptions), not to abandon
  the floor.

## Open questions

None.
