---
status: DRAFT
dependencies: ["034-02"]
last_verified:
arch_review: true
---

## Slice 034-04 — cross-repo-spec-skill

**Goal:** Ship `jig:cross-repo-spec` for authoring an org-level epic
that touches N member repos — creates a parent spec in central + child
specs in each named member, wired together via `parent_spec:` and
`affects:` frontmatter pointers.

**DoR:**
- Slice 034-02 is DONE (registry populated).

**Acceptance Criteria:**

1. **`jig:cross-repo-spec new <slug> --affects <repo1>,<repo2>,...`
   creates the parent in central** with `parent_spec: null` + an
   `affects:` list of member names. Numbering uses the central
   repo's `workflow.py new` reservation.
2. **Child spec stubs created in each affected repo** with
   `parent_spec: <central-url>#<spec-id>` frontmatter and a
   placeholder `## Overview` pointing back to the parent. Each child
   uses its own repo's `workflow.py new` reservation.
3. **Frontmatter contract documented.** `parent_spec:` and
   `affects:` shapes are specified in `docs/spec-workflow/`.
   `spec_lint.py` or equivalent validates that values resolve.
4. **Cross-repo status rollup.** A child spec marked DONE does not
   flip the parent to DONE; the parent's spec-level status rolls up
   only when every child is DONE *and* the parent's own slices (if
   any) are DONE. Implementation can reuse `compute_spec_status()`
   shape.
5. **Refuses if any affected repo is not a registered member.**
   Clear error naming the missing repo(s); points at
   `jig:repo-registry add`.
6. **Idempotent.** Re-running with the same slug + affects is a no-op
   if the parent and all children already exist with matching
   pointers. Diverging pointers raise a typed error rather than
   silently overwriting.

**DoD:**
- [ ] All ACs pass; full test suite green.
- [ ] Implementer test coverage exercises happy path, missing-member
      refusal, idempotent re-run, status rollup.
- [ ] Reviewed by `reviewer` subagent.
- [ ] Implementation review passed.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were
      deferred during implementation.

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated.
- [ ] `docs/spec-workflow/` updated with the cross-repo frontmatter
      contract.

**Anti-horizontal-phasing check:** After this slice lands, an
architect can `cross-repo-spec new payments-3ds-rollout --affects
gateway,payments-svc,billing-ui` and walk away with one parent spec +
three child specs, all linked, all in DRAFT.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

_TODO._
