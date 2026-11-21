---
status: Proposed
dependencies: [adr-0011, adr-0040, adr-0051]
last_verified: 2026-11-21
frame_review: true
---

# ADR-0068: Gate definitions are read from the base ref, not the change under evaluation

## Status

Proposed (2026-11-21)

## Context

The Claude Code team's verification post puts it plainly: "If a change can
modify the check that judges it, the check is broken." Their Code Review reads
`REVIEW.md` from the base branch, never from the pull request (PR). The
investigation record is [R-002](../research/R-002-claude-code-verification-assessment.md)
(mechanism 9, and its open question on hosts and non-GitHub fallbacks).

jig agrees in principle. [ADR-0011](./adr-0011-spec-gate-model.md) says a gate
inside the agent's trust boundary "is satisfiable by the agent", and that real
control is out-of-band, where checks "sit *outside* the agent's trust boundary"
(`adr-0011-spec-gate-model.md:145`, `:152`).
[ADR-0051](./adr-0051-autonomy-governance-plane.md) scaffolds that out-of-band
half: `CODEOWNERS`, a protected-path CI job and a governance doc. But
"out-of-band" has so far meant *runs somewhere else*, not *defined somewhere
the change cannot reach*. Probed 2026-11-21:

- **The governance job is the PR's own copy.** `render_governance_workflow()`
  emits `on: pull_request` (`skills/scaffold-init/governance.py:192-193`), so
  GitHub runs the workflow file from the PR's merge commit, and the
  protected-path list is embedded in that file (`:208`). A PR that edits the
  workflow can drop a path from the list or make the job exit 0, and its own
  check passes. ADR-0051's second kill criterion names this case ("the agent can
  also edit the workflow", `adr-0051-autonomy-governance-plane.md:198-200`). The
  workflow is a protected path, so a required Code Owner review still catches it
  (GitHub reads `CODEOWNERS` from the base, per Assumptions), but the status
  check that branch protection is asked to require does not.
- **Renames escape the check.** The job lists changed files with
  `git diff --name-only origin/<base>...HEAD` (`governance.py:204`). With git's
  default rename detection that prints only a rename's destination, so moving an
  ADR out of `docs/decisions/` is not flagged (git 2.43; `--no-renames` prints
  both paths).
- **Review configuration is read from the working tree.** The `review` block
  that picks the craft / arch / code-health rubric
  ([ADR-0040](./adr-0040-richer-skill-discovery-explicit-candidate-channel.md) D1) is
  read from `<project_dir>/scaffold.json` (`skills/_common/review_config.py:88-92`),
  and a relative rubric path resolves in the project tree (`:126-133`). A branch
  can choose or edit the rubric that reviews it.
- **jig does not run its own plane.** No `CODEOWNERS`, no `jig-governance.yml`,
  and no `protected_paths` in jig's `scaffold.json`.

## Decision Options Considered

### Option A: Status quo — definitions come from the change; CODEOWNERS and branch protection are the backstop
- **Pros:** No change. GitHub reads `CODEOWNERS` from the base branch (an
  assumption, below), so once "Require review from Code Owners" is armed, a PR
  that edits the workflow or a protected file still needs an owner.
- **Cons:** The `jig-governance` check is self-judging, so it is only as good as
  Code Owner review, which makes the check redundant where it is armed and
  beatable where only the status check is required. The rename hole stays. A
  branch picks its own reviewer rubric silently. ADR-0051's kill criterion stays
  half-met.

### Option B: Read definitions from the base ref — `pull_request_target` diff-only out-of-band, base-ref read with a notice in-band (recommended)
- **Pros:** GitHub runs the base branch's copy of a `pull_request_target`
  workflow, so both the job and its embedded list come from the base; a PR cannot
  change what judges it, and a definition change takes effect only after merge.
  It works for fork PRs. The in-band half applies the base config and says when
  the branch modifies it, which is the honest ceiling for a check inside the
  agent's trust boundary (ADR-0011). One `_common` read seam serves review config
  now and spec 127's review rules next.
- **Cons:** **`pull_request_target` runs with the base repository's token and
  any secrets, including for fork PRs.** A job that checks out or runs PR code
  under it hands both to the PR author (the "pwn request" pattern). The job must
  therefore stay diff-only, hold `contents: read` only, reference no secrets, and
  keep PR-controlled strings out of scripts, pinned by a static test, because a
  later well-meaning edit ("also run the linter here") reopens the hole. The PR
  that introduces or upgrades the workflow is not judged by it. GitHub-only.

### Option C: Keep `on: pull_request`, read the list from the base inside the job
The job runs `git show origin/<base>:<definition>` for its list and flags any PR
that edits the workflow.
- **Pros:** No secrets exposure. Simple to render.
- **Cons:** The job's *steps* are still the PR's copy, so a PR can delete the
  base read or the self-check along with everything else. Only the data is
  anchored; the job is not. In practice it falls back to Option A's Code Owner
  backstop.

### Option D: Signed or hashed definitions
Record a hash (or an owner signature) of each definition and verify it at check
time.
- **Pros:** Forge-agnostic; detects tampering offline.
- **Cons:** The expected hash or the key must itself live somewhere the change
  cannot edit, which is the base ref or an out-of-band secret, so it reduces to
  Option B or to key management a solo maintainer will not keep up. servo's
  freeze hashes are described as "tripwires for honest drift … not a sandbox"
  (R-002) for the same reason.

### Option E: Enforce in hooks
A `PreToolUse` / `PostToolUse` hook refuses edits to definition files.
- **Pros:** No forge dependency.
- **Cons:** Already rejected as ADR-0051 Option C: it violates ADR-0011, and the
  hook runs with the privileges of the agent it governs. It also guards the
  editing session, not the change that reaches review. The refinement-todo
  entry "hard `PreToolUse` gate protecting `docs/decisions/**`" stays deferred
  on its own trigger (the maintainer's "defer 3 for now until we see it
  explicitly hitting ADRs in a recurrent way"); this ADR neither fires nor
  resolves it, and builds the out-of-band control ADR-0011 prefers instead.

### Option F: Option B, but in-band helpers refuse when the branch modifies a definition
- **Pros:** Stronger signal in the session.
- **Cons:** Base-reading already stops the modification from taking effect;
  refusing as well blocks a branch that legitimately proposes a new review config
  from being reviewed at all. An in-band refusal is still satisfiable by the
  agent (ADR-0011). Whether a gate warns or blocks is
  [ADR-0070](./adr-0070-gate-modes-off-observe-enforce.md)'s question (off /
  observe / enforce), not this one's.

## Recommended Decision

**Option B.** Built by [spec 123](../specs/123-base-anchored-gate-definitions/spec.md).

1. **Principle.** A gate's definition — the data and the job that decide
   pass or fail — is read from the base ref the change targets, never from the
   change. Where a gate cannot read the base, it falls back to the working tree
   and says so. One exception: when the file is absent at the base because the
   branch adds it, and it would judge the change that adds it, a consumer may
   treat it as absent instead of falling back (spec 127's rules file;
   [123-03](../specs/123-base-anchored-gate-definitions/slice-03-review-config-from-base.md) BR-3).
2. **What counts as a definition, now.** The governance job and its
   protected-path list; the `review.*` config and any in-repo rubric it names.
   Spec 127's review rules will be read the same way. Other gates opt in through
   the same seam when they gain a project-editable definition.
3. **Out-of-band (GitHub).** The scaffolded `jig-governance` workflow triggers on
   `pull_request_target`. It checks out the base side only, reads the PR's head
   commit as data, lists changed paths against the merge base with rename
   detection off, holds `contents: read` only, references no secrets, and passes
   event values to scripts through `env:`. A static test on the rendered YAML
   pins all of this. The governance doc tells adopters never to add a step that
   runs PR code to this workflow, and why.
4. **In-band (jig helpers).** Helpers read definitions through one `_common`
   seam (base ref by spec 103's integration-base rule; working tree as a stated
   fallback). When the branch modifies a definition, the helper applies the base
   version and tells the orchestrator (stderr) and, for review passes, the
   reviewer (a prompt block). It never refuses. `JIG_BASE_DEFINITIONS=0` restores
   the working-tree read and is recorded as a gate bypass.
5. **Which base.** Definitions are read from the base branch's tip (what will
   judge the change at merge); the changed-path set is computed against the merge
   base.
6. **Hosts and forges.** The agent host does not matter for the CI half: the
   workflow is a forge artifact written identically for Claude Code, Codex and
   Copilot CLI scaffolds (`skills/scaffold-init/scaffold.py:4075-4079`). The
   in-band seam is plain git; under Copilot it inherits the existing
   runtime-command-resolution caveat (refinement-todo "Copilot skill-body +
   hook-command `${CLAUDE_PLUGIN_ROOT}` path rewrite"), no worse. On a forge
   other than GitHub jig scaffolds no job, as today (ADR-0051 Assumptions), and
   the governance doc names that forge's own code-owner approval on the target
   branch as the base-anchored control.
7. **jig dogfoods it.** jig carries the plane rendered by `governance.py`,
   drift-tested. It stays inert until the owner arms branch protection, which
   this ADR does not decide.

### Relationship to existing ADRs

- **[ADR-0051](./adr-0051-autonomy-governance-plane.md) — extends, does not
  supersede.** ADR-0051 decides that a protected-path CI job exists and what it
  protects; it does not fix the trigger. This ADR fixes the trigger and the
  definition source, and is the mechanism behind ADR-0051's second kill
  criterion. ADR-0051's text needs no change; adding a pointer to it would be an
  amendment and needs owner approval (spec 102).
- **[ADR-0011](./adr-0011-spec-gate-model.md) — consistent.** It sharpens
  "out-of-band": outside the agent's trust boundary must also mean outside the
  change. The in-band half stays a deliberateness signal.
- **[ADR-0040](./adr-0040-richer-skill-discovery-explicit-candidate-channel.md) —
  extends D1.** Changes where the `review` block is read, not its schema or the
  config → pick → baseline precedence.
- **[ADR-0060](./adr-0060-unattended-execution-write-boundary.md) (Proposed) —
  unrelated surface, complementary.** That ADR governs the push / PR boundary
  inside the session; this one governs what judges the PR once it exists.
- **[ADR-0055](./adr-0055-leanness-lens-folds-into-existing-passes.md) —
  consistent.** No new review pass or gate; existing passes gain a notice.
- **[ADR-0022](./adr-0022-pluggable-oracle-boundary.md) C5 — unrelated.** Not
  re-proposed.
- **Siblings from R-002.** [ADR-0069](./adr-0069-commit-bound-verification-evidence.md)
  anchors *what was judged* (a commit); this ADR anchors *what judges*.
  [ADR-0070](./adr-0070-gate-modes-off-observe-enforce.md) owns warn vs block.
  [ADR-0072](./adr-0072-diff-triggered-review-rules.md) reads its rules through
  point 4's seam. servo ADR-0051 / spec 045 (servo numbering) applies the same
  principle to servo's freeze. PR #230's proposed fix-evidence separation
  (evidence-modifying fixes need owner review, landing in the scaffolded
  `governance.md`) is the same post item from the other side; both edit
  `render_governance_doc`, so reconcile at merge.

## Consequences

**Becomes easier:**
- An armed `jig-governance` check cannot be turned green by the PR it judges,
  including by editing the check or renaming a protected file away.
- A branch cannot quietly choose its own review rubric; the reviewer is told
  when it tries.
- Spec 127 gets a ready read path for its rules file.
- jig feels its own governance plane, including its noise, before adopters do.

**Becomes harder:**
- Changing a definition now takes two steps: merge it, then it applies. Testing
  a new review config on a branch needs `JIG_BASE_DEFINITIONS=0`.
- The workflow carries a security constraint every future editor must keep;
  the static test is the guard, and it must not be loosened casually.
- Adopters upgrading from `on: pull_request` get one PR the check cannot judge;
  if the check is already required, that PR needs a deliberate owner merge.
- The in-band notice does not stop the reviewer from reading an edited in-repo
  rubric file; it only makes the edit visible (open question below).

## Assumptions

- **GitHub behaviour, unprobed here** (docs were egress-blocked; spec 123-02's
  DoR probes them on a scratch repository):
  - for `pull_request`, GitHub runs the workflow file as it is in the PR (its
    merge commit) — the premise of the Context's first bullet;
  - a `pull_request_target` workflow runs the file from the base side, and its
    job can be a required status check on the PR;
  - GitHub reads `CODEOWNERS` from the PR's base branch;
  - a PR that switches the trigger from `pull_request` to
    `pull_request_target` runs neither on itself;
  - `refs/pull/<n>/head`, fork PRs included, is fetchable with `contents: read`;
  - for a PR targeting a non-default branch, which branch's copy of the
    workflow runs is unknown; if it is the default branch's, point 5's "base"
    means the default branch for that job.
- The in-band seam assumes a base ref is usually resolvable in a working
  checkout (spec 103's rule: a non-own upstream, `origin/main`, `origin/master`).
  Where it is not, the fallback is the working tree, stated aloud.

## Kill criteria

- **A `pull_request_target` job cannot be made a required check on the PR**
  (or does not report on the PR's head): Option B's out-of-band half fails.
  Fall back to Option C and label it honestly as data-only anchoring, with Code
  Owner review as the real control.
- **An adopter needs the governance job to run PR code** (build, test): do not
  relax point 3; split that work into a separate `pull_request` workflow. If that
  split proves unworkable for real adopters, revisit.
- **The in-band notice fires on most branches in jig or an adopter** without
  catching a real self-modification: it has become noise and should be narrowed
  (for example to the `review` block only) before anything builds on it.

## Open questions

- Should `scaffold.json` join `PROTECTED_PATHS`? It holds `protected_paths` and
  the `review` block, both definitions, but every scaffold upgrade PR would then
  need owner review.
- In in-repo mode the gate *code* (`.claude/skills/**`) is in the project and
  editable by a branch. Protect it, or accept that plugin-only mode is the
  answer? The same question applies to jig's own CI thresholds, such as the
  routing-eval floor `MIN_RANK1_RATE` (`scripts/skill_routing.py:59`), which
  `ci.yml` reads from the PR.
- Should a review pass materialize the base copy of an in-repo rubric for the
  reviewer, instead of only warning?
- Is a portable `governance.py check-diff --base <ref>` worth shipping for
  non-GitHub CI? Not until a non-GitHub adopter asks.
