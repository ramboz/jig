---
status: DRAFT
skill: release-pipeline
use_cases: []
adr_required: true
adr: ../../decisions/adr-0036-immutable-release-identity.md
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 090: Immutable-release bytes

## Overview

Jig's stable release label does not currently identify one immutable payload.
The Claude marketplace resolves `hosts/claude` from the repository's default
branch while `.claude-plugin/plugin.json` declares a semantic version. After a
tag is cut, later commits can therefore be installed under the old version
label. The root Codex marketplace has the same shape through a local path into
the fetched marketplace snapshot, while the Codex release archive is already a
self-contained extract-then-add bundle.

This spec makes the release identity contract explicit: stable version
`X.Y.Z` means the bytes at immutable release tag `vX.Y.Z`. Release automation updates
every version-bearing manifest and both Git-backed stable marketplace entries
as one transaction; validation rejects drift; remote-install and archive smoke
tests compare the resolved payload with the tagged host package. GitHub release
immutability mechanically locks the published tag and attached archives. The host
difference remains honest: Claude has a remotely pinned plugin source and a
flat archive, while Codex has a remotely pinned plugin source plus a local,
extract-then-add archive marketplace.

This work originates in [GitHub issue #98](https://github.com/ramboz/jig/issues/98)
and extends the packaging contract in
[ADR-0018](../../decisions/adr-0018-dual-host-generated-plugin-artifacts.md)
through [ADR-0036](../../decisions/adr-0036-immutable-release-identity.md).

## Goals

1. Make the GitHub-locked `vX.Y.Z` tag the immutable source identity for every
   stable marketplace install labeled `X.Y.Z`.
2. Update source selectors and all version-bearing manifests atomically in the
   release change.
3. Fail contract checks when any release version, source selector, tag, or
   packaged payload disagrees.
4. Publish through a draft-first immutable-release flow and prove that remote
   marketplace resolution and both release archives contain the locked tag's
   host-package bytes.
5. Document the Claude and Codex install boundaries without implying that
   Codex supports direct zip installation.

## Non-goals

- No rolling every-main-commit release channel. Development checkouts may move;
  the stable channel remains semantic-versioned.
- No separate signing service or software bill of materials. GitHub's native
  immutable-release attestation is accepted as part of the chosen platform
  control, but a broader supply-chain system is out of scope.
- No change to scaffolded project contents or Codex's explicit custom-agent
  installation contract.

## Current state verified 2026-07-14

- Root `.claude-plugin/marketplace.json` uses a `git-subdir` source for
  `hosts/claude` with neither `ref` nor `sha`; both source and generated Claude
  plugin manifests declare version `2.7.0`.
- Root `.agents/plugins/marketplace.json` uses a local source at
  `./hosts/codex/plugins/jig`; both source and generated Codex plugin manifests
  declare version `2.7.0`.
- Release-please updates four manifest versions, but no marketplace source
  selector. The release workflow checks out the new tag and builds deterministic
  Claude and Codex archives from the committed `hosts/<host>` packages.
- Release-please's `GenericJson` updater replaces the semantic-version
  substring in the selected JSON string rather than replacing the whole value;
  a `v` prefix around the version is therefore preserved. See the
  [updater source](https://github.com/googleapis/release-please/blob/main/src/updaters/generic-json.ts).
- The latest local release tag is `v2.7.0` at `9798faa`; later commit `a247f76`
  changes `skills/spec-workflow/workflow.py` while the version remains `2.7.0`,
  reproducing the label/payload split described in issue #98.
- GitHub's release API reports `v2.7.0` as `immutable: false`; its three
  uploaded archives do have SHA-256 digests, but neither the tag nor assets are
  locked. GitHub documents that immutable releases lock both and require the
  draft → attach assets → publish order. See
  [GitHub immutable releases](https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases).
- Claude Code documents that an explicit plugin version changes only when the
  publisher bumps it, that Git-backed plugin sources support `ref` and `sha`,
  and that an exact `sha` wins when both are present. See
  [Claude marketplace version resolution](https://code.claude.com/docs/en/plugin-marketplaces#version-resolution-and-release-channels).
- The current Codex manual documents Git-backed marketplace entries with
  `ref`/`sha`, marketplace-source `--ref`, versioned cache paths, and local
  extract-then-add marketplaces. See
  [Codex plugin building](https://developers.openai.com/codex/plugins/build).

## Assumptions

None.

## Decomposition

**SPIDR analysis:** Path, Interface, Data, and Rules splits were considered.
A host split would create an intermediate release where Claude and Codex could
still disagree; an automation/tests/docs split would be horizontal phasing.
The smallest end-to-end unit is therefore one slice spanning the stable release
path for both host interfaces: source selection, atomic versioning, validation,
archive/remote smoke, and user-facing release documentation. No spike is needed
because both host contracts and the current implementation are directly
inspectable.

## Slices

- [090-01 — immutable stable-release contract](slice-01-immutable-stable-release-contract.md)

## Dependencies / coordination

- [ADR-0036](../../decisions/adr-0036-immutable-release-identity.md) must be
  Accepted before implementation begins.
- Coordinate with [spec 013](../013-release-pipeline/spec.md) for
  release-please behavior and [spec 061](../061-dual-host-plugin-artifacts/spec.md)
  for generated host packages and archive semantics.
- Preserve ADR-0018's rule that root source is canonical and `hosts/<host>` is
  generated; do not hand-edit generated host files.

## References

- [GitHub issue #98](https://github.com/ramboz/jig/issues/98)
- [.claude-plugin/marketplace.json](../../../.claude-plugin/marketplace.json)
- [.agents/plugins/marketplace.json](../../../.agents/plugins/marketplace.json)
- [.github/release-please-config.json](../../../.github/release-please-config.json)
- [.github/workflows/release.yml](../../../.github/workflows/release.yml)
- [scripts/build_host_packages.py](../../../scripts/build_host_packages.py)
- [scripts/build_release_zip.py](../../../scripts/build_release_zip.py)
- [GitHub immutable-release setup](https://docs.github.com/en/code-security/supply-chain-security/understanding-your-software-supply-chain/preventing-changes-to-your-releases)
