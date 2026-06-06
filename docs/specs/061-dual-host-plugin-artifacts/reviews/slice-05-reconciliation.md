---
slice: 061-05 - symmetric install + scaffold docs
pass: reconciliation
verdict: pass
reviewer: general-purpose
reviewed_at: 2026-06-06T01:56:52Z
prompt_source: review.py reconciliation <spec> 061-05
---

VERDICT: pass

Every deviation-log claim checks out against the files. The headline correction is real: README/CONTRIBUTING use `codex plugin marketplace add hosts/codex` (no bare-repo `ramboz/jig` for Codex — the only `ramboz/jig` hits are Claude's one-liner, Claude-context prose, and the `--repo-url` build flag); there is no repo-root `.agents/` (descriptor only at `hosts/codex/.agents/plugins/marketplace.json`); the repo-root `.claude-plugin/marketplace.json` points `source.path` at `hosts/claude`. Scaffold examples target the host packages, zip names are host-explicit, the verification subsection points at 061-06/07, the structural asymmetry is stated, the inverse guard exists, and the host READMEs are byte-identical to source (drift `--check` OK). Docs suite passes.

BLOCKERS: none

NOTES:
- Docs-only, drift-guarded regeneration honors the source-of-truth principle. No new TODO/FIXME; `docs/refinement-todo.md` correctly unchanged.
