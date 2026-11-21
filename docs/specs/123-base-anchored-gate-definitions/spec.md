---
status: DRAFT
skill: scaffold-init
use_cases: [UC-17, UC-7, UC-20]
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 123: Base-anchored gate definitions

> Implements [ADR-0068](../../decisions/adr-0068-base-anchored-gate-definitions.md)
> (Proposed). Investigation record: [R-002](../../research/R-002-claude-code-verification-assessment.md).
> **Status: recorded, not yet built** — the ADR must be Accepted before 123-01
> moves past DRAFT.

## Overview

The Claude Code team's rule (R-002, mechanism 9): "If a change can modify the
check that judges it, the check is broken." Their Code Review reads `REVIEW.md`
from the base branch, never from the pull request (PR). jig has three places
where the change under evaluation supplies the definition that judges it:

1. **The scaffolded governance check judges a PR with the PR's own copy.**
   `governance.render_governance_workflow()` emits `on: pull_request`
   (`skills/scaffold-init/governance.py:192-193`), so GitHub runs the workflow
   file from the PR's merge commit. The protected-path list is embedded in that
   same file (`governance.py:208`). A PR that edits
   `.github/workflows/jig-governance.yml` can drop `docs/decisions/**` from the
   list, or make the job exit 0, and its own check goes green. The workflow file
   is a protected path, so owner review still catches it **once Code Owner review
   is required** — but the `jig-governance` status check, the part ADR-0051 asks
   branch protection to require, is self-judging. This is the case ADR-0051's
   second kill criterion names ("the agent can also edit the workflow",
   `docs/decisions/adr-0051-autonomy-governance-plane.md:198-200`).
   A second hole, probed 2026-11-21 with git 2.43: the job's
   `git diff --name-only origin/<base>...HEAD` (`governance.py:204`) lists only
   the destination of a rename, so a PR that moves an ADR out of
   `docs/decisions/` is not flagged (`--no-renames` lists both paths).
2. **Review configuration is read from the working tree.**
   `review_config._raw_review_block` reads `<project_dir>/scaffold.json`
   (`skills/_common/review_config.py:88-92`), and a relative rubric path resolves
   inside the project tree (`review_config.py:126-133`). A branch can repoint its
   own craft / arch / code-health rubric, or edit the in-repo rubric it already
   points at, and the review that judges the branch uses the edited version.
3. **jig does not run its own governance plane.** jig has no `CODEOWNERS` and no
   `jig-governance.yml` (`.github/workflows/` holds only `ci.yml`,
   `pr-title.yml`, `release.yml`), and its `scaffold.json` has no
   `protected_paths` key, so the `jig-boundary-change-warn` hook jig registers for
   itself (`.claude/settings.json:69`) reads `[]`
   (`hooks/scripts/lib/protected_paths.py:74-80`) and never fires. "We dogfood
   the workflow we build" does not yet hold for this part.

## Decisions

- **D1 — A gate's definition comes from the base ref the change targets**
  (ADR-0068). "Definition" means the data and job that decide pass/fail: the
  protected-path list and governance job, the `review.*` config and the in-repo
  rubric it names, and (later) spec 127's review rules.
- **D2 — Out-of-band (GitHub): `pull_request_target`, diff only.** The
  scaffolded job runs from the base branch, reads the PR's changed paths as data,
  and never checks out, runs, or installs PR content. Least-privilege token, no
  secrets, pinned by a static test.
- **D3 — In-band (jig helpers): read from base, warn, never refuse.** A local
  helper runs inside the agent's trust boundary (ADR-0011), so the honest ceiling
  is to apply the base definition and make a modification visible. Turning the
  warning into a refusal is spec 125's job (gate modes), not this spec's.
- **D4 — jig dogfoods the generated plane; arming stays the owner's call.** jig's
  copy is rendered by `governance.py` and drift-tested, not hand-written. Branch
  protection is a server-side setting no slice here changes.

**Non-goals.** Arming branch protection on jig. In-process hook enforcement
(rejected in ADR-0051 Option C; the deferred "hard `PreToolUse` gate protecting
`docs/decisions/**`" entry in `docs/refinement-todo.md` is untouched — see
ADR-0068). Binding review evidence to a commit (spec 124). Off / observe /
enforce modes (spec 125). The review-rules file itself (spec 127, which reuses
123-03's read path). Anchoring jig's helper *code* in in-repo mode, or jig's own
CI thresholds (ADR-0068 open questions). A job for non-GitHub forges.

## Assumptions

<!-- Spec 064-02 / ADR-0020 — grounding-by-probe (risk-gated). -->

- **Probed 2026-11-21 (jig `deb5eca`):** the Overview's file and line citations;
  `_write_governance_plane` overwrites its three files and is host-agnostic,
  called on both the with-machinery and plugin-only paths
  (`skills/scaffold-init/scaffold.py:3241-3244`, `:3555-3577`, `:4075-4079`);
  `render_codeowners` already takes `owner` (`governance.py:140`) but the CLI has
  no flag for it (`governance.py:468`); host packages carry copies of
  `governance.py` and `review_config.py` under `hosts/{claude,codex,copilot}/`;
  spec 103's base-resolution rule lives in `hooks/scripts/lib/git_freshness.py:117`
  (`resolve_target`), and hook libs may import `_common`
  (`hooks/scripts/lib/entry_gate.py`).
- **Unverified GitHub behaviour (docs egress-blocked; probe in 123-02's DoR):**
  - **G0** — for `pull_request`, GitHub runs the workflow file as it is in the
    PR (its merge commit). Overview point 1 rests on this.
  - **G1** — a `pull_request_target` workflow runs the file from the base side
    and its job can be selected as a required status check on the PR.
  - **G2** — GitHub reads `CODEOWNERS` from the PR's base branch.
  - **G3** — a PR that switches the trigger from `pull_request` to
    `pull_request_target` runs neither variant on itself, so a required
    `jig-governance` check stays pending on that one PR.
  - **G4** — `refs/pull/<n>/head` (fork PRs included) is fetchable by a job
    holding only `contents: read`.
  - **G5** — for a PR targeting a non-default branch, which branch's copy of a
    `pull_request_target` workflow runs (base or default) is unknown.
- **Unverified, jig-specific:** turning on the in-boundary nudge in jig (123-01
  AC3) may be noisy, because jig edits `docs/decisions/**` on most specs. If it
  is, that is a finding about the nudge's wording for every adopter, recorded in
  `docs/inbox.md`, not a reason to keep jig off its own plane.

## Decomposition

SPIDR axes: **Paths** (out-of-band CI vs in-band helper) and **Interfaces**
(scaffold output, a `_common` read seam). Three slices:

- **123-01 (Interfaces):** jig carries the governance plane `scaffold-init`
  writes, rendered by `governance.py` and drift-tested. No behaviour change for
  adopters beyond a `--owner` CLI flag.
- **123-02 (Paths — out-of-band):** the scaffolded `jig-governance` check is
  judged by the base branch's job and list, counts renames, and never runs PR
  content. Re-renders jig's copy, so it depends on 123-01.
- **123-03 (Paths — in-band):** `review.py` reads `review.*` config from the
  base ref and warns when the branch modifies it, through a shared `_common`
  seam spec 127 reuses. Independent of 123-01/02.

**Anti-horizontal-phasing.** 123-01 alone puts jig's own PRs under the same
signal adopters get. 123-02 alone makes an adopter's armed check unbeatable by
the PR it judges. 123-03 alone stops a branch from choosing its own reviewer
rubric silently. None is an internal-only layer.

## Slices

- [123-01 — dogfood-governance-plane](slice-01-dogfood-governance-plane.md) — jig's own `CODEOWNERS`, `jig-governance.yml`, `docs/governance.md` and `protected_paths`, rendered by `governance.py` and drift-tested.
- [123-02 — base-judged-governance-check](slice-02-base-judged-governance-check.md) — `pull_request_target` diff-only job, rename-aware, least-privilege, statically pinned; embedded-matcher parity test.
- [123-03 — review-config-from-base](slice-03-review-config-from-base.md) — `review.*` config read from the base ref through a shared `_common` seam, with a warning when the branch modifies it.
