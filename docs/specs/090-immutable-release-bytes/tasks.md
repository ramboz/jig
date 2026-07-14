# Tasks: Spec 090

## Planning and decision

- [x] Inspect issue #98 and related release evidence.
- [x] Verify the distinct Claude plugin-source and Codex marketplace-source
      mechanisms from first-party docs and local builders.
- [x] Probe Codex fresh tagged add, ref-collision failure, and remove/re-add
      transition in an isolated `CODEX_HOME`.
- [x] Probe Claude tagged marketplace add, persisted catalog ref, and same-name
      ref replacement in an isolated `CLAUDE_CONFIG_DIR`.
- [x] Probe the exact Claude two-pin topology from v2.6.0 to v2.7.0 via tagged
      marketplace replacement, separately pinned `git-subdir`, and plugin
      update.
- [x] Probe current manifests, release automation, packages, and archives.
- [x] Verify release-please draft mode, lazy tag creation, and release output
      contract from its current first-party documentation.
- [x] Verify the v2.7.0 full commit and release/plugin manifest versions for the
      one-time migration anchor.
- [x] Draft spec 090 and SPIDR decomposition.
- [x] Draft ADR-0036.
- [x] Run ADR frame critique and record the passing evidence.
- [x] Accept ADR-0036 after maintainer approval.
- [ ] Obtain maintainer approval for the GitHub immutable-release setting.
- [ ] Review the spec and transition 090-01 to `READY_FOR_IMPLEMENTATION`.

## Implementation

- [ ] Write failing release-identity contract tests.
- [ ] Add and validate the reviewed v2.7.0 full-SHA/host-digest bootstrap
      baseline, then retire its active use after the first immutable release.
- [ ] Implement atomic version/Claude-ref synchronization and Codex local-source
      preservation.
- [ ] Add CI and release-workflow drift gates.
- [ ] Configure release-please draft/lazy-tag mode; build from its reported SHA;
      attach archives plus `release-identity.json`, publish, and verify final
      GitHub immutability/digests.
- [ ] Serialize the release lane; implement existing-draft resume, ambiguous
      state refusal, durable manifest/commit recovery, draft reconstruction,
      workflow-owned `jig:release-verified` provisioning/checkpointing,
      publication-to-verification crash injection, and explicit repair runbook
      coverage.
- [ ] Preflight the immutable-release setting and cover mutable-publish
      quarantine, payload-digest tombstone, consumer update guidance, cleanup,
      and corrective release-PR recovery using temporary `last-release-sha` and
      `release-as` controls removed before merge.
- [ ] Add Claude catalog/plugin-ref and Codex marketplace-ref tagged-tree
      identity smoke.
- [ ] Cover Claude fresh install and tagged marketplace replacement plus plugin
      update lifecycle.
- [ ] Cover Codex fresh install and existing-source remove/re-add lifecycle.
- [ ] Add archive tagged-tree identity smoke.
- [ ] Regenerate both host packages.
- [ ] Update install, release, and architecture docs.

## Verification and close-out

- [ ] Run focused release/package tests.
- [ ] Run host-package drift check.
- [ ] Run full test suite.
- [ ] Complete compliance, craft, arch, and code-health reviews.
- [ ] Reconcile, record review evidence, and close the slice.
