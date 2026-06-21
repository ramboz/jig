---
slice: 077-01 — pyright advisory probe
pass: compliance
verdict: pass
reviewer: main-session-fallback
reviewed_at: 2026-06-21T17:30:06Z
prompt_source: review.py implementation docs/specs/077-type-check-floor/spec.md 077-01 skills/code-health/health.py skills/code-health/test_health.py skills/code-health/SKILL.md docs/decisions/adr-0017-scaffolded-code-health.md
---

All 077-01 acceptance criteria pass.

AC1: Python projects now run a pyright AdvisoryProbe via the Python ecosystem probe list in skills/code-health/health.py; _resolve_pyright and _summarize_pyright_probe produce a count + representative diagnostic rules.
AC2: Pyright findings are emitted through _run_advisory_probes, so the normalized exit code still comes only from the primary linter path in cmd_check. test_pyright_signal_does_not_flip_clean_exit locks this.
AC3: Resolver coverage includes PATH, uvx, pipx, and absent-tool skip behavior. The local DoR probe verified uvx pyright --version => pyright 1.1.410.
AC4: The summarizer emits a tight line and the test asserts raw generalDiagnostics JSON is not leaked.

Verification: python3 -m unittest discover -s skills/code-health -p test_*.py; python3 scripts/run_tests.py; python3 scripts/spec_lint.py docs/specs/077-type-check-floor/spec.md; python3 skills/code-health/health.py check . with real pipx access.
