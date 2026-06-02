---
slice: 047-01 - plugin-release-contract-validator
pass: compliance
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-06-02T18:29:48Z
prompt_source: skills/independent-review/review.py implementation 047-01
---

VERDICT: pass

REASONING:
All four acceptance criteria are met by a clean, stdlib-only design that consolidates the plugin/release contract into one validator-facing module (`install_contract.py`) and wires it into the three validators (`validate_manifests.py`, `verify_install.py`, `test_build_release_zip.py`). Tests exercise each AC meaningfully — failure-mode fixtures strip individual artifacts and assert both the offending path *and* the expected rule appear in diagnostics — and the restated contract sets are pinned to their real sources of truth by consistency tests (verified: `EXPECTED_SKILLS` == `_TIER_SKILLS` union = 15 skills; `_EXPECTED_HOOK_SCRIPTS` == the 9 scripts hooks.json registers, correctly now including `jig-skill-trace.sh`). The "at least one" shallow checks the spec called out as the core problem are genuinely replaced with full-contract assertions, and the edge cases in `_validate_source_path` (relative `.`, `..`-escape, absolute string/object, missing path) are handled correctly with no false positives.

SPECIFIC ISSUES:
- `docs/specs/047-install-contract-verification/slice-01-plugin-release-contract-validator.md:58` — Deviation log is still `_TODO._`. Reconciliation-phase artifact (DoD item, not an implementation-correctness blocker); must be filled before RECONCILED/DONE. (Medium confidence; not blocking the implementation pass.)
- `scripts/install_contract.py:194` — Minor: AC #1 mentions "version where applicable" for manifests. `validate_marketplace_manifest` does not require a `version` on marketplace plugin entries. Defensible ("where applicable" — the real `marketplace.json` carries no per-entry version and Claude's marketplace schema doesn't require one); reads as a deliberate scope decision. No change required.

RECONCILIATION NOTES:
- The slice also corrected a pre-existing drift bug (`verify_install._EXPECTED_HOOK_SCRIPTS` was missing `jig-skill-trace.sh`, registered since spec 030) and added `HookScriptDriftConsistencyTests`. In-scope for the slice's "strengthen hook validation" goal but a behavior change beyond pure addition — worth an explicit deviation-log line.
- Plugin-mode `verify_install` previously validated no hooks at all; this slice adds a fifth check (`check_hook_contract`) to `_CHECKS`. `_make_fake_plugin_root` was extended to emit a full hooks.json + scripts. Note the plugin-mode check count went 4→5.
- `validate_manifests.py` now routes plugin.json/marketplace.json through `install_contract` validators rather than the old bare `required_fields` mechanism (retained but unused by the two real manifest specs). Intended "contract in one place" approach (Goal 1); faithful to the stated approach.

— reviewer: jig:reviewer (read-only, fresh context); compliance pass.
