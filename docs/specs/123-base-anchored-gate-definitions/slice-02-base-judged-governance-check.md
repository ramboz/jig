---
status: DRAFT
dependencies: [123-01, adr-0068, adr-0051]
last_verified: 2026-11-21
kind: feature
arch_review: true
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon).
     See docs/workflow.md "Self-defining vocabulary". -->

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation,
     else mark them as assumptions in the spec's `## Assumptions` section —
     never assert an unverified claim as fact. -->

## Slice 123-02 — base-judged-governance-check

**Goal:** the scaffolded `jig-governance` check judges each PR with the base
branch's job and protected-path list, never the PR's copy; it counts a file
renamed or deleted out of a protected path; and it never runs PR content.

**Decision:** spec 123 D2 / ADR-0068 Option B. Changes the scaffolded
workflow's contract (trigger, permissions, diff source), hence `arch_review`.

**DoR:**
- ⬜ 123-01 DONE (jig's copy exists, so this slice re-renders it under the
  drift test).
- ⬜ **Probe G0–G5** (spec Assumptions) on a scratch GitHub repository and record
  the observations in this slice before `READY_FOR_IMPLEMENTATION`. If G1 fails
  (a `pull_request_target` job cannot be a required check on the PR), stop: that
  is ADR-0068's first kill criterion.
- ✅ The job's current shape: `on: pull_request` (`governance.py:192-193`),
  checkout of the PR merge commit with `fetch-depth: 0` (`:199-201`),
  `git diff --name-only origin/<base>...HEAD` (`:204`), embedded list and
  matcher (`:206-239`).
- ✅ `git diff --name-only` with git's default rename detection lists only a
  rename's destination; `--no-renames` lists both paths (probed 2026-11-21,
  git 2.43).

**Acceptance Criteria:**

1. **Base-side trigger.** `render_governance_workflow()` emits
   `on: pull_request_target` and no `pull_request` trigger, so GitHub runs the
   base branch's copy of the file and its embedded list. A YAML comment says why
   and points at ADR-0068.
2. **Diff only, no PR execution.** The job checks out the base side only (no
   checkout step names `github.event.pull_request.head.*` or any PR ref). It gets
   the head commit's objects as data (e.g. a fetch of `refs/pull/<n>/head`) and
   computes changed paths against the merge base with rename detection off. No
   step runs, sources, imports or installs a file from the head tree.
3. **Least privilege.** Workflow-level `permissions:` grants `contents: read`
   only. No step references `secrets.`. PR-controlled strings (title, body, head
   branch name) are never interpolated into a `run:` script; event values reach
   scripts through `env:`.
4. **Pinned by a static test.** A test parses the rendered YAML and fails when
   any property in AC1–AC3 breaks: a `pull_request` trigger, a head checkout, a
   `secrets.` reference, a permission beyond `contents: read`, or a `${{ … }}`
   expression inside a `run:` block.
5. **Renames and deletions count.** A PR that renames or deletes a file under a
   protected path is flagged: the old path is in the changed set. Covered with a
   git fixture (rename `docs/decisions/adr-0001-x.md` to `tmp/x.md`) through the
   same diff command the workflow renders.
6. **Self-change notice.** When the changed set includes
   `.github/workflows/jig-governance.yml`, the job's output says the PR changes
   the governance check, that the base branch's definition judged it, and that
   the new definition applies after merge. (The PR is still flagged: the path is
   protected.)
7. **Embedded matcher is parity-pinned.** A test extracts the embedded python
   from the rendered workflow and checks it against
   `governance.path_matches_glob` over the inputs
   `test_protected_paths.GlobMatcherParityTests` uses. This resolves the
   refinement-todo entry "CI-workflow-embedded glob matcher is not
   parity-pinned", whose trigger ("`render_governance_workflow` is next
   revised") this slice fires.
8. **The governance doc says what changed.** `render_governance_doc()` states:
   (a) the check reads its definition from the base branch, so a change to the
   list or job takes effect only after merge; (b) the PR that introduces or
   upgrades the workflow is not judged by it — the owner reviews that PR by hand,
   and if the check is already required it stays pending on that PR (G3);
   (c) never add a step that checks out or runs PR code to this workflow:
   `pull_request_target` runs with the base repository's token and secrets,
   including for fork PRs; (d) on a forge other than GitHub jig scaffolds no job,
   and the base-anchored control is that forge's own code-owner approval on the
   target branch.
9. **jig's copy follows.** jig's `.github/workflows/jig-governance.yml` and
   `docs/governance.md` are re-rendered; 123-01's drift test is green.

**Edge cases to cover explicitly:**
- A PR whose only change is to the governance workflow: flagged, with the AC6
  notice.
- A PR that deletes `CODEOWNERS`: flagged (deleted path in the changed set).
- A protected glob that matches a directory prefix (`docs/decisions/**` against
  `docs/decisions`) behaves as `path_matches_glob` does (`governance.py:88-92`).
- Codex and Copilot scaffolds get the same file: `_write_governance_plane` has
  no host branch (`scaffold.py:4075-4079`); no host-specific code is added.

### Verification scenario

**Preconditions:** a scratch GitHub repository the owner controls, with the
rendered workflow merged to its default branch and `jig-governance` set as a
required check. No secrets configured. A fork under a second account for step 4.

**Invocation:** open each PR below; read the `jig-governance` check result and
log.

**Preserved behavior:** a PR touching no protected path still passes.

**Code revision / dirty-change identity:** the jig commit whose
`render_governance_workflow()` produced the file, recorded with the run links.

| Step | AC | Expected | Observed | Outcome | Evidence |
|------|----|----------|----------|---------|----------|
| 1 | AC1 | PR editing an ADR fails the check | | not-run | |
| 2 | AC1, AC6 | PR that removes `docs/decisions/**` from the workflow's list **and** edits an ADR still fails; log names both paths and shows the self-change notice | | not-run | |
| 3 | AC5 | PR renaming an ADR to `tmp/` fails; log names the old path | | not-run | |
| 4 | AC2, AC3 | Fork PR runs; log shows no head checkout and no secret; token permissions are `contents: read` | | not-run | |
| 5 | Preserved | PR editing only `README.md` passes | | not-run | |

**DoD:**
- [ ] All ACs pass; full test suite green (no regressions).
- [ ] Implementer test coverage exercises each AC with at least one
      fixture. Edge cases listed in the slice are covered explicitly.
- [ ] Each new test has been shown to fail when its feature is removed —
      the test is capable of failing, not vacuously green (mutate the
      feature, watch the test go red, restore).
- [ ] Verification scenario run on the scratch repository; every step `pass`.
- [ ] Host packages rebuilt with `scripts/build_host_packages.py`; drift guard
      green.
- [ ] Reviewed by `reviewer` subagent. Reviewer prompt built by
      `review.py`.
- [ ] Implementation review passed.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation sweep produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were
      deferred during implementation.

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated by `workflow.py status-board`.
      Notes column receives any load-bearing per-slice invariant.
- [ ] Primer hygiene per spec 025-01 rule (only if this slice closes the spec).

**Anti-horizontal-phasing check:** after this slice, an adopter who arms
branch protection has a `jig-governance` check that a PR cannot turn green by
editing the check, renaming a protected file away, or adding a step that runs
its own code.

### Deviation log (after reconciliation)

The original slice is preserved above. Implementation notes:

_To be written at reconciliation._

### Reconciliation sweep

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `README.md` | `no-op` | _TODO at reconciliation._ |
| `docs/specs/README.md` | `updated` | _TODO: regenerated by `workflow.py status-board`._ |
| `docs/product-vision.md` | `no-op` | _TODO at reconciliation._ |
| `docs/architecture.md` | `updated` | _TODO: the "Autonomy governance plane" section calls the job "a `pull_request` job" (`docs/architecture.md:407`)._ |
| Primer surfaces: `CLAUDE.md` / `AGENTS.md` / scaffold templates | `no-op` | _TODO: the Governance-plane hot-cache line may gain "judged from base"._ |
| `docs/inbox.md` | `no-op` | _TODO at reconciliation._ |
| `docs/refinement-todo.md` | `updated` | _TODO: mark "CI-workflow-embedded glob matcher is not parity-pinned" RESOLVED (AC7)._ |
| `docs/memory/**` | `no-op` | _TODO: the rename hole is a learnings candidate._ |
| `docs/decisions/README.md` / ADR index | `no-op` | _TODO at reconciliation._ |
| Additional live prose / generated templates touched by this slice | `no-op` | _TODO at reconciliation._ |
