---
slice: 060-02 — Dogfood onto jig: CI Ruff floor
pass: compliance
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-06-05T19:05:50Z
prompt_source: review.py implementation
---

VERDICT: pass

REASONING:
All four ACs are satisfied. AC1: ruff.toml is config-only with the exact curated set (select=["F","E","W","I","B"], ignore=["E402"], line-length=100); no pyproject.toml at root. AC2: CI gains a "Code-health floor (ruff)" step that dogfoods `health.py check .`; the real pin ruff==0.15.16 lives in `.jig/lint-command` (pipx run --spec), which resolve_lint_command honors first — ephemeral, reproducible, installs nothing permanently. AC3: floor green (health.py check . exits 0; full suite 2223 OK). AC4: both CI and local invoke the identical `python3 skills/code-health/health.py check .`, mirroring `.jig/test-command`.

SPECIFIC ISSUES:
(none blocking)

RECONCILIATION NOTES:
- AC2 phrasing "(pipx run ruff … / health.py)" is implemented as: version pin in `.jig/lint-command` + CI invokes health.py. Faithful/stronger reading; document where the pin lives.
- line-length=100 chosen for the spec's "house style"; record the concrete value.
- cleanup touched 060-01 DONE files (health.py blank-line, test_health.py import reorder) to bring code-health under its own floor — intentional zero-behavior.
- workflow.py:26 noqa F401 on `from _common import team_signal` is legitimate: test_workflow.py monkeypatches _workflow.team_signal.count_team_contributors, requiring the module attribute. Minimal correct fix.
- Several per-line `# noqa: E402` now redundant under the global ignore — harmless; optional follow-up (RUF100).
