---
status: DRAFT
dependencies: ["034-02", "034-03"]
last_verified:
---

## Slice 034-10 — migrate-to-federation

**Goal:** Add `jig:migrate to-federation <central-url>` as a subcommand
of the existing `migrate.py` helper, idempotent and re-runnable, so
existing standalone jig installs can join an established federation
without re-scaffolding from scratch.

**DoR:**
- Slice 034-02 is DONE.
- Slice 034-03 is DONE.

**Acceptance Criteria:**

1. **`jig:migrate to-federation --central=<url>`** runs in an
   existing standalone repo and:
   - Validates the central repo URL resolves and has a `repos.yaml`
   - Calls `scaffold-init --role=member --central=<url>` in
     upgrade-in-place mode
   - Opens a PR against central to add this repo to `repos.yaml`
2. **Refuses on conflict.** If the repo is already a member, or the
   name already exists in central's registry with a different host
   / path, the helper exits with a structured error naming the
   conflict. No partial writes.
3. **Idempotent re-run.** Re-running on an already-migrated repo
   reports "already a member" and exits 0. No new PRs opened.
4. **Dry-run support.** `--dry-run` prints every action without
   writing or opening PRs.
5. **Documented migration path.** SKILL.md (or `migrate.py`'s
   subcommand help) walks the user through: prep (central is set
   up) → migrate (local) → review/merge central PR → done.
6. **Standalone fallback.** If the central URL is unreachable, the
   helper exits with a clear error; the local install stays
   standalone.

**DoD:**
- [ ] All ACs pass; full test suite green.
- [ ] Implementer test coverage exercises happy path, conflict
      refusal, idempotent re-run, dry-run, unreachable-central.
- [ ] Reviewed by `reviewer` subagent.
- [ ] Implementation review passed.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were
      deferred during implementation.

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated.

**Anti-horizontal-phasing check:** After this slice lands, an
engineer on a team that already uses jig in standalone mode can run
`jig:migrate to-federation --central=<url>` and have their repo
participating in federation (registered, drift-aware,
cross-repo-spec-capable) without losing any local history.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

_TODO._
