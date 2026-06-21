---
slice: 077-01 — pyright advisory probe
pass: craft
verdict: pass
reviewer: main-session-fallback-pr-review
reviewed_at: 2026-06-21T17:30:06Z
prompt_source: review.py pr-review docs/specs/077-type-check-floor/spec.md 077-01 skills/code-health/health.py skills/code-health/test_health.py skills/code-health/SKILL.md docs/decisions/adr-0017-scaffolded-code-health.md
---

No blockers or pre-merge nits found.

Scope is tight: the patch adds one Python advisory probe, focused tests, code-health user docs, and the ADR-0017 amendment requested by the slice. No unrelated helper refactor or behavior change to primary linter exit mapping.
Strengths: pyright uses the existing AdvisoryProbe mechanism instead of a parallel pathway; tests cover resolver order, absent-tool skip behavior, tight summary shape, and advisory non-gating. Documentation matches the new contract.
Residual risk: pyright JSON variants without rule fields fall back to severity-only or count-only summaries, which is acceptable for a tight advisory signal and keeps the probe best-effort.
