---
status: DRAFT
---

# Spec 034: Federation tier (multi-repo orgs)

## Overview

Jig today assumes a single-repo project: `docs/specs/`,
`docs/decisions/`, one `CLAUDE.md` hot cache, and a status board all
scoped to one repo with one main branch. This works well for solo
devs and small teams.

For organizations running ~40 repositories across 40–60 engineers —
with a central code-and-docs entry-point repo, varying degrees of
repo coupling, shared ownership, and multi-host GitHub setups
(public + private + GHEC behind SSO with different users per host) —
the single-repo assumption breaks in five ways:

1. **Cross-repo specs have no home.** A feature that touches N repos
   gets either duplicated into N specs or pinned in one repo with
   the other N−1 unaware.
2. **ADRs and glossary drift.** Without a shared layer, decisions
   and terminology fork silently per repo.
3. **Reviewers can't see the seams.** The reviewer subagent works
   inside one tree; cross-repo contract reviews need different
   plumbing.
4. **The ~40% context ceiling cannot accommodate 40 hot caches.**
   Loading them all is the obvious wrong default; loading only one
   loses cross-repo context entirely.
5. **Standalone discovery breaks down.** Spec numbering and
   status-board regeneration assume one repo; an engineer onboarding
   to the org can't see "what's in flight where" without manually
   walking 40 trees.

This spec introduces a **Federation tier (Tier 2)** — a
conditionally-scaffolded skill bundle plus federation-aware tweaks
to existing Tier 0/1 skills — that lets one repo act as the
**central** for an org and the others as **members**, without
changing how solo / standalone projects work.

The Federation tier is the first promotion *into* Tier 2 from its
deliberately-empty state, and the first that responds to a named
user signal rather than speculation. See vision §"How new work
enters jig" for the bar.

## Why now

- **First named Tier 2 user signal.** A real 40-repo / 40–60
  engineer organization with a central entry-point repo asked for
  federation. Vision §"How new work enters jig" reserves Tier 2 for
  exactly this case.
- **Tier 0/1 surface is stable.** Tier 0 + Tier 1 are effectively
  complete (per product-vision MVP scope); federation can extend a
  steady baseline without churning it.
- **Host adapter (spec 033) is concurrent.** Both touch
  `scaffold-init`, configuration shape, and the boundary between
  renderer and helper. Designing federation while 033 is in flight
  avoids two retrofits.

## Goals

1. **Three roles** — `standalone` / `central` / `member` — supported
   via `.jig/scaffold.json`. Existing standalone users see no
   behavioral change.
2. **Tier 2 skill bundle** (`repo-registry`, `cross-repo-spec`,
   `federated-status`, `context-pull`, `repo-sync`) installable
   conditionally, with skills no-op-ing based on role rather than
   tier 2 being split into per-role sub-bundles.
3. **`repos.yaml` registry schema** covering hosts, repos, roles,
   and declared contract surfaces. Sits in the central repo's
   `docs/`.
4. **Multi-host GitHub auth without `gh auth switch`.** Each repo
   declares its host; helpers run `gh` per-command with `--hostname`
   / `GH_HOST` env scoping. Global `gh` state is never mutated by
   jig.
5. **Federation-aware tweaks to existing Tier 0/1 skills + hooks**
   that degrade to no-op outside federation. No new skill is needed
   for the read-through behaviors (memory-sync, spec-workflow,
   adr-workflow, independent-review, plus two hooks).
6. **Member lifecycle** — `add`, `remove`, `update`, `audit`, with
   archive-don't-delete semantics on removal and clear failure
   modes on drift / version mismatch.
7. **Pull-based drift detection.** Members don't poll; a
   SessionStart hook in member mode surfaces a one-line nudge when
   central conventions or jig version drift past local cache.
8. **Migration path** from existing standalone installs into
   federation, idempotent and re-runnable.

## Non-goals

- **A project management surface.** The federated status board
  aggregates *spec state*, not estimates / roadmaps / capacity
  planning. Same line jig already holds for single-repo.
- **Cross-vendor host support.** v1 ships GitHub only (public,
  private, GHEC). Adapter shape leaves room for GitLab / Bitbucket
  / Azure DevOps / Gitea later, but no files are generated for
  them.
- **A central runtime / daemon / service.** Federation runs through
  git, `gh`, and local state files. Nothing to host. Nothing to
  deploy.
- **Mutating `gh` global state.** Jig never invokes
  `gh auth switch`. Helpers respect whichever account is configured
  per host.
- **Auto-pushing central updates to members.** Pull-based; the
  member decides when to consume updates via
  `jig:repo-sync update`.
- **Governance of org-wide ADRs.** This spec covers how org ADRs
  are *stored* + *propagated*, not who proposes / accepts them.
  That stays a team-process question outside jig's scope.
- **Replacing existing ticket systems.** Jira / Linear / GitHub
  Issues remain the ticket layer; jig specs are the engineering
  artifact, as in single-repo mode.

## Role model

| Role | Where used | Tier 2 skills installed | Role-active subset |
|---|---|---|---|
| `standalone` | Today's default | None | — |
| `central` | One repo per org | All Tier 2 | `repo-registry`, `cross-repo-spec`, `federated-status`, `context-pull` |
| `member` | The other ~39 repos | All Tier 2 | `cross-repo-spec`, `context-pull`, `repo-sync` |

Tier 2 *installs* uniformly when `role != standalone`; individual
skills refuse with a clear message when invoked in the wrong role
(`federated-status` on a member, etc.).

## SPIDR analysis

| Technique | Question | Decision |
|---|---|---|
| **S** - Spike | Is research needed before designing? | **No.** Every component is concrete: registry shape, gh auth scoping, scaffold-init extension, frontmatter contract. Codex-style v1/v2 deferral does not apply. |
| **P** - Path | One big landing or phased? | **Phased.** Slices 1–6 are MVP federation (registry + adapter, add/list, scaffold-init extension, cross-repo-spec, status, context-pull). Slice 7 hardens Tier 0/1 tweaks. Slices 8–11 are lifecycle + migration + the contract-surface hook. |
| **I** - Interface | Where is the federation boundary? | **`repos.yaml` + host adapter.** Schema sits in central; helpers consult it; nothing else mediates between central and members. |
| **D** - Data | What data shape is foundational? | **Registry schema (`hosts:` + `repos:`) + scaffold.json fields (`role`, `central_repo`).** Slice 1. |
| **R** - Rules | What rules govern lifecycle? | **Archive-don't-delete on remove; pull-based drift detection; never mutate `gh` global state; central conventions win on conflict; standalone behavior unchanged.** |

## Known constraints

- **`gh` CLI is the only adapter primitive in v1.** No raw GitHub
  API calls; no other vendors.
- **`gh auth switch` must NOT be invoked by any helper.** Only
  respected. Mutates global state; breaks parallel sessions.
- **`JIG_HOST_<id>_TOKEN` env vars are the only auth override.**
  For CI / headless use. Interactive sessions go through `gh`'s
  normal chain.
- **Spec numbering stays scope-local.** `workflow.py new` reserves
  on the *local* repo's `origin/main`; no global counter.
  Cross-repo specs use `parent_spec:` frontmatter pointers, not a
  unified ID space.
- **Central repo is not a critical path for per-repo slices.**
  Federation must not slow down or block routine single-repo work
  in a member repo.
- **Conventions hierarchy is read-only on the member side.**
  Central `conventions.md` is fetched, not copied; local
  `conventions.md` may extend but not contradict. Helper
  enforcement is in slice 7.
- **No backward-compat shims for the host adapter contract.** If
  `repos.yaml` schema changes after v1 lands, it changes wholly
  (per product-vision design principle #6).
- **No changes to `docs/conventions.md` without explicit
  approval.** Any conventions-affecting decision in implementation
  needs a deliberate human approval gate.
- **Context economy is per-session, not per-org.** Cross-repo work
  must never auto-load more than the local repo's hot cache + the
  central primer. Additional repos load via `context-pull`
  explicitly.

## Slices

- [034-01 — registry-schema-and-host-adapter](slice-01-registry-schema-and-host-adapter.md)
- [034-02 — repo-registry-add-and-list](slice-02-repo-registry-add-and-list.md)
- [034-03 — scaffold-init-role-member](slice-03-scaffold-init-role-member.md)
- [034-04 — cross-repo-spec-skill](slice-04-cross-repo-spec-skill.md)
- [034-05 — federated-status-aggregator](slice-05-federated-status-aggregator.md)
- [034-06 — context-pull-skill](slice-06-context-pull-skill.md)
- [034-07 — tier0-1-federation-aware-tweaks](slice-07-tier0-1-federation-aware-tweaks.md)
- [034-08 — repo-registry-remove-update-audit](slice-08-repo-registry-remove-update-audit.md)
- [034-09 — repo-sync-and-drift-hook](slice-09-repo-sync-and-drift-hook.md)
- [034-10 — migrate-to-federation](slice-10-migrate-to-federation.md)
- [034-11 — cross-repo-impact-hook](slice-11-cross-repo-impact-hook.md)

## Clarifications

### Q1: When the central repo is unreachable mid-session (network outage, GHEC SSO expired, gh auth issue), how should federation-aware skills behave?
_(category: Edge Cases & Failure Modes)_

Standalone-equivalent ops proceed. Single-repo work continues
uninterrupted; federation-specific calls (cross-repo-spec,
federated-status, repo-sync update) refuse with a clear error naming
central unreachable. Drift hook becomes silent rather than nudging.

### Q2: Can a member repo participate in more than one federation simultaneously (e.g., a shared library belonging to two product orgs)?
_(category: Scope & Boundaries)_

Defer to refinement-todo. v1 enforces exactly one central per member
with a clear error on second-federation attempt. Add to
`docs/refinement-todo.md` with resolution trigger: first real
shared-library user asks. Schema designed to leave the door open.

### Q3: Spec 033 (host-adapter portability) is concurrent and also defines a "host adapter". How should 034's `host_adapter.py` relate to 033's adapter?
_(category: Dependencies & Blockers)_

Orthogonal concerns. 033's adapter is LLM-host rendering (Claude /
Codex). 034's adapter is Git-host scoping (gh.com / GHEC). Different
files, different responsibilities. Document the distinction in spec
034 to avoid confusion.

### Q4: Slice 034-01 introduces both `federation_mode` and `role` in scaffold.json as "mirrors". Is the duplication intentional?
_(category: Terminology Consistency)_

Collapse to one field — `role`. Drop `federation_mode`; keep only
`role` (one of `standalone` / `central` / `member`). Shorter, clearer,
no semantic loss. Update slice 034-01 ACs accordingly.

### Coverage summary

| Category | Status |
|---|---|
| Scope & Boundaries | Resolved |
| Acceptance Criteria Testability | Clear |
| Dependencies & Blockers | Resolved |
| Non-functional Requirements | Partial |
| Edge Cases & Failure Modes | Resolved |
| Terminology Consistency | Resolved |
