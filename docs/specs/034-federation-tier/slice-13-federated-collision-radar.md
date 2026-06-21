---
status: DRAFT
dependencies: ["034-05", "034-12"]
last_verified:
arch_review: true
---

## Slice 034-13 — federated-collision-radar

**Goal:** Extend touchset preflight across a federation so engineers
starting or resuming work in one repo see likely conflicts with
unfinished specs in registered member repos.

**DoR:**
- Slice 034-05 is DONE, so central can aggregate federated spec state.
- Slice 034-12 is DONE, so active specs can expose `touches:`
  metadata consistently.

**Acceptance Criteria:**

1. **Federated touchset aggregation.** `jig:federated-status` includes
   each unfinished spec's repo, spec id, owner, work branch, status,
   and declared `touches:` tokens in its gathered data.
2. **Machine-readable cache.** The central repo writes a small
   generated touchset cache under `docs/federation/` (exact filename
   chosen in implementation) so member-side preflight can warn without
   walking every repo in the session.
   A companion generated contract-surface cache records declared and
   discovered surfaces (for example npm package names, OpenAPI
   files/paths, event topics, DB migration/RPC names, and deploy units)
   with provenance.
3. **`jig:collision-radar check`.** A Tier 2 skill/helper accepts a
   candidate touchset and compares it against the local repo's active
   specs plus the central cache when available.
4. **Repo-scoped matching.** Plain local paths compare only within the
   current repo. `repo-name:path` tokens compare against that named
   repo. Central parent specs may include multiple repo-prefixed
   tokens.
5. **Warning classes.** Output distinguishes at least: exact file
   overlap, glob/path overlap, same typed contract surface, and broad
   same-directory overlap. Exact file and contract-surface overlaps are
   listed first.
6. **Degraded central behavior.** If central is unreachable or the
   cache is absent/stale, member preflight still runs against local
   specs and emits a short "federated cache unavailable" note. Routine
   single-repo work is never blocked by a missing central cache.
7. **No context blow-up.** Collision checks load metadata only: spec
   frontmatter, slice frontmatter, and generated touchset/contract
   caches. They do not pull full spec bodies from every repo.
8. **Cross-repo-spec integration.** `jig:cross-repo-spec new` runs
   collision radar for the parent and child touchsets before creating
   stubs, and includes warnings in its user-facing output.

**DoD:**
- [ ] All ACs pass; full test suite green.
- [ ] Implementer test coverage exercises central aggregation,
      cache read/write, member degraded mode, repo-scoped matching,
      warning ordering, and cross-repo-spec integration.
- [ ] Reviewed by `reviewer` subagent.
- [ ] Implementation review passed.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were
      deferred during implementation.

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated.
- [ ] `docs/architecture.md` updated with the generated federated
      touchset cache and collision-radar data flow.

**Anti-horizontal-phasing check:** After this slice lands, an engineer
in `billing-ui` starting a spec that declares
`billing-ui:src/contracts/invoice.ts` sees a warning if an unfinished
central or member spec already declared that same contract surface.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

_TODO._
