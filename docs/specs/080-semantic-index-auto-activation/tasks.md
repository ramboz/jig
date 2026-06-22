# Spec 080 Tasks

## 080-03 - Codex adapter activation

- [x] Re-open deferred slice `080-03` and move it to `IN_PROGRESS`.
- [x] Re-read 033 Codex scaffold/plugin adapter surfaces and 080 semantic-index
      contract/helper surfaces.
- [x] Add Codex scaffold tests for semantic-index hook registration,
      `host="codex"` activation, Codex one-time suggestion state, and public
      semantic-index primer guidance with no Scout prose.
- [x] Add Codex committed-package tests proving plugin packaging rewrites the
      semantic-index hook script and registers it in rendered `hooks.json`.
- [x] Update `CodexScaffoldRenderer` hook-script rewriting for Codex host
      activation and Codex suggestion state.
- [x] Update `build_codex_plugin.py` to rewrite copied hook scripts, not only
      `hooks.json`.
- [x] Add semantic-index public-provider guidance to `AGENTS.md.template`.
- [x] Rebuild committed host packages.
- [x] Run focused Codex scaffold/package tests.
- [x] Run shared semantic-index, Codex install smoke, scaffold, host-package
      drift, host-package check, and spec-lint verification.
- [x] Run compliance, craft, and architecture review passes.
- [x] Record compliance, craft, and architecture review evidence.
- [x] Reconcile docs/deviation log and run reconciliation review.
- [x] Transition `080-03` through `REVIEWED` and `RECONCILED`.

## 080-04 - usage attribution digest

- [x] Claim slice `080-04` and move it to `IN_PROGRESS`.
- [x] Re-read `scripts/usage.py` report/top/read-attribution surfaces.
- [x] Re-read 080-01 semantic-index telemetry schema and tests.
- [x] Add semantic-index activation digest builder and renderer.
- [x] Add `usage.py semantic-index` CLI command with fixture-friendly
      overrides.
- [x] Add synthetic tests for empty telemetry, mixed providers/hosts/profiles,
      overlay-disabled rows, malformed rows, missing transcript data, read/search
      proxies, time-window filtering, and no content leakage.
- [x] Run focused usage tests.
- [x] Run script test discovery, semantic-index helper tests, and spec lint.
- [x] Run compliance and craft review passes.
- [x] Record compliance and craft review evidence.
- [x] Reconcile reviewer finding about stale task checklist state.
- [x] Record reconciliation review evidence.
- [x] Transition `080-04` through `REVIEWED`, `RECONCILED`, and `DONE`.
