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

1. **Stable Git sources are locked-tag-pinned.** For a release version `X.Y.Z`, the
   root Claude and Codex marketplace entries that fetch plugin content from Git
   select `vX.Y.Z`; their resolved plugin trees are respectively
   `hosts/claude` and `hosts/codex/plugins/jig` from that tag. Generated archive
   marketplaces may retain local sources because their payload is already
   sealed inside the release archive. The release is not stable unless GitHub
   reports it immutable and the locked tag targets the release commit.
2. **The release change is atomic.** Release automation updates the root and
   generated Claude/Codex manifest versions plus both stable Git source refs in
   the same release change. Regenerating host packages preserves the expected
   source shape and does not hand-edit `hosts/`.
3. **Drift is rejected before publication.** A deterministic contract check exits
   non-zero and names every mismatch when any semantic version differs, a
   stable ref is absent or not exactly `v<version>`, the release tag disagrees,
   or a generated host package is stale. CI and the release workflow run this
   check before artifacts are published.
4. **Remote payload identity is proven.** A smoke fixture resolves each root
   stable marketplace source at its declared tag and compares a deterministic
   tree digest with the corresponding tagged `hosts/<host>` payload. A fixture
   modeled on the issue #98 post-tag-change case fails rather than accepting
   later default-branch bytes under the old version.
5. **Archives are attached before immutable publication.** The workflow creates
   a draft release, attaches the already-validated Claude and Codex archives,
   and only then publishes it. The job verifies GitHub reports
   `immutable: true`, the locked tag commit is the tested commit, and the
   published asset digests equal the locally built archives. It never relies on
   post-publication uploads or edits.
6. **Archive payload identity is proven.** Claude and Codex archive smoke tests
   verify the archive's plugin payload against the same tagged host-package
   digest, in addition to their existing shape checks. Rebuilding either archive
   from the same tag remains byte-for-byte deterministic.
7. **Host semantics are explicit.** README/release documentation defines
   `vX.Y.Z` as the stable identity, tells remote installers how the pin is
   applied, and preserves the Codex archive wording "extract-then-add
   marketplace bundle" without claiming direct zip installation.

**Edge cases:**

- A release candidate with four matching manifests but a stale marketplace
  ref is rejected.
- A matching `ref` with the wrong prefix, version, path, or repository is
  rejected.
- A post-tag default-branch commit cannot alter the payload digest accepted for
  the already-released version.
- Publication is refused when release immutability is disabled or GitHub does
  not report the final release/tag/assets as immutable and matching.
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
