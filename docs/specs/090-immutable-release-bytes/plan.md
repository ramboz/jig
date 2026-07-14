# Plan: Spec 090

## Slice 090-01 — immutable stable-release contract

1. Accept ADR-0036 after frame critique.
2. Add failing contract fixtures for missing, stale, and malformed stable refs,
   including the post-tag/default-branch drift reported in issue #98.
3. Implement one release-identity validator shared by CI, release packaging,
   and focused tests.
4. Wire release automation to update all manifest versions and both root stable
   source refs in one release change; regenerate host packages from root source.
5. Replace publish-then-upload with draft → attach validated assets → publish,
   then verify GitHub locked the tag/assets and reports matching digests.
6. Extend remote-source and archive smoke checks with deterministic tagged-tree
   identity comparisons for Claude and Codex.
7. Update install/release documentation and the dual-host architecture contract.
8. Run focused tests, host-package drift check, full suite, required review
   passes, and reconciliation.

## Likely deliverables

- `.claude-plugin/marketplace.json`
- `.agents/plugins/marketplace.json`
- `.github/release-please-config.json`
- `.github/workflows/release.yml`
- release identity validation and tests under `scripts/`
- `scripts/build_release_zip.py` and focused tests
- generated `hosts/` packages
- README/release and architecture documentation

Exact file ownership may change during implementation if the smallest shared
validator belongs in an existing release helper rather than a new module; any
change will be recorded in the deviation log.
