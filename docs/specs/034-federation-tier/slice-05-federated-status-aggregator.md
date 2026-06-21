---
status: DRAFT
dependencies: ["034-02"]
last_verified:
---

## Slice 034-05 — federated-status-aggregator

**Goal:** Ship `jig:federated-status` (central-only) that walks the
`repos.yaml` registry, pulls each repo's spec frontmatter via the repo
access provider, and writes a federated status board at
`docs/specs/INDEX.md` in the central repo.

**DoR:**
- Slice 034-02 is DONE.

**Acceptance Criteria:**

1. **`federated-status regen`** walks every active repo in the
   registry, fetches each repo's configured spec listing via the repo
   access provider (no clone unless `local-worktree` / `git-ssh`
   provider is selected), reads frontmatter from each supported
   `spec.md`, and emits `docs/specs/INDEX.md` in the central repo.
2. **INDEX.md shape** mirrors the single-repo status board: spec,
   slice, status, notes. New columns: `repo`, `parent_spec` (when
   set).
3. **Cross-repo specs are grouped.** A parent spec and its children
   render together under a `## Cross-repo specs` section; pure-local
   specs land under `## Per-repo specs · <name>` sections per repo.
4. **Tolerates legacy or external spec homes.** A member with no
   `docs/specs/` directory is reported as `no_jig_specs` or
   `external_spec_home` when discovery found another documented spec
   location, but still emits the index for other members. Single bad
   apple doesn't break aggregation.
5. **Caching layer.** Provider ETags / modified timestamps /
   fingerprints are stored in generated cache files under
   `docs/federation/` (or `.jig/cache/` for local-only provider state),
   not in human-authored `repos.yaml`, so routine regen does not churn
   registry config.
6. **Read-only.** Helper writes only `docs/specs/INDEX.md` in the
   central repo plus generated federation cache artifacts. Never
   touches member repos.

**DoD:**
- [ ] All ACs pass; full test suite green.
- [ ] Implementer test coverage exercises happy path,
      missing-spec-dir, external-spec-home, cross-repo rollup,
      provider-cache re-run, and partial provider failure.
- [ ] Reviewed by `reviewer` subagent.
- [ ] Implementation review passed.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were
      deferred during implementation.

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated (central side).

**Anti-horizontal-phasing check:** After this slice lands, an
engineer on any member team can open
`<central>/docs/specs/INDEX.md` and see a single view of "what's in
flight where" across all 40 repos.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

_TODO._
