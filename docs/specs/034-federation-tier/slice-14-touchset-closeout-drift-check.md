---
status: DRAFT
dependencies: ["034-12"]
last_verified:
arch_review: true
---

## Slice 034-14 — touchset-closeout-drift-check

**Goal:** Add a close-out/review guard that compares declared
`touches:` metadata with the actual files changed by the branch, so
collision radar stays honest without requiring constant metadata pushes.

**DoR:**
- Slice 034-12 is DONE, so specs and slices have a documented
  `touches:` contract and local overlap preflight.

**Acceptance Criteria:**

1. **Actual touchset extraction.** The helper computes changed files
   from `git diff --name-only <base>...HEAD`, with `<base>` defaulting
   to `origin/main` and overridable for PR/review contexts.
2. **Declared-vs-actual comparison.** It reports files changed outside
   declared `touches:`, declared touches that matched no changed file,
   and changed files that overlap another unfinished spec even though
   they were not declared up front.
   In federation mode it also reports actual changes to known
   contract-surface files that were not represented in the candidate
   touchset/contract metadata.
3. **Review integration.** `review.py` or the review prompt builder
   includes the touchset drift report when reviewing an implementation
   slice.
4. **Land integration.** `slice-land` dry-run output includes the
   touchset drift report before merge/push instructions. Direct mode
   refuses only on malformed metadata or an explicit future exclusive
   policy, not on advisory overlap warnings.
5. **Update hint.** When undeclared files are found, the report names
   the helper command from slice 034-12 that updates the spec/slice
   touchset metadata.
6. **Generated/noisy file handling.** The helper respects a small
   built-in ignore list for generated jig artifacts that are already
   managed by status-board or close-out flows, and documents every
   ignored path pattern in code and tests.
7. **Federation-aware labels.** In member repos, report paths are
   labeled with the local repo name when the federation role is known,
   so output can be compared with `repo-name:path` tokens from central
   parent specs.
8. **Verification-profile handoff.** When slice 034-15 is present and
   actual changes match a declared verification profile surface, the
   report lists the affected repo commands/deploy-order notes as
   advisory follow-up.

**DoD:**
- [ ] All ACs pass; full test suite green.
- [ ] Implementer test coverage exercises declared match,
      undeclared changed file, stale declared touch, overlap with
      another active spec, generated-file ignore, review integration,
      and land dry-run integration.
- [ ] Reviewed by `reviewer` subagent.
- [ ] Implementation review passed.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were
      deferred during implementation.

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated.
- [ ] Reviewer/land workflow docs mention the touchset drift report.

**Anti-horizontal-phasing check:** After this slice lands, a branch
that declared only `skills/spec-workflow/workflow.py` but also changed
`skills/adr-workflow/adr.py` gets a clear close-out warning before
review/landing.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

_TODO._
