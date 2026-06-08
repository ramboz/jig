---
slice: 061-07 - Codex install verification
pass: compliance
verdict: pass
reviewer: codex
reviewed_at: 2026-06-08T19:03:18Z
prompt_source: Codex live validation of slice 061-07
---

VERDICT: pass

All five acceptance criteria are met by the existing Codex smoke tooling plus
the live Codex run in this environment.

- AC1: `python3 scripts/codex_install_smoke.py --use-committed-package
  --require-live-codex --keep-work --timeout 60` validated the committed
  `hosts/codex/plugins/jig` package, including
  `.agents/plugins/marketplace.json`, `plugins/jig/.codex-plugin/plugin.json`,
  rendered skills, hooks, hook scripts, and marketplace descriptor coherence.
- AC2: `python3 scripts/build_release_zip.py --host codex --version 1.12.0`
  built `jig-codex-v1.12.0.zip`, and
  `python3 scripts/build_release_zip.py --host codex --smoke-test <zip>`
  validated the extracted marketplace bundle.
- AC3: A real Codex CLI was available (`codex-cli 0.133.0`). The isolated
  `CODEX_HOME` probe ran `codex plugin marketplace add hosts/codex`,
  `codex plugin add jig@jig`, confirmed installed hook config, checked
  representative skill visibility through `codex debug prompt-input`, and
  reported hook-trust state.
- AC4: The deterministic fallback path remains covered by
  `scripts/test_codex_install_smoke.py`; the live run did not need to fall back
  because the Codex surface was available.
- AC5: Smoke result names are Codex-specific (`codex-cli`,
  `codex-marketplace-add`, `codex-plugin-add`, `codex-hook-config`,
  `codex-skill-visibility`, `codex-hook-trust-state`), so diagnostics cannot
  be mistaken for Claude failures.

BLOCKERS: none

NOTES:
- The hook-trust caveat is explicitly documented: `README.md` and the packaged
  `hosts/codex/plugins/jig/README.md` tell users to open `/hooks` and trust
  plugin-bundled hooks before they run; `.codex-plugin/plugin.json` carries the
  same requirement in its long description.
