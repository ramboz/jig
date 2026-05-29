---
status: DRAFT
dependencies: ["034-04"]
last_verified:
arch_review: true
---

## Slice 034-12 — touchset-frontmatter-and-preflight

**Goal:** Add lightweight touch-intent metadata to specs and a local
preflight that warns when new or resumed work overlaps unfinished specs
already visible on `origin/main`.

**DoR:**
- Slice 034-04 is DONE, so cross-repo spec frontmatter is already
  documented and validated.

**Acceptance Criteria:**

1. **Touchset frontmatter contract.** `docs/spec-workflow/` documents
   `touches:` as a YAML-lite list of strings on `spec.md` and/or slice
   files. Tokens are either repo-relative paths/globs (`skills/foo.py`,
   `skills/spec-workflow/**`) or federation-scoped tokens
   (`repo-name:src/contracts/**`). Absolute paths and `..` segments
   are invalid.
2. **Optional owner/branch metadata.** `owner:` and `work_branch:`
   are documented as optional advisory fields. Defaults may come from
   `git config user.name` / current branch when the helper can infer
   them, but absence never invalidates a spec.
3. **Create-time declaration.** `workflow.py new` accepts repeatable
   `--touches <path-or-glob>` values plus optional `--owner` and
   `--work-branch`, and writes them into the reserved spec stub on
   `origin/main` (or local-only under `--no-push`).
4. **Deliberate update path.** A helper command updates touchset
   metadata for an existing spec/slice when scope changes materially.
   It does not auto-push on every edit; if the update happens off
   main, the helper tells the user to push or land the metadata change.
5. **Local conflict preflight.** Given a candidate touchset, the
   helper fetches `origin/main` best-effort, scans unfinished specs and
   slices for `touches:`, excludes the current spec, and reports exact
   path overlaps, glob overlaps, and same-directory broad overlaps.
6. **Advisory by default.** Overlap warnings exit 0 and include spec
   id, owner, work branch, and matching touch tokens when known.
   Malformed touchset metadata exits non-zero with a clear validation
   error.
7. **Automatic invocation at start points.** `workflow.py new
   --touches ...` runs the preflight before committing the reservation
   stub. The update helper also runs the preflight before writing the
   changed metadata.
8. **Standalone-safe.** The feature works in ordinary single-repo
   jig projects without federation configured; repo-prefixed tokens
   are accepted but only compared literally unless slice 034-13 is
   present.

**DoD:**
- [ ] All ACs pass; full test suite green.
- [ ] Implementer test coverage exercises schema validation, create
      metadata, update metadata, exact overlap, glob overlap,
      same-directory warning, malformed metadata, and no-overlap.
- [ ] Reviewed by `reviewer` subagent.
- [ ] Implementation review passed.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were
      deferred during implementation.

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated.
- [ ] `docs/spec-workflow/` updated with the touchset frontmatter
      contract and examples.

**Anti-horizontal-phasing check:** After this slice lands, an engineer
starting `workflow.py new cache-refactor --touches
skills/spec-workflow/workflow.py` gets an immediate warning if another
unfinished spec on `origin/main` already declared the same file.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

_TODO._
