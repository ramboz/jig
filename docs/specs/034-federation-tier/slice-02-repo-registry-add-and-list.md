---
status: DRAFT
dependencies: ["034-01"]
last_verified:
---

## Slice 034-02 — repo-registry-add-and-list

**Goal:** Ship the first half of the central registry CRUD —
`jig:repo-registry add <repo>` (registers + opens member bootstrap PR)
and `jig:repo-registry list` — so an engineer can populate the registry
one repo at a time.

**DoR:**
- Slice 034-01 is DONE.
- `repos.yaml` schema is published.

**Acceptance Criteria:**

1. **`jig:repo-registry` skill ships** with SKILL.md describing `add`
   / `list` subcommands. Skill is central-only (refuses with a clear
   message when invoked in standalone or member role).
2. **`registry.py add <repo>` appends to `repos.yaml`** with
   `status: pending`. Refuses if the repo name already exists, the
   host id is unknown, or the path doesn't match the GitHub repo (via
   adapter `gh repo view`).
3. **Bootstrap PR opens against the member repo.** `add` opens a PR
   against the target repo's default branch, adding a placeholder
   `.jig/scaffold.json` with `role: pending` and `central_repo:
   <url>`. The PR description names slice 034-03 as the follow-up
   (which fills in `--role=member` and Tier 2 skills).
4. **Two-PR sequence documented.** SKILL.md walks the user through:
   central PR → review/merge → member PR → review/merge → status
   flips to `active`. Helper does not auto-merge either side.
5. **`registry.py list`** prints all repos (active, pending,
   archived) in a stable order with role, host, and status.
   Read-only.
6. **Dry-run flag.** `add --dry-run` shows the registry diff + the
   bootstrap PR title/body without opening either PR.

**DoD:**
- [ ] All ACs pass; full test suite green.
- [ ] Implementer test coverage exercises add (happy path, conflict,
      unknown host, missing remote repo) and list.
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
