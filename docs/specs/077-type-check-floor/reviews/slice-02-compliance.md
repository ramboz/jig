---
slice: 077-02 — jig self typed baseline
pass: compliance
verdict: pass
reviewer: main-session-fallback
reviewed_at: 2026-06-21T18:01:49Z
prompt_source: review.py implementation docs/specs/077-type-check-floor/spec.md 077-02 pyrightconfig.json scripts/run_tests.py scripts/test_run_tests.py skills/code-health/health.py skills/migrate/migrate.py skills/scaffold-init/scaffold.py skills/slice-land/land.py skills/spec-workflow/workflow.py skills/tdd-loop/quality.py skills/tdd-loop/tdd.py docs/specs/077-type-check-floor/slice-02-self-baseline.md docs/specs/077-type-check-floor/plan.md docs/specs/077-type-check-floor/tasks.md
---

All 077-02 acceptance criteria pass.

AC1: `pyrightconfig.json` establishes the jig helper/runtime baseline over `skills/` plus `scripts/run_tests.py`, excludes `test_*.py` with an inline rationale for the dynamic import harnesses, and `uvx pyright --outputjson` reports 19 analyzed files with 0 errors, warnings, or information diagnostics.

AC2: `scripts/run_tests.py` is now import-safe, builds the existing unittest suite through `build_suite()`, then runs `run_pyright_gate()` after tests. The gate resolves pyright by PATH -> `uvx` -> `pipx`, reports compact diagnostics, and returns failure on any pyright non-zero exit. `scripts/test_run_tests.py` covers resolver order, missing checker failure, clean pass, and diagnostic failure. A real reversible probe (`_TYPECHECK_FAILURE_PROBE: str = None`) made the pyright gate fail with `reportAssignmentType` before removal.

AC3: The deviation log records real findings fixed: nullable custom-command parsers, jscpd percentage narrowing, optional CLI/default signatures, release-reason guard, optional YAML inputs, Inventory field annotations, scaffold nullable arguments, and the scripts import path used for `verify_install` resolution.

Verification: `python3 scripts/test_run_tests.py` passed 5 tests; `uvx pyright --outputjson` passed with 0 diagnostics; `python3 scripts/run_tests.py` passed 2,756 tests with 3 skipped and ended with `pyright: clean`; the reversible type-error probe failed the pyright gate as expected.
