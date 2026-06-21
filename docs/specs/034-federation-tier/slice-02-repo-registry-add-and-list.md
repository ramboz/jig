---
status: DRAFT
dependencies: ["034-01"]
last_verified:
---

## Slice 034-02 — repo-registry-add-and-list

**Goal:** Ship the first half of the central registry CRUD —
`jig:repo-registry import`, `add <repo>` (registers + opens member
bootstrap PR), and `list` — so a multi-repo team can seed the registry
from an existing inventory source and still add individual repos over
time.

**DoR:**
- Slice 034-01 is DONE.
- `repos.yaml` schema is published.
- If slice 034-00 ran, its `repos.proposed.yaml` is available as an
  import fixture.

**Acceptance Criteria:**

1. **`jig:repo-registry` skill ships** with SKILL.md describing `add`
   / `import` / `list` subcommands. Skill is central-only (refuses
   with a clear message when invoked in standalone or member role).
2. **`registry.py import <proposal-or-source>` merges inventory.** It
   accepts a slice-034-00 `repos.proposed.yaml` or any supported
   inventory importer output. v1 includes the workspace-manifest
   importer (`mani.yaml`, with optional `workspace.yaml` sidecar) as a
   bundled example, but the command contract is importer-neutral. The
   merge preserves tags/provenance/provider hints and emits a
   deterministic `docs/repos.yaml` diff. Existing entries are updated
   only when the imported source still matches their recorded
   provenance; otherwise the helper reports a conflict for human review.
3. **`registry.py add <repo>` appends to `repos.yaml`** with
   `status: pending` and a valid `role` (`member` unless explicitly
   adding the central/authority repo). Refuses if the repo name already
   exists, the host id is unknown, or the path doesn't match the repo
   returned by the configured repo access provider.
4. **Bootstrap PR opens against the member repo when supported.** `add`
   opens a PR against the target repo's default branch, adding a
   placeholder `.jig/scaffold.json` with `role: member`,
   `central_repo: <url>`, and onboarding `status: pending` in the
   central registry. If the provider cannot open PRs, the helper emits
   the exact patch and manual PR instructions.
5. **Two-PR sequence documented.** SKILL.md walks the user through:
   central PR → review/merge → member PR → review/merge → status
   flips to `active`. Helper does not auto-merge either side.
6. **`registry.py list`** prints all repos (active, pending,
   archived) in a stable order with role, host, and status.
   Read-only.
7. **Dry-run flag.** `add --dry-run` and `import --dry-run` show the
   registry diff + any bootstrap PR title/body without opening PRs or
   writing files.

**DoD:**
- [ ] All ACs pass; full test suite green.
- [ ] Implementer test coverage exercises import (proposal,
      workspace-manifest importer, conflict, provenance-preserving
      update), add (happy path, conflict, unknown host, missing remote
      repo), and list.
- [ ] Reviewed by `reviewer` subagent.
- [ ] Implementation review passed.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were
      deferred during implementation.

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated.
- [ ] CLAUDE.md Skills table gains a `repo-registry` row
      (central-only).

**Anti-horizontal-phasing check:** After this slice lands, a
central-repo maintainer can run `repo-registry add my-service` and see
two PRs opened (central + member) that, once merged, complete a member
onboarding end-to-end.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

_TODO._
