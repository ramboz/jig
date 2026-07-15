# Plan: Spec 090

## Slice 090-01 — immutable stable-release contract

1. Accept ADR-0036 after frame critique.
2. Add failing contract fixtures for missing, stale, and malformed host-native
   stable refs, including Codex local-path preservation and the
   post-tag/default-branch drift reported in issue #98.
3. Implement one release-identity validator shared by CI, release packaging,
   and focused tests.
   Seed and verify the one-time v2.7.0 full-SHA/host-digest baseline used before
   the first immutable release exists.
4. Wire release automation to update all manifest versions and the root Claude
   stable source ref in one release change; regenerate both host packages while
   preserving the Codex local-source catalogs.
5. Configure release-please draft mode with lazy tag creation, build from its
   durable merged release commit, and add a serialized preflight that derives a
   pending transaction from the release manifest/tag gap. Validate or
   reconstruct its draft, idempotently attach assets/notes plus a durable
   `release-identity.json`, publish, verify the locked tag/assets/digests, and
   apply a workflow-owned verification checkpoint before advancing the rolling
   anchor. Document repair plus mutable-publish quarantine/version-retirement
   states.
6. Extend remote-source and archive smoke checks with deterministic tagged-tree
   identity comparisons through Claude's marketplace and plugin refs and
   Codex's marketplace ref plus local plugin path. Exercise Claude fresh install
   and tagged-source replacement plus plugin update, fresh Codex install, and
   the existing-source Codex remove/re-add transition in isolated homes.
7. Update install/release documentation and the dual-host architecture contract.
8. Run focused tests, host-package drift check, full suite, required review
   passes, and reconciliation.

## Likely deliverables

- `.claude-plugin/marketplace.json`
- `.agents/plugins/marketplace.json` contract tests (local source preserved)
- `.github/release-please-config.json`
- `.github/release-identity-baseline.json`
- `.github/workflows/release.yml`
- release identity validation and tests under `scripts/`
- `scripts/build_release_zip.py` and focused tests
- generated `hosts/` packages
- README/release and architecture documentation

Exact file ownership may change during implementation if the smallest shared
validator belongs in an existing release helper rather than a new module; any
change will be recorded in the deviation log.
