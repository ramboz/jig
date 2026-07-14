---
status: Accepted
dependencies: []
last_verified: 2026-07-14
frame_review: true
---

# ADR-0036: Immutable Release Identity

## Status

Accepted (2026-07-14)

## Context

Jig publishes semantic versions and release tags, but its root Claude
marketplace currently fetches `hosts/claude` from the repository default
branch without a `ref` or `sha`. The plugin manifest supplies the cache version.
Consequently, a commit made after `v2.7.0` can be installed into a cache labeled
`2.7.0`, while an existing installation with that same label may skip the new
bytes. Issue [#98](https://github.com/ramboz/jig/issues/98) records the concrete
incident.

The two host mechanisms are not symmetric:

- Claude first loads the repository-root marketplace catalog, then performs a
  separate `git-subdir` fetch for the plugin source at `hosts/claude`. The
  package builder deliberately excludes the root marketplace descriptor from
  `hosts/claude`. Stable installs must pin both fetches: the marketplace source
  selected by the install command and the plugin source declared by the
  catalog.
- Codex adds a Git marketplace snapshot, then resolves the root catalog's
  `source: local` path at `./hosts/codex/plugins/jig` within that snapshot. The
  generated catalog at `hosts/codex/.agents/plugins/marketplace.json` likewise
  uses a package-relative local path, `./plugins/jig`; that shape is also the
  extract-then-add release-archive contract. The stable Git selector belongs
  on `codex plugin marketplace add ... --ref vX.Y.Z`, not on either local
  plugin entry.

Codex includes the selected ref in marketplace source identity. A disposable
`CODEX_HOME` probe against this repository added `jig` at `v2.7.0`, then
rejected an add at `main` with "already added from a different source; remove
it before adding this source." Removing marketplace `jig`, re-adding it at the
new ref, and running `codex plugin add jig@jig` succeeded; the existing plugin
enablement remained in config and resolved from the newly selected snapshot.
Thus a stable tag pin also requires an explicit transition contract for users
who already have an unpinned or older tagged marketplace.

Claude likewise supports a marketplace-source ref, using `owner/repo@ref` or
`git-url#ref`, independently of the catalog's plugin-source ref. A disposable
`CLAUDE_CONFIG_DIR` probe added this repository from its HTTPS URL at
`v2.7.0`, verified that the saved marketplace source carried that ref, then
added the same marketplace name at `main`; the current CLI replaced the source
successfully. Therefore Claude's stable command can pin the bootstrap catalog
without changing the generated Claude package or requiring a remove step.

Marketplace replacement alone does not update an already-cached Claude plugin.
An exact-topology isolated probe cloned the real `v2.6.0` and `v2.7.0`
marketplace snapshots and injected only the proposed matching `ref` field into
each disposable cached `git-subdir` entry. Claude separately fetched
`hosts/claude` at `v2.6.0`, installed jig 2.6.0, replaced the marketplace with
`v2.7.0`, separately fetched that plugin ref on `claude plugin update jig@jig`,
then reported 2.6.0 → 2.7.0, retained enablement, and selected the 2.7.0 cache
path. The stable transition therefore requires both an explicit plugin update
and a semantic-version bump; re-pointing a catalog to new bytes under the same
manifest version remains invalid.

Claude documents that an explicit plugin version is the update key and that an
exact plugin-source `sha` wins over `ref`. Codex documents marketplace-source
`--ref`, Git-backed plugin entries, and local plugin entries resolved relative
to the catalog. A release commit cannot embed its own final Git SHA without a
self-reference cycle, but it can embed the release tag that will point to that
commit.

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

Release-please has a supported draft handoff that preserves its release PR,
version, changelog, and release-note generation. Its manifest configuration
supports `draft: true`; with `force-tag-creation` left false, its documentation
states that GitHub creates the tag lazily when the draft is published. The v4
action exposes `release_created`, `tag_name`, `version`, `sha`, and `upload_url`
for the created release. Jig can therefore build from the action's exact `sha`,
attach assets to the draft release, and publish only after validation, without
exposing an unlocked stable tag during packaging.

Release-please also warns that a tagless draft is not discoverable as the
previous release on a later release-please run. The draft cannot be the durable
handoff record. The source of truth is the merged release commit that uniquely
advances `.github/.release-please-manifest.json`, together with its merged
release PR metadata. A validator derives the pending version by comparing the
manifest with the latest verified immutable release, locates the unique commit
that introduced that version, and rechecks every manifest/ref at that commit.
Release-please documents its merged-PR lifecycle labels: `autorelease: pending`
means the release still needs release creation, while `autorelease: tagged`
means release-please consumed it. These labels plus draft presence distinguish
first handoff from recovery.

The handoff is a serialized, resumable state machine. One non-cancelling release
concurrency group owns the lane and re-reads state after every mutation. The
workflow provisions and owns a `jig:release-verified` label. Every draft carries
a generated `release-identity.json` asset containing the durable commit,
version/tag, deterministic Claude/Codex host tree digests, and archive asset
digests. Publication locks that evidence with the release.

The rolling anchor is the latest immutable release whose merged release PR has
`jig:release-verified`, not merely the latest published immutable release.
Before computing the manifest/tag gap, preflight first finds any newer immutable
candidate without that checkpoint. It re-verifies the locked tag, commit,
assets, and digests against `release-identity.json`; repairs release-please's
terminal label to exactly `autorelease: tagged`; and applies
`jig:release-verified` last. Only then may the candidate advance the rolling
anchor and unblock release-please. A missing or mismatched identity asset on an
immutable candidate fails closed because the locked release can no longer be
repaired in place. With no pending version, release-please may maintain the next
release PR; packaging does not run. With a pending version:

- `autorelease: pending` plus no matching draft invokes release-please once to
  create the draft, then re-reads state.
- A matching draft with either `pending` or `tagged` resumes that draft; this
  covers a crash before or after the label transition.
- A published immutable release for the pending tag, under either `pending` or
  `tagged`, resumes at postcondition verification from its locked
  `release-identity.json` and checkpoint-label normalization; it never
  reconstructs a draft for an already locked tag.
- A published mutable release enters the quarantine/version-retirement path.
- Only when there is no published release or tag does `tagged` plus a
  missing/corrupt draft reconstruct from the durable Git transaction without
  asking release-please to recalculate.
- Multiple incompatible releases, drafts, commits, or version mismatches fail
  closed. Temporary label combinations are tolerated only when an authoritative
  published release determines the recovery direction.

Intervening pushes cannot supersede the target. Release-please may calculate a
later release only after publication makes the tag discoverable. Failure-
injection tests cover pending → action crash, draft → label-transition crash,
publish → process crash before verification, later push → resume, and tagged
→ corrupt/delete draft → reconstruct. An
unrecoverable target stays unpublished and blocks the lane; the repair runbook
cannot silently skip or reuse its semantic version.

After immutable postconditions pass, the workflow normalizes to
release-please's documented terminal `autorelease: tagged` label: add/retain
`tagged` first, then remove `autorelease: pending`, then apply
`jig:release-verified` as the final mutation. Publication itself is proven by
the immutable GitHub release and its locked identity asset; the workflow-owned
label is the durable verification checkpoint, not an alternative publication
signal. A crash after publication or between label mutations, including a
no-label state, is idempotently normalized on the next run after re-verifying
that evidence. If the verification label is deleted, the next run re-verifies
and restores it before using the release as an anchor. The workflow never
clears `pending` merely because a draft exists, preventing the next release PR
from starting early.

The migration has no previous immutable release: `v2.7.0` is explicitly
mutable. Bootstrap from a reviewed content anchor instead of trusting that tag
name. Record version `2.7.0`, tag `v2.7.0`, full commit
`9798faa1bedb97bdd69212c812bcae28af3c957e`, and deterministic Claude/Codex host
tree digests in a release-baseline file. At implementation time, verify those
values against the repository and the four 2.7.0 manifests before accepting
the anchor. The first pending transaction compares against this exact commit,
even if the legacy tag later moves. After the first successfully published
immutable release, the latest immutable release carrying the verified
checkpoint supersedes the bootstrap anchor. Validation rejects unreviewed
baseline changes.

This decision extends [ADR-0018](./adr-0018-dual-host-generated-plugin-artifacts.md):
that ADR defines which per-host packages are shipped; this ADR defines how a
stable version identifies those package bytes.

## Decision Options Considered

### Option A: Host-native tag pins plus GitHub immutable releases

- **Pros:** Preserves both hosts' existing package shapes; pins Claude's
  catalog and separate plugin fetches plus Codex's marketplace fetch at their
  actual Git boundaries; makes the version label, generated package, and
  release archive one reviewable transaction; GitHub mechanically locks both
  the tag and uploaded assets.
- **Cons:** Requires enabling a repository-level control and changing the
  workflow to draft → attach assets → publish; release automation and tests
  must validate more coupled surfaces.

### Option B: Convert Codex local plugin entries to Git-backed tag pins

- **Pros:** Makes the Claude and Codex catalog JSON superficially symmetric;
  both plugin entries visibly carry `ref: vX.Y.Z`.
- **Cons:** Adds a second Codex Git fetch instead of preserving resolution
  within the already-pinned marketplace snapshot; changes the generated
  archive marketplace away from its proven local bundle shape; and couples
  stable release concerns into the local development package.

### Option C: Keep semantic versions and SHA-pin a follow-up catalog commit

- **Pros:** Plugin sources are content-addressed without relying on tag
  governance; the GitHub immutable-release setting is not required for remote
  installs.
- **Cons:** The release commit cannot contain its own SHA, so the catalog pin
  requires a second commit after the release commit exists. Version manifests
  and source identity are no longer one atomic reviewed change; archives still
  need a separate immutability control.

### Option D: Omit semantic versions and use commit-SHA versions

- **Pros:** Every default-branch commit is content-addressed automatically;
  there is no version/ref synchronization step.
- **Cons:** Changes jig from stable releases to rolling every-commit updates,
  weakens release-note and archive alignment, and changes the user-facing
  distribution model beyond the reported problem.

### Option E: Keep unpinned sources and rely on version bumps

- **Pros:** No release-pipeline change.
- **Cons:** The version and fetched bytes remain independently mutable; a
  post-tag commit can reproduce the exact failure from issue #98.

## Recommended Decision

Adopt **Option A**.

For stable version `X.Y.Z`, pin each host at the Git boundary it actually uses:

- The root Claude catalog's `git-subdir` plugin source selects `ref:
  vX.Y.Z`, resolving `hosts/claude` from that tag.
- Stable Claude instructions add the marketplace itself at the same tag, for
  example `/plugin marketplace add ramboz/jig@vX.Y.Z`, before installing
  `jig@jig`. Upgrading an existing install re-adds `jig` at the newer stable
  tag, then runs `/plugin update jig@jig`; the manifest version bump moves the
  plugin cache to that tag's bytes. Bare `ramboz/jig` is a moving
  development/latest source, not the stable contract.
- The root Codex catalog and generated Codex archive catalog remain
  `source: local`. Stable Codex instructions add the repository marketplace
  with `codex plugin marketplace add ramboz/jig --ref vX.Y.Z`; the root local
  entry then resolves `hosts/codex/plugins/jig` inside that tagged snapshot.
- A fresh Codex install runs the tagged marketplace add followed by `codex
  plugin add jig@jig`. Switching an existing `jig` marketplace from an
  unpinned or different ref runs `codex plugin marketplace remove jig`, adds
  the marketplace again with `--ref vX.Y.Z`, then runs `codex plugin add
  jig@jig`. `marketplace upgrade` is not presented as a way to change the
  selected tag; it only refreshes the configured source.
- Bare Codex `marketplace add ramboz/jig` is a moving development/latest
  channel, not the stable `X.Y.Z` install contract.

All root and generated plugin manifest versions, the Claude stable plugin
source ref, and committed host packages are one release transaction. A release
identity validator must reject missing or mismatched refs, versions, tags,
packages, install commands, and archives before publication. Claude validation
must prove that the documented stable command selects the same tag as the
catalog's plugin source. Codex validation must prove that its documented stable
command selects the matching marketplace tag and that both Codex catalog
entries retain their package-relative local sources. Isolated lifecycle smokes
must cover Claude fresh tagged add/install and old-tag → tagged replacement →
plugin update, plus Codex fresh add and old-ref or unpinned → remove → tagged
re-add → plugin add, so a release cannot document a pin that only works for new
users.

Before the next release, enable GitHub immutable releases for the repository.
Configure release-please with `draft: true` and do not force early tag creation.
Run the serialized preflight/resume state machine before release-please. For a
new action-created or reconstructed draft, check out the durable transaction's
commit rather than the not-yet-created tag; verify the draft's target commit and
that the tag is still absent; preflight that repository immutable releases are
enabled; idempotently rebuild and replace draft assets and notes; then publish.
Publication should create and lock the tag. The publish response and a fresh
read must report `immutable: true`, with the locked tag commit matching the
durable commit used for source and archive identity checks.

GitHub exposes no atomic "publish only if this repository setting is unchanged"
condition. Stable means the post-publication immutability check passed, not
merely that a tag briefly existed. If publication returns a mutable release,
the workflow quarantines that semantic version, removes the mutable release and
tag, records a durable terminal tombstone containing the exposed commit and
payload digests, and never reuses the version. Consumers may already have cached
that one payload; quarantine cannot revoke it, so documentation marks the
version unsupported and directs them to update. Recovery creates a new
corrective release PR for a new semantic version. A temporary reviewed recovery
change sets release-please's `last-release-sha` to the failed transaction commit
and `release-as` to the next unused semantic version. The generated corrective
PR must update every manifest, ref, install command, and host package and remove
both temporary overrides before merge; CI rejects the tombstoned version,
missing version advancement, or lingering recovery keys. After merge, the new
version follows the normal durable transaction path. Failure-injection tests
cover a crash before and after corrective-PR creation and prove idempotent
resume. This preserves one observed payload for the retired version under the
stated trusted-admin assumption, but does not claim protection from a
repository administrator concurrently changing the control plane.
For the first release only, derive the pending transaction from the reviewed
v2.7.0 commit anchor rather than requiring a prior immutable tag; subsequent
releases use the latest immutable release whose transaction carries the
verified checkpoint.

The identity target is the tagged host package, without changing the generated
host layouts:

- Claude remote install pins the catalog and its `hosts/claude` plugin source
  at `vX.Y.Z`; the Claude archive identifies the same tagged package.
- Codex remote install identifies the repository marketplace snapshot at
  `vX.Y.Z`, whose local entry identifies `hosts/codex/plugins/jig`.
- The Codex archive keeps its local extract-then-add marketplace because the
  tagged archive already seals `hosts/codex`; its plugin payload must match the
  same tagged directory.

Development checkouts and local marketplaces may remain moving inputs, but
documentation must not present them as the stable release channel. Claude
contributors load the generated package directly with `claude --plugin-dir
hosts/claude` instead of adding the now-tag-pinned root catalog. Codex
contributors continue to add `hosts/codex` as a local marketplace.

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

- Version bumps must update the Claude marketplace ref and regenerate both host
  packages in the same change.
- Stable install documentation is version-bearing release state: its Claude
  and Codex marketplace-source refs must advance with the release.
- Claude's stable transition is two-phase (replace the tagged marketplace,
  then update the plugin) and requires a restart to apply the updated plugin.
- Stable Codex upgrades require adding or selecting the desired tagged
  marketplace snapshot through an explicit remove/re-add transition; the
  unqualified repository shorthand remains moving.
- Release tooling owns a stricter cross-file invariant and must report all
  drift clearly.
- The release workflow must attach all assets while the release is still a
  draft; post-publication asset edits are intentionally unavailable.
- Release automation owns a provisioned `jig:release-verified` checkpoint and
  must lock `release-identity.json` into every draft before publication.
- Packaging checks out release-please's reported commit SHA because the stable
  tag intentionally does not exist until the fully populated draft is
  published.
- Release automation needs explicit recovery states and a maintainer runbook;
  a stuck draft intentionally blocks later releases instead of letting
  release-please calculate against incomplete history.
- The migration carries one explicit legacy baseline record until the first
  immutable release establishes the normal rolling anchor.
- Repository release immutability is an external prerequisite that code alone
  cannot enable safely on the maintainer's behalf.
- A mutable publish caused by control-plane drift retires that semantic version
  permanently; it cannot revoke existing host caches and requires a new
  version-bearing release commit for recovery.

## Assumptions

<!-- Spec 064-02 / ADR-0020 §1–§2 — grounding-by-probe (risk-gated). -->

_Load-bearing factual claims about runnable surfaces (library/API capability,
version/perf behavior, behavior of existing code) must be backed by an executed
probe (run a command, read source/`node_modules`) or a citation — or listed
here explicitly as an assumption. Never assert an unverified claim as fact._

_Risk-gated: omit this section (or write "None") when the decision has no
unverified load-bearing assumptions — do not pad with boilerplate._

Repository administrators are trusted not to disable or alter immutable-release
settings concurrently with the short publish operation. GitHub exposes a
preflight read and post-publication `immutable` state, but no documented atomic
conditional publish on the repository setting. The workflow detects a violated
assumption after publication and quarantines the version; it cannot make a tag
that was briefly public become retroactively immutable.

All other current repository and release metadata were probed directly;
platform claims are backed by current first-party documentation:

- [Claude marketplace version resolution](https://code.claude.com/docs/en/plugin-marketplaces#version-resolution-and-release-channels)
- [Codex plugin building](https://developers.openai.com/codex/plugins/build)
- [GitHub immutable releases](https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases)
- [GitHub immutable-release setup](https://docs.github.com/en/code-security/supply-chain-security/understanding-your-software-supply-chain/preventing-changes-to-your-releases)
- [Release-please lifecycle labels](https://github.com/googleapis/release-please/blob/main/docs/customizing.md#release-lifecycle-labels)

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
- Repository administration cannot provide the trusted, stable control-plane
  window required during publication; in that environment this design needs a
  different registry or an external atomic publication service.

## Open questions

None.
