---
status: DRAFT
skill: release-pipeline, scaffold-init
tier: host-adapter
adr_required: true
adr: ../../decisions/adr-0018-dual-host-generated-plugin-artifacts.md
---

# Spec 061: Dual-host plugin artifacts

## Overview

Spec 033 made Codex a supported host and Spec 059 polished the Codex
runtime contract. The remaining imbalance is delivery shape:

- Claude's release zip is currently built directly from the repo root.
- Codex already has a generated marketplace tree under `dist/codex-plugin/`.
- The repo root now looks partly like source and partly like an install
  artifact, which makes the Claude and Codex paths feel asymmetrical.

This spec makes the delivery architecture explicit:

```text
canonical source tree
  -> dist/claude-plugin/
  -> dist/codex-plugin/
```

Both host artifacts are generated, disposable build outputs. The source
tree remains the canonical place to edit skills, agents, hooks,
templates, and host manifests. Install, scaffold, smoke-test, and release
instructions point at the generated host artifact, not at the source
root by accident.

The architectural decision is recorded in
[ADR-0018](../../decisions/adr-0018-dual-host-generated-plugin-artifacts.md).

## Goals

1. **Generate both host artifacts.** Claude gets a generated
   `dist/claude-plugin/` tree just like Codex gets `dist/codex-plugin/`.
2. **Keep artifact names balanced.** Use host names for folders and
   release assets: `claude-plugin`, `codex-plugin`,
   `jig-claude-vX.Y.Z.zip`, and `jig-codex-vX.Y.Z.zip`.
3. **Preserve honest Codex delivery semantics.** The Codex zip is an
   extract-then-add marketplace bundle, not a direct zip install.
4. **Point scaffold installs at artifacts.** Local/development scaffold
   commands should run from the relevant generated artifact path:
   `dist/claude-plugin/...` for Claude and
   `dist/codex-plugin/plugins/jig/...` for Codex.
5. **Verify each host in its own environment.** Claude and Codex each
   get a dedicated final verification slice so a spec authored in one
   host does not stand in for proof that the other host installs and
   runs correctly.
6. **Keep source canonical.** Build outputs should be reproducible from
   the root tree and safe to delete.

## Non-goals

- **No direct Codex zip install claim.** Current Codex documentation does
  not document direct zip plugin installation. This spec must not imply
  otherwise.
- **No plugin-native Codex agent discovery.** Spec 059-06 confirmed the
  explicit `--install-codex-agents` helper remains the supported
  contract.
- **No broad source-tree relocation.** This spec may introduce builders
  and artifact contracts without moving every checked-in manifest into a
  new `manifests/` hierarchy.
- **No change to scaffolded project contents.** The generated artifacts
  are install sources; scaffold output should remain host-shaped exactly
  as Specs 033 and 059 define it.
- **No checked-in `dist/` artifacts.** `dist/` remains generated output.

## Current state verified 2026-06-05

- `scripts/build_release_zip.py` creates `jig-vX.Y.Z.zip` directly from
  the source root. It includes both `.claude-plugin/` and
  `.codex-plugin/` plus shared runtime folders.
- `.github/workflows/release.yml` uploads only
  `dist/jig-vX.Y.Z.zip`.
- `scripts/build_codex_plugin.py` materializes
  `dist/codex-plugin/plugins/jig/` and writes the Codex marketplace
  descriptor at `dist/codex-plugin/.agents/plugins/marketplace.json`.
- README already documents installing the generated Codex marketplace
  with `codex plugin marketplace add dist/codex-plugin`.
- No equivalent generated Claude artifact exists yet.

## Decomposition

**Suggested SPIDR axis: Interface.** Each slice stabilizes one external
interface: generated artifact shape, release/archive naming,
artifact-first documentation, and host-specific install verification.

## Slices

- [061-01 - `dist/claude-plugin` generated artifact](slice-01-claude-generated-artifact.md)
- [061-02 - host-explicit release archives](slice-02-host-explicit-release-archives.md)
- [061-03 - artifact-first install docs](slice-03-artifact-first-install-docs.md)
- [061-04 - Claude artifact install verification](slice-04-claude-artifact-install-verification.md)
- [061-05 - Codex artifact install verification](slice-05-codex-artifact-install-verification.md)

## Dependencies / coordination

- Implements [ADR-0018](../../decisions/adr-0018-dual-host-generated-plugin-artifacts.md).
- Coordinate with [Spec 013](../013-release-pipeline/spec.md) because it
  owns release zip creation and GitHub release upload.
- Coordinate with [Spec 033](../033-host-adapter-portability/spec.md)
  because it introduced the Codex build artifact and host renderer
  boundary.
- Coordinate with [Spec 047](../047-install-contract-verification/spec.md)
  so install/release validators keep checking the full plugin contract
  after the source-root-to-dist cutover.
- Coordinate with [Spec 059](../059-codex-port-polish/spec.md) so Codex
  docs keep the hook trust and explicit agent-install caveats.

## References

- [scripts/build_release_zip.py](../../../scripts/build_release_zip.py)
- [scripts/build_codex_plugin.py](../../../scripts/build_codex_plugin.py)
- [scripts/install_contract.py](../../../scripts/install_contract.py)
- [scripts/codex_install_smoke.py](../../../scripts/codex_install_smoke.py)
- [.github/workflows/release.yml](../../../.github/workflows/release.yml)
- [README.md](../../../README.md)
- [ADR-0018: Dual-host generated plugin artifacts](../../decisions/adr-0018-dual-host-generated-plugin-artifacts.md)
