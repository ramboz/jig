---
status: DRAFT
dependencies: [adr-0036]
last_verified:
arch_review: true
code_health_review: true
# design_review: true  # set true when this slice ships UI gated by an external
#                      # design-fidelity eval (attest-only; ADR-0014/0022).
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon).
     See docs/workflow.md "Self-defining vocabulary". -->

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation,
     else mark them as assumptions in the spec's `## Assumptions` section —
     never assert an unverified claim as fact. -->

## Slice 090-01 — immutable stable-release contract

**Goal:** A fresh stable marketplace install and either host release archive
labeled `X.Y.Z` resolve to the same payload committed at `vX.Y.Z`.

**DoR:**
- [ ] ADR-0036 is Accepted after a passing frame-critique review.
- [ ] The maintainer explicitly approves enabling GitHub immutable releases for
      `ramboz/jig`; the setting applies only to future releases.
- [x] The release-please update mechanism for a `v`-prefixed source ref is
      verified against its current documented or executable behavior.
- [ ] The existing deterministic host-package and release-archive fixtures are
      identified for extension rather than duplicated.

**Acceptance Criteria:**

1. **Each host is pinned at its real Git boundary.** For release version
   `X.Y.Z`, stable Claude instructions add the marketplace source at
   `ramboz/jig@vX.Y.Z`, and the root catalog's `git-subdir` plugin source also
   selects `vX.Y.Z` and resolves `hosts/claude` from that tag. Stable Codex
   instructions select the repository marketplace snapshot with `codex plugin
   marketplace add ramboz/jig --ref vX.Y.Z`; the root catalog then resolves its
   unchanged local path `./hosts/codex/plugins/jig`. The release is not stable
   unless GitHub reports it immutable and the locked tag targets the release
   commit.
2. **The release change is atomic.** Release automation updates the root and
   generated Claude/Codex plugin manifest versions plus the Claude stable
   plugin-source ref and both hosts' version-bearing stable install selectors
   in the same release change. Regenerating host packages preserves the
   expected source shapes and does not hand-edit `hosts/`.
3. **Drift is rejected before publication.** A deterministic contract check exits
   non-zero and names every mismatch when any semantic version differs, a
   Claude stable ref is absent or not exactly `v<version>`, the documented
   Claude marketplace-source ref or Codex stable marketplace ref disagrees,
   either Codex catalog stops using its expected package-relative local path,
   the release tag disagrees, or a generated host package is stale. CI and the
   release workflow run this check before artifacts are published.
4. **Remote payload identity is proven.** A smoke fixture resolves each root
   stable install through its host-native boundary—Claude marketplace-source
   ref plus plugin-source ref, Codex marketplace-source ref plus local plugin
   path—and compares a deterministic tree digest with the corresponding tagged
   `hosts/<host>` payload. A fixture modeled on the issue #98 post-tag-change
   case fails rather than accepting later default-branch bytes under the old
   version. The isolated Claude lifecycle proves a fresh tagged add/install and
   an old-tag → new-tag marketplace replacement → `plugin update jig@jig`
   transition; the enabled plugin's version, cache path, and payload digest all
   advance to the new tag. A new release that does not advance the semantic
   plugin version is rejected because Claude would retain the old cache key.
   The isolated Codex lifecycle covers both a fresh tagged add and transition
   from an unpinned or older tagged `jig` marketplace: remove `jig`, re-add it
   with the new `--ref`, then run `plugin add jig@jig`. It proves the plugin is
   enabled and resolves from the new tagged snapshot; documentation does not
   claim that `marketplace upgrade` changes the configured tag.
5. **Archives are attached before immutable publication.** The workflow uses
   one non-cancelling release concurrency group and provisions a workflow-owned
   `jig:release-verified` label. Every draft includes a generated,
   subsequently locked `release-identity.json` containing the durable commit,
   version/tag, Claude/Codex host tree digests, and archive asset digests. A
   preflight first finds any immutable release newer than the last verified
   anchor but lacking the checkpoint, re-verifies it from that identity asset,
   repairs release-please's terminal label to exactly `autorelease: tagged`,
   and applies `jig:release-verified` last. Only a verified immutable release
   may become the rolling anchor. The workflow then compares the current
   release manifest with that anchor. If a
   version is pending, it identifies the unique merged commit that introduced
   that manifest version, verifies all release manifests/refs there, and treats
   that Git transaction—not a draft—as the durable target. It combines the
   merged release PR's documented `autorelease: pending`/`tagged` label with
   draft presence: pending+no draft invokes release-please once; a matching
   draft under either label resumes; an existing published immutable release
   resumes postcondition verification/label normalization; a published mutable
   release quarantines; and only no-published-release/no-tag plus
   tagged+missing/corrupt draft reconstructs the same tag/version/SHA/notes
   without release-please. Ambiguous state fails.
   Every mutation is followed by a state re-read, and release-please cannot
   calculate again until the pending transaction is published. With no pending
   transaction, release-please may maintain release PRs but packaging does not
   run. The job checks out the durable target, verifies the tag
   is absent, idempotently rebuilds and replaces validated archives/notes, then
   publishes, causing GitHub to create and lock the tag. It verifies
   `immutable: true`, the locked tag commit, identity asset, and asset digests;
   adds or retains release-please's `autorelease: tagged` label; removes
   `autorelease: pending`; and applies `jig:release-verified` last. The
   immutable GitHub release and locked identity asset are authoritative for
   publication; the additional label records completed verification. A crash
   after publication or during either label normalization—including a no-label
   state—resumes from that release, re-verifies the locked evidence, and repairs
   both checkpoints idempotently. A deleted verification label is likewise
   restored only after re-verification. A missing or mismatched identity asset
   on an immutable release fails closed because the release cannot be repaired
   in place. The workflow never clears pending at draft creation.
   Failure-injection
   tests cover action crash, label-transition crash, publish → crash before
   verification/checkpoint, intervening push → resume, and
   tagged+corrupt/delete draft → reconstruct. Ambiguous or unrecoverable
   transactions fail closed; the repair runbook cannot skip or reuse their
   semantic version.
   For the first release, where no prior immutable release exists, the
   comparison uses a reviewed baseline containing v2.7.0's full commit SHA and
   verified Claude/Codex host tree digests. The baseline is checked against all
   four 2.7.0 manifests and is not derived from the movable legacy tag. After
   the first immutable publication and verification checkpoint, that release
   supersedes this bootstrap path; unreviewed baseline drift is rejected.
6. **Archive payload identity is proven.** Claude and Codex archive smoke tests
   verify the archive's plugin payload against the same tagged host-package
   digest, in addition to their existing shape checks. Rebuilding either archive
   from the same tag remains byte-for-byte deterministic.
7. **Host semantics are explicit.** README/release documentation defines
   `vX.Y.Z` as the stable identity, tells remote installers how the pin is
   applied, labels unqualified Codex repository installs as moving/latest, and
   preserves the Codex archive wording "extract-then-add marketplace bundle"
   without claiming direct zip installation. Contributor instructions use
   `claude --plugin-dir hosts/claude` and `codex plugin marketplace add
   hosts/codex`, so the stable pin does not redirect local development to an
   older release. Claude stable instructions pin the marketplace source, label
   the bare repository shorthand as moving/latest, and distinguish fresh
   install from tagged marketplace replacement plus plugin update (and
   restart). Codex stable instructions distinguish the two-command fresh
   install from the remove/re-add/plugin-add transition required for an
   existing marketplace registered at another source ref.

**Edge cases:**

- A release candidate with four matching manifests but a stale marketplace
  ref is rejected.
- A matching `ref` with the wrong prefix, version, path, repository, or host
  boundary is rejected.
- A Codex catalog that replaces its expected local path with a second Git fetch
  is rejected.
- A Claude install command that fetches its catalog from the mutable default
  branch is not presented as stable even when that catalog currently contains
  a pinned plugin ref.
- Replacing a Claude marketplace source without updating the installed plugin,
  or publishing a new stable tag under the previous semantic plugin version,
  is rejected as an incomplete transition.
- Adding a new Codex stable ref over an existing differently sourced `jig`
  marketplace is not assumed to be idempotent; the tested remove/re-add path is
  the supported transition.
- A post-tag default-branch commit cannot alter the payload digest accepted for
  the already-released version.
- Publication is refused when release immutability is disabled or GitHub does
  not report the final release/tag/assets as immutable and matching.
- An immutable publication followed by a process crash cannot advance the
  rolling anchor until the next run verifies its locked `release-identity.json`
  and applies `jig:release-verified`. Missing or mismatched locked evidence
  fails closed and forces the version-retirement/corrective-release path.
- The setting is checked immediately before publication. If GitHub nevertheless
  returns a mutable published release, that version is quarantined: remove the
  mutable release/tag, persist a terminal tombstone with its commit/payload
  digests, never reuse its semantic version, and mark it unsupported for any
  consumers that already cached it. Recovery requires a new corrective release
  PR generated with temporary `last-release-sha` (the failed commit) and
  `release-as` (the next unused version) controls. The corrective PR advances
  all manifests, refs, stable commands, and generated packages, removes both
  overrides before merge, and is rejected if it reuses the tombstoned version.
  Crash-before/after-PR failure fixtures prove idempotent resume. The design
  does not claim resistance to a repository admin concurrently changing this
  control plane or the ability to revoke an existing host cache.
- Publication is refused when release-please creates the tag before packaging,
  the draft target differs from its reported `sha`, or any asset/note update is
  attempted after publication.
- A failed package/publish job, manual rerun, or intervening main push resumes
  the pending Git transaction without invoking release-please or changing its
  target commit. A missing/corrupt draft is reconstructed from that transaction;
  ambiguous history or an unrecoverable target blocks the lane until explicit
  repair completes the same version.
- With no prior immutable release, the first pending transaction anchors to the
  reviewed v2.7.0 full commit/digests; a moved legacy tag cannot alter that
  baseline, and missing or changed baseline data fails closed.
- Local development marketplaces continue to work without pretending to be a
  stable release channel.

**DoD:**
- [ ] All ACs pass; full test suite green (no regressions).
- [ ] Implementer test coverage exercises each AC with at least one
      fixture. Edge cases listed in the slice are covered explicitly.
- [ ] Reviewed by `reviewer` subagent. Reviewer prompt built by
      `review.py`.
- [ ] Implementation review passed.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation sweep produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were
      deferred during implementation.

### Close-out (post-DONE)

These items can only be ticked AFTER the final `RECONCILED → DONE`
transition. Slice-land's `check_dod` (slice 009-01) excludes them
from the count.

- [ ] `docs/specs/README.md` regenerated by `workflow.py status-board`.
      Notes column receives any load-bearing per-slice invariant
      (it's preserved across regen).
- [ ] Primer hygiene per spec 025-01 rule: **if this slice closes the
      spec** (all non-deferred slices DONE), check `CLAUDE.md`,
      `AGENTS.md`, and scaffold templates when present, then **compress**
      the spec's Active-specs entry — drop facts derivable from the
      spec dir + status board, migrate load-bearing per-slice
      invariants to the status board Notes column, keep at most a
      one-liner only for cross-cutting facts. If the spec is still
      in flight (other slices DRAFT / READY / IN_PROGRESS), leave
      the entry. If this slice introduces a new skill, add or
      update its row in the Skills table.

**Anti-horizontal-phasing check:** After this slice lands, every stable install
surface labeled `X.Y.Z` is checked against the same tagged host-package bytes;
there is no intermediate release state that relies on a later slice.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

_TODO: numbered sections covering deviations from the planned shape,
reviewer findings folded back in, doc updates, plan adherence._

### Reconciliation sweep

Record the drift-prone surfaces checked during reconciliation. The transition
gate only requires this subsection to exist; the reconciliation reviewer judges
whether coverage and rationales are honest.

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `README.md` | `no-op` | _TODO: why this slice did not affect the project front door, or summarize the update._ |
| `docs/specs/README.md` | `updated` | _TODO: regenerated by `workflow.py status-board`, or explain why deferred._ |
| `docs/product-vision.md` | `no-op` | _TODO: checked for behavior / scope drift._ |
| `docs/architecture.md` | `no-op` | _TODO: checked for module-boundary / public-contract drift._ |
| Primer surfaces: `CLAUDE.md` / `AGENTS.md` / scaffold templates | `no-op` | _TODO: primer hygiene checked; note compression or template updates if any._ |
| `docs/inbox.md` | `no-op` | _TODO: checked for items resolved by this slice._ |
| `docs/refinement-todo.md` | `no-op` | _TODO: checked for resolved items or new deferred decisions._ |
| `docs/memory/**` | `no-op` | _TODO: note memory-sync result or why nothing was worth capturing._ |
| `docs/decisions/README.md` / ADR index | `no-op` | _TODO: use `updated` when the slice touched ADRs; otherwise mark checked._ |
| Additional live prose / generated templates touched by this slice | `deferred` | _TODO: name owner or trigger when real cleanup remains; otherwise replace with `no-op`._ |
