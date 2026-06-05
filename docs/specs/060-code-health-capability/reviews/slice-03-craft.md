---
slice: 060-03 — Broaden ecosystems + complexity dimension
pass: craft
verdict: pass
reviewer: jig:reviewer (pr-review)
reviewed_at: 2026-06-05T19:40:07Z
prompt_source: review.py implementation docs/specs/060-code-health-capability/spec.md 060-03 <deliverables> (craft pass)
---

VERDICT: pass

REASONING:
The rewrite is genuinely table-driven — adding a third ecosystem is a single `Ecosystem` descriptor with its own resolver/summarizer/probes; detection, degradation, and dispatch all iterate `ECOSYSTEMS` rather than forking on if/elif. The advisory-probe abstraction enforces "reported, not gating" structurally (only the primary linter's exit code maps through). Tests are hermetic and cover Python+Node detection, complexity/prettier advisory signals (including best-effort failure-swallow), and mixed/unknown degradation. The named focus risks (broad except, prettier heuristic, redundant re-detection) are defensible craft choices; remaining items are nits.

SCOPE: Rewrites health.py from Python-only to table-driven multi-ecosystem (Python ruff + Node eslint) with advisory probes (complexity/prettier); extends test_health.py; updates SKILL.md.

NITS:
- health.py:469-492 — _summarize_for / _advisory_probes_for re-run override-check + ecosystem detection; could thread a resolved Ecosystem through one pass.
- health.py:408-410 — _summarize_findings back-compat alias is speculative dead code; drop unless an external caller exists.
- health.py:143-145 — _detect_node docstring says it mirrors tdd.py's _pkg_deps source but only checks package.json presence; docstring imprecision.
- health.py:151,176 — _resolve_ruff / _resolve_ruff_complexity duplicate the ruff→uvx→pipx launcher block; a _ruff_launcher(args) helper would DRY it.

STRENGTHS:
- Genuinely extensible Ecosystem/AdvisoryProbe table.
- "reported, not gating" is structural, not per-call discipline; locked by tests.
- Broad except scoped to the advisory runner only; primary cmd_check still discriminates FileNotFoundError/OSError → 2 from findings → 1.
- Tests hermetic with _seed_python/_seed_node fixtures; deviation log honest about the principled setUp marker-seeding.

RECONCILIATION NOTES:
Deviation log's "_resolved_name renders override's first tokens" claim: a `pipx run --spec ...` override actually renders as `pipx run` (3 tokens), not `pipx run --spec`. Cosmetic; fix the deviation-log wording.
