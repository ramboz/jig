# Tasks: Spec 090

## Planning and decision

- [x] Inspect issue #98 and related release evidence.
- [x] Verify Claude and Codex marketplace capabilities from first-party docs.
- [x] Probe current manifests, release automation, packages, and archives.
- [x] Draft spec 090 and SPIDR decomposition.
- [x] Draft ADR-0036.
- [x] Run ADR frame critique and record the passing evidence.
- [ ] Accept ADR-0036 after maintainer approval.
- [ ] Obtain maintainer approval for the GitHub immutable-release setting.
- [ ] Review the spec and transition 090-01 to `READY_FOR_IMPLEMENTATION`.

## Implementation

- [ ] Write failing release-identity contract tests.
- [ ] Implement atomic version/ref synchronization.
- [ ] Add CI and release-workflow drift gates.
- [ ] Convert release publication to draft → attach → publish and verify the
      final GitHub immutability/digest state.
- [ ] Add remote-source tagged-tree identity smoke.
- [ ] Add archive tagged-tree identity smoke.
- [ ] Regenerate both host packages.
- [ ] Update install, release, and architecture docs.

## Verification and close-out

- [ ] Run focused release/package tests.
- [ ] Run host-package drift check.
- [ ] Run full test suite.
- [ ] Complete compliance, craft, arch, and code-health reviews.
- [ ] Reconcile, record review evidence, and close the slice.
