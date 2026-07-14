---
status: Proposed
dependencies: []
last_verified:
frame_review: true
---

# ADR-0036: Immutable Release Identity

## Status

Proposed (2026-07-14)

## Context

Jig publishes semantic versions and release tags, but its root Claude
marketplace currently fetches `hosts/claude` from the repository default
branch without a `ref` or `sha`. The plugin manifest supplies the cache version.
Consequently, a commit made after `v2.7.0` can be installed into a cache labeled
`2.7.0`, while an existing installation with that same label may skip the new
bytes. Issue [#98](https://github.com/ramboz/jig/issues/98) records the concrete
incident.

The root Codex marketplace similarly points at a local plugin path inside the
fetched marketplace snapshot. Codex release archives differ: they already
contain a local marketplace and plugin payload, so their immutable boundary is
the tagged archive rather than a second remote fetch.

Both hosts support Git-backed plugin entries selected by `ref` or `sha`.
Claude documents that an explicit plugin version is the update key and that an
exact `sha` wins over `ref`; Codex documents versioned cache paths and
Git-backed `ref`/`sha` entries. A release commit cannot embed its own final Git
SHA without a self-reference cycle, but it can embed the release tag that will
point to that commit.

A tag name alone is not an immutable identity. GitHub's immutable-release
control locks a published release's tag to one commit, prevents the tag from
being moved or deleted while the release exists, prevents reuse of its name,
locks release assets, and emits an attestation tying the tag, commit, and
assets together. The repository's published `v2.7.0` release reports
`immutable: false`, so this control is not in force for the current release.
GitHub also requires assets to be attached to a draft before publication;
jig's current workflow publishes via release-please first and uploads archives
afterward, so enabling immutability without changing that order would break the
package job.

This decision extends [ADR-0018](./adr-0018-dual-host-generated-plugin-artifacts.md):
that ADR defines which per-host packages are shipped; this ADR defines how a
stable version identifies those package bytes.

## Decision Options Considered

### Option A: Tag-pinned sources plus GitHub immutable releases

- **Pros:** Preserves jig's existing release channel; makes the version label,
  remote source, generated package, and release archive one reviewable
  transaction; GitHub mechanically locks both the tag and uploaded assets;
  users can reason about `X.Y.Z` consistently across hosts.
- **Cons:** Requires enabling a repository-level control and changing the
  workflow to draft → attach assets → publish; release automation and tests
  must validate more coupled surfaces.

### Option B: Keep semantic versions and SHA-pin a follow-up catalog commit

- **Pros:** Plugin sources are content-addressed without relying on tag
  governance; the GitHub immutable-release setting is not required for remote
  installs.
- **Cons:** The release commit cannot contain its own SHA, so the catalog pin
  requires a second commit after the release commit exists. Version manifests
  and source identity are no longer one atomic reviewed change; archives still
  need a separate immutability control.

### Option C: Omit semantic versions and use commit-SHA versions

- **Pros:** Every default-branch commit is content-addressed automatically;
  there is no version/ref synchronization step.
- **Cons:** Changes jig from stable releases to rolling every-commit updates,
  weakens release-note and archive alignment, and changes the user-facing
  distribution model beyond the reported problem.

### Option D: Keep unpinned sources and rely on version bumps

- **Pros:** No release-pipeline change.
- **Cons:** The version and fetched bytes remain independently mutable; a
  post-tag commit can reproduce the exact failure from issue #98.

## Recommended Decision

Adopt **Option A**.

For stable version `X.Y.Z`, every root marketplace entry that fetches jig
plugin content from Git must select release tag `vX.Y.Z`. All root and generated
plugin manifest versions, stable marketplace source refs, and committed host
packages are one release transaction. A release identity validator must reject
missing or mismatched refs, versions, tags, packages, and archives before
publication.

Before the next release, enable GitHub immutable releases for the repository.
Change the release flow to create a draft release at `vX.Y.Z`, build and attach
both host archives, then publish. After publication, verify that GitHub reports
the release as immutable and that its locked tag commit matches the commit used
for source and archive identity checks. A release that cannot establish those
conditions is failed, not advertised as stable.

The identity target is the tagged host package:

- Claude remote install and Claude archive both identify `hosts/claude` at
  `vX.Y.Z`.
- Codex remote install identifies `hosts/codex/plugins/jig` at `vX.Y.Z`.
- The Codex archive keeps its local extract-then-add marketplace because the
  tagged archive already seals `hosts/codex`; its plugin payload must match the
  same tagged directory.

Development checkouts and local marketplaces may remain moving inputs, but
documentation must not present them as the stable release channel.

## Consequences

**Becomes easier:**

- A version label has one cross-host payload identity.
- Fresh install, reinstall, cache lookup, and release archive can be compared
  against the same tag and deterministic tree digest.
- Contract tests can fail at the release boundary instead of relying on manual
  publisher discipline.
- Published tags and archives gain GitHub-enforced immutability plus a native
  release attestation.

**Becomes harder:**

- Version bumps must update marketplace refs and regenerate host packages in
  the same change.
- Release tooling owns a stricter cross-file invariant and must report all
  drift clearly.
- The release workflow must attach all assets while the release is still a
  draft; post-publication asset edits are intentionally unavailable.
- Repository release immutability is an external prerequisite that code alone
  cannot enable safely on the maintainer's behalf.

## Assumptions

<!-- Spec 064-02 / ADR-0020 §1–§2 — grounding-by-probe (risk-gated). -->

_Load-bearing factual claims about runnable surfaces (library/API capability,
version/perf behavior, behavior of existing code) must be backed by an executed
probe (run a command, read source/`node_modules`) or a citation — or listed
here explicitly as an assumption. Never assert an unverified claim as fact._

_Risk-gated: omit this section (or write "None") when the decision has no
unverified load-bearing assumptions — do not pad with boilerplate._

None. Current repository and release metadata were probed directly; platform
claims are backed by current first-party documentation:

- [Claude marketplace version resolution](https://code.claude.com/docs/en/plugin-marketplaces#version-resolution-and-release-channels)
- [Codex plugin building](https://developers.openai.com/codex/plugins/build)
- [GitHub immutable releases](https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases)
- [GitHub immutable-release setup](https://docs.github.com/en/code-security/supply-chain-security/understanding-your-software-supply-chain/preventing-changes-to-your-releases)

## Kill criteria

_What would make this decision wrong? List the conditions that, if observed,
should reverse or shelve it. Risk-gated like Assumptions — write "None" or omit
when there is no meaningful kill condition; do not invent ceremonial ones._

- A host adopts a stronger native immutable-package identifier that makes the
  Git tag indirection redundant and can preserve the same stable-release user
  experience.
- Jig deliberately abandons semantic releases for a rolling commit-addressed
  channel through a superseding ADR.
- GitHub removes or materially weakens immutable releases, and no equivalent
  tag-and-asset locking control is available.

## Open questions

None.
