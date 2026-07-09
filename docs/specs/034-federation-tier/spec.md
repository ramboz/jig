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
with an existing workspace repo, service catalog, or repo manifest,
split authority for architecture / guidelines / workspace operations,
varying degrees of
repo coupling, shared ownership, and multi-host GitHub setups
(public + private + GHEC behind SSO with different users per host) —
the single-repo assumption breaks in seven ways:

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
6. **Parallel spec collision is discovered too late.** Two engineers
   can start unrelated-looking specs that touch the same files or
   contract surfaces and only discover the overlap at merge time.
7. **Existing multi-repo metadata is already authoritative.** Mature
   teams may already carry workspace manifests, service catalogs,
   package workspaces, GitHub org/team inventories, MCP routing, repo
   tags, and doc-placement rules. Federation must import and adapt that
   substrate rather than creating a second stale registry.

This spec supports **two federation topologies** (see
[ADR-0028](../../decisions/adr-0028-federation-workspace-provider-model.md)),
differing in *where jig state lives*, and ships the lighter one first:

- **Hub-and-referenced (first-supported).** One *hub* repo holds all jig
  state — tracks, specs, ADRs, glossary, routing primer — organized as
  multiple **tracks** (per-track subprojects via
  [ADR-0033](../../decisions/adr-0033-configurable-docs-root.md) / spec 084
  `layout.docs_root="."`). Other repos are **referenced work targets** in a
  `repos.yaml` manifest (`scope:`-tagged to tracks), checked out on demand,
  carrying **no jig state**. Genuinely multi-repo and multi-host, but
  nothing distributed to keep coherent. Grounded in a running project
  (`personalization-workspace`: one hub, ~8 referenced repos across two
  GitHub hosts, three tracks) — the **first consumer**.
- **Peer-members-and-central (escalation — deferred).** Every repo is a
  scaffolded jig *member*; a *central* coordinates them via a membership
  registry, cross-repo specs, read-through authority, and pull-based drift.
  The Spacecat/Mysticat shape. This is the model this spec originally
  assumed as the *only* shape; it is re-scoped as escalation and its slices
  are DEFERRED until a real distributed consumer starts building.

The hub topology answers most of the seven breakages by centralizing jig
state and referencing the rest; the peer topology answers them by
distributing and coordinating state — the heavier contract, deferred until
demanded. Spacecat/Mysticat remains the *peer-tier* validation fixture, not
the normative product shape. Solo / standalone projects remain unchanged.

## Why now

- **A running hub consumer (2026-07-08).** `personalization-workspace` is
  a live hub-and-referenced federation (one hub repo, ~8 referenced repos,
  three tracks) already migrating flat `docs/` into `tracks/` — the hub
  tier's first real consumer, and why the hub tier ships first.
- **First named Tier 2 user signal (peer tier).** A real 35+ repo / 40–60
  engineer organization with existing repo inventory, split
  spec/architecture homes, and multiple GitHub auth paths asked for
  federation. Vision §"How new work enters jig" reserves Tier 2 for
  exactly this scale; the implementation must generalize beyond that
  one team's specific manifest and testing conventions.
- **Tier 0/1 surface is stable.** Tier 0 + Tier 1 are effectively
  complete (per product-vision MVP scope); federation can extend a
  steady baseline without churning it.
- **Host adapter (spec 033) is concurrent.** Both touch
  `scaffold-init`, configuration shape, and the boundary between
  renderer and helper. Designing federation while 033 is in flight
  avoids two retrofits.

## Goals

> **Two-topology note (2026-07-08, [ADR-0028](../../decisions/adr-0028-federation-workspace-provider-model.md)):**
> the goals below were authored for the peer-members model. In the
> **hub tier** (first to build), the relevant goals are: a `hub` role +
> track layout on 084 (goal 1, minus `central`/`member`); a `repos.yaml`
> **reference** manifest (goal 4, minus membership/authority); a multi-host
> repo-**checkout** provider (goal 5); discovery/import (goal 3); migrate
> flat→hub (goal 9); and workspace status across tracks. Goals 6, 10, 11
> apply *cross-track* in the hub tier and *cross-repo* in the peer tier.
> Goals 2 (Tier-2 skill bundle), 7 (member lifecycle), and 8 (pull-based
> drift) are peer-tier only and deferred.

1. **Three roles** — `standalone` / `central` / `member` — supported
   via `.jig/scaffold.json`. Existing standalone users see no
   behavioral change.
2. **Tier 2 skill bundle** (`repo-registry`, `cross-repo-spec`,
   `federated-status`, `context-pull`, `repo-sync`,
   `collision-radar`) installable conditionally, with skills no-op-ing
   based on role rather than tier 2 being split into per-role
   sub-bundles.
3. **Discovery/import adoption path.** Federation can inventory
   existing repo sources such as workspace manifests (`mani.yaml` /
   `workspace.yaml` as one bundled example), service catalogs, package
   workspaces, GitHub org/team discovery, hand-authored registries,
   `AGENTS.md`/`CLAUDE.md`, MCP routing, spec homes, OpenAPI files,
   package dependencies, and default branches, then generate a
   reviewable adoption report + draft registry instead of asking mature
   teams to re-enter what they already know.
4. **`repos.yaml` registry schema** covering hosts, repos, roles,
   membership status, authority mappings, import-source provenance,
   and declared or discovered contract surfaces. In simple central
   installs it sits in the central repo's `docs/`; in imported-inventory
   installs it may be generated from and reconciled against the chosen
   source inventory.
5. **Multi-host repo access without global auth mutation.** Each repo
   declares a project-selected access provider (`mcp`, `gh`,
   `github-api`, `git-ssh`, or `local-worktree`). Helpers never invoke
   `gh auth switch`; `gh --hostname` is one provider implementation,
   not the federation contract.
6. **Federation-aware tweaks to existing Tier 0/1 skills + hooks**
   that degrade to no-op outside federation. No new skill is needed
   for the read-through behaviors (memory-sync, spec-workflow,
   adr-workflow, independent-review, plus two hooks).
7. **Member lifecycle** — `add`, `import`, `sync`, `remove`, `update`,
   `audit`, with
   archive-don't-delete semantics on removal and clear failure
   modes on drift / version mismatch.
8. **Pull-based drift detection.** Members don't poll; a
   SessionStart hook in member mode surfaces a one-line nudge when
   central conventions or jig version drift past local cache.
9. **Migration path** from existing standalone installs into
   federation, idempotent and re-runnable.
10. **Collision radar for parallel specs.** Specs can declare an
   advisory `touches:` list in frontmatter; new/resumed work scans
   unfinished specs visible on `origin/main` and the federation
   registry/cache to warn about likely file or contract-surface
   conflicts before branches drift.
11. **Optional verification profile.** Larger installs can declare
    project-specific per-repo validation commands and cross-repo
    workflow checks without making that matrix mandatory for
    small/simple federation users.

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
- **Replacing workspace repos, service catalogs, or local-dev systems.**
  A team's existing environment/control-plane layer remains in place.
  Federation consumes inventory and context through importers; it does
  not become a clone manager, secrets resolver, IDE workspace generator,
  or local-dev harness.
- **Governance of org-wide ADRs.** This spec covers how org ADRs
  are *stored* + *propagated*, not who proposes / accepts them.
  That stays a team-process question outside jig's scope.
- **Replacing existing ticket systems.** Jira / Linear / GitHub
  Issues remain the ticket layer; jig specs are the engineering
  artifact, as in single-repo mode.
- **General code ownership or mandatory locks.** Collision radar is
  an early-warning surface, not a codeowner replacement and not a
  default hard block on parallel implementation.

## Topology model

Federation `role` in `.jig/scaffold.json` selects the topology:

| Role | Topology | Where used | jig state |
|---|---|---|---|
| `standalone` | — | Today's default | this repo only (unchanged) |
| `hub` | **Hub-and-referenced** (first-supported) | the one coordination repo | all here (multi-track); other repos referenced, no jig state |
| `central` / `member` | **Peer-members** (deferred escalation) | central + N scaffolded members | distributed across members |

**Hub tier:** only the hub is a jig citizen. It carries the `repos.yaml`
reference manifest (repos + host + `scope:`→track) and checks referenced
work repos out on demand; there are no member repos to register, no
per-member drift, no cross-repo spec pinning. Tracks (084) organize
concurrent workstreams inside the hub.

**Peer tier (deferred):** the original `central` / `member` roles,
membership registry (`status` = `pending` / `active` / `archived`, tracked
separately from `role`), and read-through authority. Retained in this spec
for when a distributed consumer builds; not installed by the hub tier.

## SPIDR analysis

| Technique | Question | Decision |
|---|---|---|
| **S** - Spike | Is research needed before designing? | **No separate spike.** The Spacecat/Mysticat workspace and guidelines repo supplied the first evidence; slice 034-00 turns that into a repeatable discovery/adoption pass that other repo-operating models can plug into. |
| **P** - Path | One big landing or phased? | **Phased.** Slice 00 proves/imports existing inventory through importer examples. Slices 1–6 are MVP federation (registry + provider adapter, import/add/list, scaffold-init extension, cross-repo-spec, status, context-pull). Slice 7 hardens Tier 0/1 tweaks. Slices 8–11 are lifecycle + migration + contract-surface hook. Slices 12–14 add advisory collision radar. Slice 15 adds the optional verification profile. |
| **I** - Interface | Where is the federation boundary? | **Inventory importers + `repos.yaml` + repo access provider.** `repos.yaml` is the normalized jig view; an existing workspace manifest, service catalog, package workspace, or hand registry can remain the source of truth. |
| **D** - Data | What data shape is foundational? | **Registry schema (`hosts:` + `repos:` + `authorities:` + provider config + import provenance) + scaffold.json fields (`role`, `central_repo`, optional `authority_repos`) + spec/slice `touches:` string-list metadata + typed contract-surface metadata.** |
| **R** - Rules | What rules govern lifecycle? | **Import before duplicate entry; archive-don't-delete on remove; pull-based drift detection; never mutate global auth state; authority-specific conventions win on conflict; collision radar warns by default; standalone behavior unchanged.** |

## Known constraints

- **GitHub is the only repo host family in v1, but `gh` is not the
  only access primitive.** Providers may use MCP, `gh`, GitHub API
  with token env, git-over-SSH, or local worktrees. No GitLab /
  Bitbucket / Azure DevOps / Gitea adapters ship in v1.
- **Spacecat/Mysticat is a validation fixture, not a schema.** The
  fixture should prove that federation handles a large, messy,
  split-authority workspace. It must not make `mani.yaml`, a specific
  testing convention, or MCP-over-`gh` a universal requirement.
- **Inventory importers are examples behind one workflow.** v1 can ship
  built-in importers for `repos.proposed.yaml` and common workspace
  manifest shapes, but the product contract is discover → decide →
  normalize → sync/audit. Future Backstage, Terraform/IaC, package
  workspace, GitHub org/team, or hand-registry importers should fit the
  same pipeline.
- **`gh auth switch` must NOT be invoked by any helper.** Only
  respected. Mutates global state; breaks parallel sessions.
- **Auth is provider-scoped.** `JIG_HOST_<id>_TOKEN` env vars are the
  CI/headless override for GitHub API / `gh` providers; MCP providers
  use configured MCP credentials; SSH providers use the workspace's
  SSH alias / identity setup. Helpers never assume one global GitHub
  identity can see every repo.
- **Spec numbering stays scope-local.** `workflow.py new` reserves
  on the *local* repo's `origin/main`; no global counter.
  Cross-repo specs use `parent_spec:` frontmatter pointers, not a
  unified ID space.
- **Central repo is not a critical path for per-repo slices.**
  Federation must not slow down or block routine single-repo work
  in a member repo.
- **Authority repos can be split.** Simple installs use one central.
  Workspace-scale installs may map `workspace_ops`, `architecture`,
  `guidelines`, `org_rfcs`, and `product_specs` to different repos.
  A member still has one primary federation, but read-through
  authority can come from multiple declared repos.
- **Conventions hierarchy is read-only on the member side.**
  Authority `conventions.md` / glossary / org ADRs are fetched or
  read through cache, not copied; local conventions may extend but
  not contradict. Helper enforcement is in slice 7.
- **No backward-compat shims for the RepoAccessProvider contract.** If
  the provider or `repos.yaml` schema changes after v1 lands, it
  changes wholly (per product-vision design principle #6).
- **No changes to `docs/conventions.md` without explicit
  approval.** Any conventions-affecting decision in implementation
  needs a deliberate human approval gate.
- **Context economy is per-session, not per-org.** Cross-repo work
  must never auto-load more than the local repo's hot cache + the
  central primer. Additional repos load via `context-pull`
  explicitly.
- **Touchset metadata is advisory and intentionally small.** `touches:`
  is a YAML-lite list of repo-relative paths or globs. Cross-repo
  entries use `repo-name:path/to/file` strings. No nested YAML objects
  in v1, because jig's shared frontmatter parser supports scalars and
  string lists only.
- **Contract metadata is richer than touch metadata.** `touches:`
  stays frontmatter-small. Typed contract surfaces live in registry /
  generated federation metadata and may include OpenAPI paths, npm
  packages, event topics, DB migrations/RPCs, and deploy units.
- **Main is the coordination surface, not a live lock service.** A
  spec stub on `origin/main` advertises likely touch intent. Routine
  scope changes do not auto-push on every edit; users update touchsets
  deliberately when scope materially changes.
- **Collision radar is soft by default.** Exact file overlaps,
  overlapping globs, and declared contract-surface edits produce
  warnings. Only paths explicitly marked by project convention as
  exclusive may become a refusal in a later spec or local policy.

## Slices

Re-dispositioned 2026-07-08 into the two topologies (ADR-0028). Hub-tier
slices are the active DRAFT set (re-scoped to hub semantics — the slice
*bodies* still carry peer-model detail and are refined to hub semantics on
pickup); peer-tier slices are **DEFERRED** with the shared resolution
trigger below.

### Hub tier (active — first to build)

> **084 dependency (not free):** the hub layout builds on spec 084
> `docs_root="."`, which delivers layout-aware artifact *paths* only.
> Multi-jig-per-repo coordination, **subtree-aware git anchoring** (per-track
> reserve/land against a shared `main`), and migrate-into-subtree are
> **explicitly deferred by [ADR-0033](../../decisions/adr-0033-configurable-docs-root.md)**
> and must be closed by 034-01 / 034-03 / 034-10 — ADR-0033 flags per-track
> reserve/land as a possible *category mismatch* (the hub tier's biggest
> risk). Cross-repo collision (034-12/13) is computed *locally* over
> referenced-repo paths, not distributed (ADR-0028 A4).

- [034-00 — discovery-and-import-framework](slice-00-workspace-discovery-and-import.md) — import an existing repo inventory into `repos.yaml`.
- [034-01 — registry-schema-and-host-adapter](slice-01-registry-schema-and-host-adapter.md) — `repos.yaml` **reference** manifest schema + multi-host repo **checkout** access (drop roles / membership / authority-mapping).
- [034-02 — repo-registry-add-and-list](slice-02-repo-registry-add-and-list.md) — add / list referenced work repos + `scope:`→track binding.
- [034-03 — scaffold-init-role-member](slice-03-scaffold-init-role-member.md) — re-scope to **hub scaffold**: tracks + `docs_root="."` + routing primer; **must close ADR-0033's deferred multi-jig-per-repo + subtree git-anchoring gaps** (per-track reserve/land — the *category-mismatch* risk).
- [034-05 — federated-status-aggregator](slice-05-federated-status-aggregator.md) — workspace status **across tracks** (local, no network).
- [034-10 — migrate-to-federation](slice-10-migrate-to-federation.md) — migrate a flat repo → hub (carve `docs/` into `tracks/`, author `repos.yaml`).
- [034-12 — touchset-frontmatter-and-preflight](slice-12-touchset-frontmatter-and-preflight.md) — **cross-repo** touchset metadata over referenced-repo paths (`repo:path`), computed hub-local.
- [034-13 — federated-collision-radar](slice-13-federated-collision-radar.md) — **cross-repo** collision radar over referenced-repo paths, computed hub-local (no network), advisory.
- [034-15 — federation-verification-profile](slice-15-federation-verification-profile.md) — per-track / per-referenced-repo verification profile.

### Peer tier (DEFERRED — escalation)

**Resolution trigger (all peer-tier slices):** a real distributed-peer /
multi-member consumer starts *building* (not just a named signal) — i.e. an
org needs jig state scaffolded into many member repos coordinated by a
central. Until then these stay parked.

- [034-04 — cross-repo-spec-skill](slice-04-cross-repo-spec-skill.md) — cross-*repo* spec pinning (distributed jig state).
- [034-06 — context-pull-skill](slice-06-context-pull-skill.md) — pull context from other member repos.
- [034-07 — tier0-1-federation-aware-tweaks](slice-07-tier0-1-federation-aware-tweaks.md) — read-through to authority repos.
- [034-08 — repo-registry-remove-update-audit](slice-08-repo-registry-remove-update-audit.md) — member membership lifecycle.
- [034-09 — repo-sync-and-drift-hook](slice-09-repo-sync-and-drift-hook.md) — member pulls central drift.
- [034-11 — cross-repo-impact-hook](slice-11-cross-repo-impact-hook.md) — cross-*repo* impact hook.
- [034-14 — touchset-closeout-drift-check](slice-14-touchset-closeout-drift-check.md) — cross-repo touchset closeout drift.

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
with a clear error on second-federation attempt, but a single
federation may declare multiple read-only authority repos for
architecture, guidelines, org RFCs, and workspace operations. Add true
multi-federation membership to `docs/refinement-todo.md` with
resolution trigger: first real shared-library user asks.

### Q3: Spec 033 (host-adapter portability) is concurrent and also defines a "host adapter". How should 034's `host_adapter.py` relate to 033's adapter?
_(category: Dependencies & Blockers)_

Orthogonal concerns. 033's adapter is LLM-host rendering (Claude /
Codex). 034's adapter is Git-host scoping (gh.com / GHEC). Different
files, different responsibilities. Document the distinction in spec
034 to avoid confusion.

2026-06-21 update: rename 034's implementation concept to
`RepoAccessProvider` in prose and code to avoid overloading "host
adapter." The provider boundary is repo-content/status access; the
spec 033 host adapter boundary is prompt/rendering portability.

### Q4: Slice 034-01 introduces both `federation_mode` and `role` in scaffold.json as "mirrors". Is the duplication intentional?
_(category: Terminology Consistency)_

Collapse to one field — `role`. Drop `federation_mode`; keep only
`role` (one of `standalone` / `central` / `member`). Shorter, clearer,
no semantic loss. Update slice 034-01 ACs accordingly.

### Q5: Should collision radar block a second engineer from starting overlapping work?
_(category: Scope & Boundaries)_

No by default. It warns and names the potentially conflicting specs,
owners, branches, and touched paths. Blocking is reserved for future
project-specific policy on explicitly exclusive paths, because
parallel work often overlaps safely after human coordination.

### Q6: Do Spacecat/Mysticat conventions become federation requirements?
_(category: Scope & Boundaries)_

No. Spacecat/Mysticat is a scale fixture and source of concrete
adoption evidence. Its `mani.yaml` / `workspace.yaml` inventory, MCP
preference, split authority repos, and testing conventions are examples
of project-specific decisions. The product workflow is generic:
discover existing inventory and policies, make unresolved decisions
explicit, normalize the accepted shape into federation metadata, then
sync/audit against the chosen source of truth.

### Coverage summary

| Category | Status |
|---|---|
| Scope & Boundaries | Resolved |
| Acceptance Criteria Testability | Clear |
| Dependencies & Blockers | Resolved |
| Non-functional Requirements | Partial |
| Edge Cases & Failure Modes | Resolved |
| Terminology Consistency | Resolved |
