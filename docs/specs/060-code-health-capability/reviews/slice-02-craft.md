---
slice: 060-02 — Dogfood onto jig: CI Ruff floor
pass: craft
verdict: pass
reviewer: pr-review
reviewed_at: 2026-06-05T19:05:50Z
prompt_source: review.py pr-review
---

VERDICT: pass

REASONING:
ruff.toml uses the correct modern [lint] table schema with a justified E402 ignore and a defensible line-length=100; the CI step is well-placed alongside the existing run_tests/spec_lint/validate_manifests steps and invokes the same health.py check . entry point used locally (AC4 mirroring). The non-mechanical cleanup edits verified are behavior-preserving: the # noqa: F401 carries a clear re-export rationale, strict=True additions zip provably equal-length iterables, and the E741/ln renames are consistent local comprehension variables.

SPECIFIC ISSUES:
- [strength] workflow.py:26 — # noqa: F401 on the team_signal re-export clearly states WHY; correct way to suppress F401 on a deliberate re-export.
- [strength] verify_install.py + test_scaffold_mode.py — B905 strict=True added only where iterables are provably equal-length (fixed parallel lists / guarded by an explicit len assert). Correct, not blind.
- [nit] ruff.toml — E402 is globally ignored yet many files still carry per-line # noqa: E402, now redundant dead weight. Harmless (RUF100 not selected); optional cleanup.
- [nit] .jig/lint-command hardcodes trailing `.`; health.py honors the override verbatim, so `health.py check subdir/` would still lint the whole repo. Pre-existing 060-01 verbatim-override behavior, not introduced here.

RECONCILIATION NOTES:
- Deviation log should accurately enumerate the B-rule fixes actually applied: B904×1 (skills/memory-sync/memory.py, `) from None`), B007×2 (migrate.py dropped unused enumerate index; land.py args→_args), B905×4 strict=True, F841 removals, E741×11 renames, F401/E402 noqa. (The orchestrator's implementer brief had inaccurate path/line guesses; the actual fixes are correct.)
- Consider noting the redundant per-line # noqa: E402 (subsumed by global ignore) as a follow-up, optionally adding RUF100 to catch unused-noqa drift.
