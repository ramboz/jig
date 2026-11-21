---
status: DRAFT
dependencies: [adr-0068, adr-0040]
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

## Slice 123-03 — review-config-from-base

**Goal:** when `review.py` builds or records a craft, arch or code-health pass
on a branch, it reads the `review.*` config from the base ref, and tells both
the orchestrator and the reviewer when the branch modifies that config or the
in-repo rubric it names. The read goes through one `_common` seam that spec 127
(diff-triggered review rules) reuses for its rules file.

**Decision:** spec 123 D3 / ADR-0068: apply the base definition and warn; never
refuse. A new `_common` module and a changed read path for `review_config`,
hence `arch_review`.

**DoR:**
- ✅ ADR-0068 Accepted (spec preamble).
- ✅ Every `review.*` read goes through `review_config._raw_review_block`
  (`skills/_common/review_config.py:79-105`), consumed by
  `_resolve_richer_for_pass`, `_substrate_lines` and the prompt subcommands in
  `skills/independent-review/review.py` (`:813`, `:850-861`, `:2249`).
- ✅ Spec 103's integration-base rule exists (`hooks/scripts/lib/git_freshness.py:117`,
  `resolve_target`: a non-own `@{upstream}`, else `origin/main`, else
  `origin/master`); hook libs may import `_common`
  (`hooks/scripts/lib/entry_gate.py`).
- ✅ `cross_ref_state._show` already reads a file at a ref with
  `git show <ref>:<path>` (`skills/_common/cross_ref_state.py:115-117`).

**Assumptions:** None beyond the spec's. The base is the base branch's tip, not
the merge base: the definition that will judge the change at merge is the one
that applies (the same choice as `pull_request_target` in 123-02).

**Acceptance Criteria:**

1. **One seam.** A new `_common` module exposes `resolve_base(project_dir)`,
   `read_at_base(project_dir, relpath)` → text plus `source`
   (`base` / `working-tree`), the ref used, and a reason when it fell back; and
   `modified_on_branch(project_dir, relpaths)` → the subset changed against the
   merge base with the base, counting commits, uncommitted edits and untracked
   files. It never raises and never fetches.
2. **One base rule.** `resolve_base` is spec 103's rule, implemented once:
   `git_freshness.resolve_target` delegates to it, and the existing
   `test_git_freshness.py` stays green. When no base resolves, reads fall back to
   the working tree.
3. **`review_config` reads the base.** `_raw_review_block` gets `scaffold.json`
   through `read_at_base`, so `configured_value`, `configured_skill`, the
   richer-skill resolver and the recorded `substrate:` all see the base value.
   A track-local project (ADR-0033, `scaffold.json` below the repository root)
   reads the right file.
4. **A modification is visible.** When the branch changes the parsed `review`
   block (not merely other keys in `scaffold.json`), or changes a file under a
   configured rubric path that resolves inside the repository, the craft / arch /
   code-health prompt builders (a) write one stderr line naming the paths and
   (b) add a short block to the reviewer prompt: the branch modifies the review
   configuration or rubric that judges it, the base definition was applied, and
   the change is an in-scope finding. Exit codes are unchanged.
5. **Honest fallbacks.** In a git repository with no resolvable base, or a
   `scaffold.json` absent at the base, the read uses the working tree and the
   stderr line says so once, with the reason. Outside a git repository behaviour
   and output are exactly today's. A malformed base config raises the same
   `ReviewConfigError` as today, naming the ref.
6. **Bypass.** `JIG_BASE_DEFINITIONS=0` restores today's working-tree read with
   no notice, checked with `parsing.env_gate_enabled`
   (`skills/_common/parsing.py:88`) and recorded with
   `gate_telemetry.emit_gate_bypass` (`skills/_common/gate_telemetry.py:24`).

### Behavioral rules

| Rule | Operation/control | Actor | State/precondition | Outcome | Rationale | AC |
|------|-------------------|-------|--------------------|---------|-----------|----|
| BR-1 | resolve `review.<category>_skill` | `review.py` | base resolves; branch leaves the `review` block alone | base value; no notice | the merged config is the team's policy (ADR-0040 D1) | AC3 |
| BR-2 | same | `review.py` | branch edits the `review` block | base value; stderr notice + prompt block | a change cannot pick its own judge | AC3, AC4 |
| BR-3 | same | `review.py` | branch adds a `review` block absent at base | baseline (no config); notice says it applies after merge | same as BR-2 | AC4 |
| BR-4 | same | `review.py` | base names an in-repo rubric the branch edits or deletes | base value; notice names the rubric paths | the reviewer still reads the working-tree file, so say so | AC4 |
| BR-5 | same | `review.py` | git repo, no base ref | working tree; one fallback notice | fail open, never silent | AC5 |
| BR-6 | same | `review.py` | not a git repo | working tree; no notice | nothing to anchor to; today's behaviour | AC5 |
| BR-7 | same | operator | `JIG_BASE_DEFINITIONS=0` | working tree; bypass recorded | a deliberate local experiment | AC6 |

**Edge cases to cover explicitly:**
- Uncommitted edits to the `review` block while on the base branch itself:
  BR-2 applies (the working tree is the change).
- A bare-name config that resolves to a user-scope skill outside the
  repository: no rubric-path check (BR-4 does not apply).
- A `scaffold.json` change to `installed_tiers` only: no notice.
- Detached `HEAD`: `resolve_base` falls through to `origin/main` /
  `origin/master`, as spec 103's rule does.

**DoD:**
- [ ] All ACs pass; full test suite green (no regressions).
- [ ] Implementer test coverage exercises each AC with at least one
      fixture. Edge cases listed in the slice are covered explicitly.
- [ ] Each new test has been shown to fail when its feature is removed —
      the test is capable of failing, not vacuously green (mutate the
      feature, watch the test go red, restore).
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

**Anti-horizontal-phasing check:** after this slice, a branch that repoints
or edits its own review rubric is reviewed with the base branch's rubric
choice, and both the orchestrator and the reviewer are told the branch tried
to change it.

### Deviation log (after reconciliation)

The original slice is preserved above. Implementation notes:

_To be written at reconciliation._

### Reconciliation sweep

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `README.md` | `no-op` | _TODO at reconciliation._ |
| `docs/specs/README.md` | `updated` | _TODO: regenerated by `workflow.py status-board`._ |
| `docs/product-vision.md` | `no-op` | _TODO at reconciliation._ |
| `docs/architecture.md` | `updated` | _TODO: the new `_common` seam and its consumers (`review_config`, `git_freshness`, later spec 127)._ |
| Primer surfaces: `CLAUDE.md` / `AGENTS.md` / scaffold templates | `no-op` | _TODO at reconciliation._ |
| `docs/inbox.md` | `no-op` | _TODO at reconciliation._ |
| `docs/refinement-todo.md` | `no-op` | _TODO: record ADR-0068's open questions that stay open._ |
| `docs/memory/**` | `no-op` | _TODO: glossary term for the base-anchored read, if it earns one._ |
| `docs/decisions/README.md` / ADR index | `no-op` | _TODO at reconciliation._ |
| `skills/independent-review/SKILL.md` | `updated` | _TODO: say where review config is read from and what the notice means._ |
