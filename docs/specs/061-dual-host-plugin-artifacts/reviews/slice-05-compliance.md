---
slice: 061-05 - symmetric install + scaffold docs
pass: compliance
verdict: pass
reviewer: general-purpose
reviewed_at: 2026-06-06T01:54:56Z
prompt_source: review.py implementation <spec> 061-05 <docs>
---

VERDICT: pass

All five ACs plus the edge case are met, verified against repository reality.

- AC1 (both installs, honest): Claude `/plugin marketplace add ramboz/jig` → `/plugin install jig@jig` is valid (repo-root `.claude-plugin/marketplace.json` → `source.path: hosts/claude`, confirmed). Codex uses the proven `codex plugin marketplace add hosts/codex` → `codex plugin add jig@jig` and explicitly states there's no bare-repo one-liner (descriptor lives in the `hosts/codex` subtree, not the repo root — confirmed NO repo-root `.agents/plugins/marketplace.json`). Hook-trust (`/hooks`) + `--install-codex-agents` caveats retained. `test_codex_install_does_not_claim_bare_repo_shorthand` is a tight regression guard.
- AC2: three peers named; host packages stated committed, source-derived, drift-guarded (`build_host_packages.py [--check]`), NOT hand-edited.
- AC3: both host-package scaffold paths present; no bare repo-root invocation; `${PLUGIN_ROOT}/...` installed-plugin form correctly distinct.
- AC4: `jig-claude-vX.Y.Z.zip` (drag-drop) + `jig-codex-vX.Y.Z.zip` ("no direct zip-drop … extract-then-add").
- AC5: per-host verification pointers (Claude `verify_install.py` / `--host claude --smoke-test`, 061-06; Codex `codex_install_smoke.py`, 061-07), stating one host's check doesn't prove the other.
- Edge case: flat Claude vs marketplace-wrapped Codex stated plainly with the concrete descriptor path.

Doc-guard tests are non-trivial (positives match real commands/prose, inverse guards fire on simulated regressions, don't false-positive on legitimate host-prefixed/`${PLUGIN_ROOT}` paths).

BLOCKERS: none

NOTES:
- Committed `hosts/*/README.md` copies are regenerated build outputs (drift passes); doc-guards correctly target only the canonical README/CONTRIBUTING.
