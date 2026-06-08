---
slice: 061-06 - Claude install verification
pass: compliance
verdict: pass
reviewer: general-purpose
reviewed_at: 2026-06-08T17:04:10Z
prompt_source: review.py implementation <spec> 061-06 <deliverables>
---

VERDICT: pass

All six ACs are met by scripts/claude_install_smoke.py and meaningfully exercised by scripts/test_claude_install_smoke.py with injected runners + a stub CLI; tests neither depend on the real `claude` binary nor mutate global Claude config (read-only `plugin validate` only).

- AC1: `_validate_committed_package` = `validate_claude_package` + `_DEV_ONLY_DIRS` guard. Tests: clean pass, `.codex-plugin/` fail, in-package marketplace fail, dev-dir fail, real package pass.
- AC2: `_validate_remote_pointer` validates the manifest then asserts source path `== "hosts/claude"` (handles dict + string source), `!= "."`. Tests: hosts/claude pass, "." fail, real root pass.
- AC3: `_validate_release_archive` builds via build_release_zip.build, extracts, asserts flat `.claude-plugin/plugin.json` + contract. Tests: built-zip pass, nested-zip fail.
- AC4: `_probe_live_claude` records `--version` then read-only `plugin validate` on package/marketplace/extracted-zip; no marketplace add/install. Test asserts command + version recorded.
- AC5: UNAVAILABLE on missing CLI; deterministic substitute (4 static checks) always runs as pass/fail basis; scaffold-helper execution via `_validate_scaffold_helper`. Tests: missing-CLI-unavailable + substitute-passes, skip-flag, real helper runs, missing helper fails.
- AC6: every result `claude-`-prefixed; failures name "Claude"; unrecognized subcommand degrades to UNAVAILABLE not FAIL.

BLOCKERS: none

NOTES:
- `run_smoke` accepts `require_live_claude` but only `exit_code` consumes it (dead param, mirrored from the Codex sibling) — harmless.
- `--require-live-claude` exit-2 path unit-covered via direct `exit_code`, not end-to-end through `main`; behavior still verified.
