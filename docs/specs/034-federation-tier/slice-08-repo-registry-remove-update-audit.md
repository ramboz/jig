---
status: DEFERRED
dependencies: ["034-02"]
last_verified:
---

## Slice 034-08 — repo-registry-remove-update-audit

**Resolution trigger:** A real distributed-peer / multi-member consumer starts *building* (see spec.md § Peer tier) — jig state scaffolded into many member repos coordinated by a central. Re-open via DEFERRED → DRAFT.

**Goal:** Ship the second half of registry CRUD — `remove` (archive,
don't delete), `update` (metadata changes), and `audit` (drift +
broken-pointer detection).

**DoR:**
- Slice 034-02 is DONE.

**Acceptance Criteria:**

1. **`registry.py remove <repo>` archives.** Sets `status: archived`
   + `archived_date` in `repos.yaml`. Entry stays — historical
   references in cross-repo specs continue to resolve. Refuses to
   delete the entry outright.
2. **Archived repos flag orphaned contract surfaces.** `remove`
   prints a list of surfaces the archived repo declared as owned;
   humans decide where they re-home or whether to deprecate.
3. **`registry.py update <repo>`** supports changing `role`,
   membership `status`, provider config, authority mapping overrides,
   and declared `contract_surfaces` (host id stays immutable — a host
   change requires remove + add). Imported/discovered fields carry
   provenance so manual declarations are not overwritten silently by a
   later inventory-source sync.
4. **`registry.py audit`** reports four classes of drift:
   - members whose `jig_version` lags central's by ≥2 versions
   - members whose `federation-state.json` cache is stale (>30 days)
   - `affects:` references that point to non-existent or archived
     members
   - contract surfaces declared or discovered but not referenced by any
     cross-repo spec for ≥90 days (potential dead surfaces)
   - imported inventory-source drift (tag/path/provider changed in the
     source importer, e.g. a workspace manifest, since last import)
5. **Audit is read-only.** Reports only; never mutates `repos.yaml`.
   Exits 0 if no findings, 1 if findings, 2 if helper error.
6. **Cross-repo spec impact on remove.** Cross-repo specs touching
   the archived repo get a reconciliation note (via slice 034-05's
   regen) naming the archived dependency.

**DoD:**
- [ ] All ACs pass; full test suite green.
- [ ] Implementer test coverage exercises remove, update, each audit
      finding class.
- [ ] Reviewed by `reviewer` subagent.
- [ ] Implementation review passed.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were
      deferred during implementation.

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated.

**Anti-horizontal-phasing check:** After this slice lands, a central
maintainer can run `repo-registry audit` weekly and get a structured
report of every drift class — version lag, stale cache, broken
pointers, dead surfaces — without grepping `repos.yaml` by hand.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

_TODO._
