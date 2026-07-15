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
label. Codex has a different boundary: its root catalog resolves a local plugin
path inside whichever Git marketplace snapshot the installer selected, while
the Codex release archive is a self-contained extract-then-add bundle.

This spec makes the release identity contract explicit: stable version
`X.Y.Z` means the bytes at immutable release tag `vX.Y.Z`. Release automation
updates every version-bearing manifest and Claude's Git-backed stable plugin
source as one transaction. Stable Claude instructions pin the marketplace
catalog at that tag as well. Stable Codex instructions pin the marketplace
snapshot with `--ref vX.Y.Z` while both Codex plugin entries remain local to
that snapshot or archive. Validation rejects drift, and remote-install and
archive smoke tests compare the resolved payload with the tagged host package.
GitHub release immutability mechanically locks the published tag and attached
archives. The host difference remains honest: Claude pins both the catalog and
a separate remote plugin fetch, while Codex pins the catalog fetch and
preserves local plugin resolution within both the repository snapshot and
extract-then-add archive.

This work originates in [GitHub issue #98](https://github.com/ramboz/jig/issues/98)
and extends the packaging contract in
[ADR-0018](../../decisions/adr-0018-dual-host-generated-plugin-artifacts.md)
through [ADR-0036](../../decisions/adr-0036-immutable-release-identity.md).

## Goals

1. Make the GitHub-locked `vX.Y.Z` tag the immutable source identity for every
   stable marketplace install labeled `X.Y.Z`.
2. Update Claude's plugin selector, stable install selectors, and all
   version-bearing manifests atomically while preserving Codex's generated
   local-source catalogs.
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
  `./hosts/codex/plugins/jig`; generated
  `hosts/codex/.agents/plugins/marketplace.json` uses `./plugins/jig`; both
  source and generated Codex plugin manifests declare version `2.7.0`.
- `scripts/build_claude_plugin.py` excludes the root Claude marketplace
  descriptor from `hosts/claude`, while `scripts/build_codex_plugin.py`
  generates the Codex host catalog with its local path. Those are host package
  contracts, not release selectors to normalize.
- Release-please updates four manifest versions, but no marketplace source
  selector. The release workflow checks out the new tag and builds deterministic
  Claude and Codex archives from the committed `hosts/<host>` packages.
- Release-please's manifest mode supports `draft: true`; with
  `force-tag-creation` false, its current documentation states that GitHub
  creates the tag lazily when the draft is published. The action exposes the
  release `sha`, `tag_name`, `version`, and `upload_url`, allowing packaging to
  preserve release-please's versioning outputs while building and attaching
  assets before the stable tag exists. See the
  [release-please manifest documentation](https://github.com/googleapis/release-please/blob/main/docs/manifest-releaser.md)
  and [action outputs](https://github.com/googleapis/release-please-action#outputs).
- The same release-please documentation warns that an unpublished draft's
  absent tag cannot serve as the previous-release marker. Recovery therefore
  uses the merged commit that uniquely advanced
  `.github/.release-please-manifest.json`, not the draft, as durable identity;
  the workflow must serialize release ownership and complete or reconstruct
  that pending transaction before release-please can calculate again.
- Release-please documents `autorelease: pending` as the pre-release-creation
  state and `autorelease: tagged` as the consumed release-PR state. Combined
  with draft presence and the durable merged commit, those labels distinguish
  first draft creation from recovery across action/label-transition crashes.
- Immutable publication and completed postcondition verification are distinct
  states. The workflow therefore needs a provisioned `jig:release-verified`
  checkpoint on the merged release PR plus a locked `release-identity.json`
  asset. Only a release with both immutable evidence and that final checkpoint
  may replace the bootstrap or previous rolling anchor; a crash between
  publication and verification must resume verification before release-please
  can advance.
- Release-please's `GenericJson` updater replaces the semantic-version
  substring in the selected JSON string rather than replacing the whole value;
  a `v` prefix around the version is therefore preserved. See the
  [updater source](https://github.com/googleapis/release-please/blob/main/src/updaters/generic-json.ts).
- The latest local release tag is `v2.7.0` at `9798faa`; later commit `a247f76`
  changes `skills/spec-workflow/workflow.py` while the version remains `2.7.0`,
  reproducing the label/payload split described in issue #98.
- The full legacy release commit is
  `9798faa1bedb97bdd69212c812bcae28af3c957e`; its release manifest and root
  Claude/Codex plugin manifests all declare 2.7.0. Because its tag is mutable,
  the migration must record and verify this exact commit plus host-package tree
  digests as a one-time bootstrap baseline. The first immutable release then
  replaces that baseline with the normal latest-immutable-release anchor.
- GitHub's release API reports `v2.7.0` as `immutable: false`; its three
  uploaded archives do have SHA-256 digests, but neither the tag nor assets are
  locked. GitHub documents that immutable releases lock both and require the
  draft → attach assets → publish order. See
  [GitHub immutable releases](https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases).
- Claude Code documents that an explicit plugin version changes only when the
  publisher bumps it, that Git-backed plugin sources support `ref` and `sha`,
  that marketplace sources independently support `ref`, and that an exact
  plugin-source `sha` wins when both are present. See
  [Claude marketplace version resolution](https://code.claude.com/docs/en/plugin-marketplaces#version-resolution-and-release-channels).
- An isolated current-CLI probe added the Claude marketplace by HTTPS URL at
  `v2.7.0`, observed the saved marketplace-source ref, then added the same
  marketplace at `main`; the source was replaced successfully. Stable Claude
  installs can therefore pin the bootstrap catalog at `vX.Y.Z`, while moving
  to another stable tag does not require an explicit remove.
- A second isolated probe used the exact proposed topology: it added only a
  matching `ref` to disposable copies of the real v2.6.0 and v2.7.0 catalogs'
  `git-subdir` entries. Claude separately fetched and installed
  `hosts/claude` at v2.6.0, replaced the tagged marketplace, then separately
  fetched v2.7.0 on `claude plugin update jig@jig`. Claude reported the 2.6.0 →
  2.7.0 transition, retained enablement, and selected the 2.7.0 cache path.
  Stable upgrade instructions must include that plugin-update step, and release
  validation must reject a new tag whose manifest version did not advance.
- The current Codex manual documents marketplace-source `--ref`, Git-backed
  plugin entries, relative local plugin entries, and local extract-then-add
  marketplaces. See
  [Codex plugin building](https://developers.openai.com/codex/plugins/build).
- An isolated current-CLI probe added `ramboz/jig` at `v2.7.0` and rejected a
  second add at `main` because marketplace `jig` was already registered from a
  different source. `marketplace remove jig` followed by a tagged re-add and
  `plugin add jig@jig` succeeded and retained the plugin's enabled state. A
  stable upgrade therefore needs this transition sequence; `marketplace
  upgrade` cannot be treated as a tag switch.

## Assumptions

Repository administrators do not concurrently disable or alter GitHub's
immutable-release setting during publication. GitHub has no documented atomic
conditional publish on that setting; the workflow can preflight it and inspect
the publish result, but a violated assumption requires permanent quarantine of
that semantic version rather than pretending the briefly public tag was always
immutable. Quarantine cannot revoke already-cached host payloads; it records
their commit/digests, marks the version unsupported, and requires a new release
PR that advances every version-bearing surface before another publication. The
recovery uses temporary release-please `last-release-sha` and `release-as`
overrides anchored to the failed commit/new version; the corrective PR removes
those overrides before merge.

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
  generated; do not hand-edit generated host files. In particular, do not
  replace either Codex local entry with a second Git fetch.

## References

- [GitHub issue #98](https://github.com/ramboz/jig/issues/98)
- [.claude-plugin/marketplace.json](../../../.claude-plugin/marketplace.json)
- [.agents/plugins/marketplace.json](../../../.agents/plugins/marketplace.json)
- [.github/release-please-config.json](../../../.github/release-please-config.json)
- [.github/workflows/release.yml](../../../.github/workflows/release.yml)
- [scripts/build_host_packages.py](../../../scripts/build_host_packages.py)
- [scripts/build_release_zip.py](../../../scripts/build_release_zip.py)
- [GitHub immutable-release setup](https://docs.github.com/en/code-security/supply-chain-security/understanding-your-software-supply-chain/preventing-changes-to-your-releases)
