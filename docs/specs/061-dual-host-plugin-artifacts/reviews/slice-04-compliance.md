---
slice: 061-04 - host-explicit release zips
pass: compliance
verdict: pass
reviewer: general-purpose
reviewed_at: 2026-06-05T23:54:33Z
prompt_source: review.py implementation <spec> host-explicit <deliverables>
---

VERDICT: pass

All five acceptance criteria for slice 061-04 are met by `scripts/build_release_zip.py` and `.github/workflows/release.yml`, with tests that exercise each AC against real builds of the committed `hosts/` packages.

- AC1 (Claude flat at root): `_iter_files` yields paths relative to the package root → `.claude-plugin/plugin.json` at zip root. Verified by `test_claude_plugin_json_at_root`, `test_no_wrapping_directory`, `test_no_hosts_prefix`, `test_runtime_dirs_present`.
- AC2 (Codex marketplace root): `.agents/plugins/marketplace.json` + `plugins/jig/.codex-plugin/plugin.json` both at root, no `hosts/` prefix.
- AC3 (exact extract-then-add language): asserted positively (presence of "extract-then-add") and negatively (absence of "directly-installable"/"drag-droppable") across builder output, smoke output, and release.yml notes.
- AC4 (version coherence): `_read_manifest_version` reads each host's own committed manifest; mismatch exits 2 with "mislabeled" and writes no zip. Stale-`hosts/` edge case tested by `test_stale_hosts_tree_fails_coherence`.
- AC5 (workflow uploads both): release.yml builds/smokes/uploads `jig-claude`, `jig-codex`, and the byte-identical legacy `jig-v` alias (`cp`); legacy decision recorded in the deviation log per the either/or.

BLOCKERS: none

NOTES:
- release.yml heredoc body is indented; appended release-note lines carry leading whitespace into the release body but render fine as Markdown list continuation. Cosmetic.
- Claude smoke-validator swap (`validate_claude_package` instead of `verify_install.run_headless`) is a well-justified deviation, already in the deviation log — correct validator for the post-061-01 committed package shape.
