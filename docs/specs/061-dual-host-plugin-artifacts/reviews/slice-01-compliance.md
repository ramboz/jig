---
slice: 061-01 - committed Claude package + repoint marketplace
pass: compliance
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-06-05T20:52:22Z
prompt_source: review.py implementation <slice> 061-01 <deliverables>
---

All five ACs met and exercised by meaningful tests built against the real source tree (no mocks).
- AC1 reuse-not-restate: identity test pins build_release_zip._is_excluded_dir/_file.
- AC2 runtime-only: excludes verified incl. .codex-plugin + root marketplace.json absence; nested runtime paths (hooks/scripts/, templates/docs/) preserved.
- AC3 repoint: git-subdir path -> hosts/claude committed + re-validated.
- AC4 unsafe-output guards + atomic stale-tree replacement tested.
- AC5 positive validate_claude_package helper added.
Deviation log honest; drift guard correctly scoped to 061-03.

Non-blocking: leak test (test_build_claude_plugin.py:80-89) uses install_contract.is_excluded_release_path rather than the builder's own predicates — sets agree today; slightly weaker scan, no leak in practice.
Follow-up for 061-03: add a status-board Notes invariant that the committed hosts/claude version must be rebuilt on version bump (only 061-03 CI catches drift).
