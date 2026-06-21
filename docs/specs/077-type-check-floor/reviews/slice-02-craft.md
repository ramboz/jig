---
slice: 077-02 — jig self typed baseline
pass: craft
verdict: pass
reviewer: main-session-fallback-pr-review
reviewed_at: 2026-06-21T18:02:03Z
prompt_source: review.py pr-review docs/specs/077-type-check-floor/spec.md 077-02 pyrightconfig.json scripts/run_tests.py scripts/test_run_tests.py skills/code-health/health.py skills/migrate/migrate.py skills/scaffold-init/scaffold.py skills/slice-land/land.py skills/spec-workflow/workflow.py skills/tdd-loop/quality.py skills/tdd-loop/tdd.py docs/specs/077-type-check-floor/slice-02-self-baseline.md docs/specs/077-type-check-floor/plan.md docs/specs/077-type-check-floor/tasks.md
---

No blockers or pre-merge nits found.

Scope is tight for 077-02: the patch adds a jig-local pyright baseline, wires the documented local gate, fixes only the runtime helper contracts pyright surfaced, and records slice plan/tasks/deviation evidence. It preserves 077-01's scaffolded-project behavior: `health.py` still treats pyright as an advisory probe, while only jig's own `scripts/run_tests.py` gates on pyright.

Strengths: the gate is importable and unit-tested; diagnostics are compact rather than dumping raw pyright JSON; resolver behavior mirrors the existing PATH/ephemeral pattern; and the baseline explicitly excludes `test_*.py` with rationale instead of silently suppressing broad rule categories.

Residual risk: `python3 scripts/run_tests.py` now depends on pyright being available via PATH, `uvx`, or `pipx`; this is intentional for jig's stricter self-gate. The full gate was run with `uvx pyright` available and passed.
