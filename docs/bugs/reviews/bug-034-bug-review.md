---
bug: 034
pass: bug-review
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-09-17T03:08:40Z
prompt_source: review.py bug-review docs/bugs/034-copilot-scaffold-defaults-claude.md skills/scaffold-init/scaffold.py skills/scaffold-init/test_scaffold_mode.py hosts/copilot/.github/skills/scaffold-init/scaffold.py
---

VERDICT: pass

REASONING:
The fix addresses the recorded root cause rather than just the symptom: the Copilot-packaged helper now infers `copilot` from the `.github/skills/...` package topology, resolves the package root above `.github`, accepts Copilot manifests, uses `.github/templates`, and renders `AGENTS.md` with `host_renderer: "copilot"`. The committed Copilot package carries the same source changes, and the regression test exercises the exact repro shape: running the committed Copilot scaffold helper without `--host` and asserting no Claude primer/tree is produced. The scope is narrow and honestly accounts for the remaining unsupported Copilot in-repo machinery path by refusing it instead of silently copying Claude machinery.

SPECIFIC ISSUES:
None.

RECONCILIATION NOTES:
None.
