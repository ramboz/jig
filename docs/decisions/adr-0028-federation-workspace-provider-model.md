---
status: Accepted
dependencies: [docs/specs/034-federation-tier/spec.md, docs/decisions/adr-0012-scaffold-tier-gated-install.md, docs/decisions/adr-0033-configurable-docs-root.md]
last_verified: 2026-07-08
frame_review: true
---

# ADR-0028: Federation supports two topologies (hub-and-referenced first) and composes with existing repo operating models

## Status

Accepted (2026-07-08)

_Revised 2026-07-08 to add the two-topology model (hub-and-referenced first,
peer-members deferred)._

## Context

Federation must compose with mature multi-repo operating models instead
of replacing them, and it must not assume every participating repo is a
scaffolded jig citizen. Two real multi-repo shapes now inform the design,
and they differ in **where jig state lives** — the load-bearing axis:

- **Hub-and-referenced (centralized jig state).** One *hub* repo holds
  all jig coordination artifacts — tracks, specs, ADRs, glossary, the
  routing primer — organized as multiple **tracks** (per-track
  subprojects via [ADR-0033](adr-0033-configurable-docs-root.md) /
  spec 084 `layout.docs_root="."`). The other repos are **referenced
  work targets** listed in a `repos.yaml` manifest (with `scope:` tags
  binding repos to tracks) and checked out on demand; they carry **no
  jig state**. Grounded in a running project (`personalization-workspace`:
  one hub repo, ~8 referenced repos across two GitHub hosts, three
  tracks). This is genuinely multi-repo and multi-host, but there is
  nothing distributed to keep coherent — one source of truth.

- **Peer-members-and-central (distributed jig state).** Every repo is a
  scaffolded jig *member*; a *central* repo coordinates them via a
  membership registry, cross-repo specs, read-through authority, and
  pull-based drift. The Spacecat/Mysticat shape (30+ repos, split
  authority, multiple auth routes). This is the original spec 034 model.
  It has a *named* signal (a 35+ repo org asked) but has **not** converted
  to implementation — spec 034 is all-DRAFT, zero slices started.

Spec 034 originally assumed the peer-members topology was the *only*
federation shape, entered via a "simple central." External review against
the Spacecat repos plus a portability pass had already surfaced three
adoption blockers (duplicate registry state vs. existing inventory;
repo access is project policy, not universally `gh --hostname`; cross-repo
work is governed by contract/deploy surfaces, not just file overlap).
The hub exemplar surfaces a fourth: **most participating repos are not
jig citizens at all**, so the roles / membership / drift machinery that
dominates spec 034 is not needed to federate them — it exists only to
keep *distributed* jig state coherent.

The local-first / no-service shape of spec 034 still holds. The disputed
boundaries are (1) which topology federation supports *first*, and (2)
what federation treats as source input, how helpers read repos, and which
verification policy a project chooses.

## Options Considered

Two orthogonal decisions: the **topology axis** (what shape ships first)
and the **composition axis** (how federation relates to existing
systems). The composition axis was settled by the original 0028; the
topology axis is the new decision.

### Topology axis

**T1 — Peer-members first (original 034).** Ship the distributed model
(roles, registry, cross-repo-spec, drift) as the entry point. Rejected as
*first*: it is a 16-slice tier serving a consumer that has not started
building, while it cannot express the hub shape at all (the hub has no
members to register). Over-built for the common case.

**T2 — Hub-and-referenced first (chosen).** Ship the centralized-hub model
first: multi-track org (already on 084) + a thin reference/access layer
(`repos.yaml` reference manifest, `scope:`→track binding, multi-host repo
checkout, workspace-level status across tracks). Defer the peer-members
machinery until a real distributed consumer builds. Grounded in a running
exemplar; most of it is convention plus one new access layer.

**T3 — Ship both together.** Rejected: doubles scope and couples a
buildable-now, demand-real tier to a deferred, unproven one. Violates
jig's defer-until-trigger bar.

### Composition axis (unchanged from the original 0028)

- **Option A: one central repo + `gh` as the v1 adapter.** Enough for
  greenfield teams with no existing inventory; fails mature adopters by
  duplicating registry state and assuming a discouraged auth path.
- **Option B: replace existing repo-operating systems.** Makes jig the
  clone manager, secrets surface, workspace bootstrapper, service catalog,
  and local-dev harness. Too large and misplaced.
- **Option C: compose + repo access providers (chosen).** Treat existing
  inventory as importable source input, normalize into jig metadata, and
  read repos through a provider boundary. Simple installs author
  `repos.yaml` directly; mature installs import + reconcile.

## Recommended Decision

Adopt **T2 (hub-and-referenced first)** on top of **Option C (compose +
providers)**.

**Two supported topologies, hub-first:**

1. **Hub-and-referenced — the first-supported tier.** All jig state lives
   in one hub repo, organized as tracks (084). A `repos.yaml` *reference*
   manifest lists work repos with host + `scope:`→track binding; a repo
   access provider checks them out on demand. No roles, no membership
   registry, no per-member drift, no cross-repo spec pinning, no
   read-through authority — there is only one jig citizen. It **does** still
   coordinate work *across* the referenced repos — cross-repo touchset +
   collision radar computed **locally** in the hub (no network, per A4) —
   and it **must close** ADR-0033's deferred multi-jig-per-repo /
   subtree-git-anchoring / migrate-into-subtree gaps (the per-track
   reserve/land "category mismatch" is the open risk). Grounded in
   `personalization-workspace`.
2. **Peer-members-and-central — the escalation tier (deferred).** The
   original 034 distributed model, re-scoped as escalation for orgs that
   genuinely need distributed jig state across many scaffolded members.
   Stays DRAFT/deferred until a real distributed consumer starts building.

**Retained from the original decision (apply to both topologies):**

- One portable workflow: **discover → decide → normalize → sync/audit**,
  via importer-specific adapters. Two entry paths: author `repos.yaml`
  directly, or import an existing inventory source (workspace manifest /
  service catalog / package workspace / GitHub org/team / hand registry).
- Repo reads/writes go through a `RepoAccessProvider` boundary (MCP, `gh`,
  GitHub API + token env, git-over-SSH, local worktree). Helpers never
  invoke `gh auth switch`; `gh --hostname` is one provider, not the
  contract. In the hub tier the provider is used for **checkout of
  referenced work repos**, not for coordinating distributed jig state.
- Verification stays project policy (`docs/federation/verification.yaml`
  optional; per-track in the hub tier, per-repo in the peer tier).

The normalized registry/manifest is useful but not always the source of
truth; it records import provenance and can be regenerated or audited.

## Assumptions

- **A1 — The hub topology is real and demanded now.** Grounded:
  `personalization-workspace` is a running project (one hub repo, ~8
  referenced work repos across `git.corp.adobe.com` + `github.com`, three
  tracks) actively migrating its flat `docs/` into `tracks/`. Not a
  hypothetical fixture.
- **A2 — Spec 084 / ADR-0033 delivers layout-aware artifact *paths*, but the
  multi-track hub has named 084 *dependencies*, not a finished foundation.**
  `layout.docs_root="."` (DONE) makes a *single* subproject's artifact paths
  layout-aware. But ADR-0033 **explicitly defers** the three things a
  multi-*track* hub needs (adr-0033 § "scoped OUT"): **multi-jig-per-repo
  coordination** (N subprojects sharing one branch / status-board
  namespace), **subtree-aware git anchoring** (per-track reserve/land against
  a shared `main` — push-mode is *refused* today and flagged as possibly a
  *"category mismatch, not merely unbuilt"*), and **migrate-into-subtree**.
  So the hub tier must *close* those gaps — it is a real spec with real risk,
  not "084 + conventions." The per-track reserve/land "category mismatch" is
  the hub tier's biggest open unknown.
- **A3 — Hub-first does not starve a building peer consumer.** Spec 034 is
  all-DRAFT with zero slices started; the named 35+ repo signal has not
  converted to implementation, so deferring the peer tier delays nothing
  in flight.
- **A4 — Centralizing jig state kills *state-coherence* machinery, but NOT
  *cross-repo work coordination*.** The boundary is the *state-coherence*
  axis, not "where state lives." Because all jig state is in one repo,
  **membership, per-member drift, read-through authority, and cross-repo
  spec pinning** have nothing to sync — genuinely peer-only. **But the hub
  still coordinates work across its ~8 referenced repos**, so **cross-repo
  touchset + collision** (034-12/13) stay a hub-tier need at v1 — computed
  *locally* from the hub's own specs + manifest over referenced-repo paths
  (`repo:path` strings), with no network and no distributed state. That is
  lighter than the peer tier's distributed impact hooks (034-11/14) but it
  is cross-*repo*, not cross-*track*: two specs in different tracks routinely
  touch the same shared referenced repo (e.g. `personalization`, which the
  exemplar's `repos.yaml` tags `scope: [rtb, offer-management]`), so a
  track-only collision radar would under-build. This split
  — **state-coherence peer-only, work-coordination hub-local** — is the
  load-bearing correction, and the claim most worth attacking.

## Kill criteria

- A real peer-members consumer starts *building* before the hub tier
  ships → revisit ordering (peer may need to be concurrent, not deferred).
- A hub-tier user needs genuine distributed-state *sync* — per-track drift
  across separate branches, or specs that must physically live in the work
  repos → the state-coherence boundary (A4) is leakier than claimed, and the
  hub/peer split must be reconsidered rather than treated as clean. (Note:
  cross-repo *collision/touchset* is already hub-local per A4, so it does
  **not** trip this criterion — only distributed state *sync* does.)
- ADR-0033's subtree git-anchoring "category mismatch" (per-track reserve/
  land against a shared `main`) proves unresolvable → the hub tier is
  blocked at its foundation and multi-track must fall back to
  per-track-branch or one-track-per-repo. (This displaces the earlier
  "maybe it's only a recipe" concern — the named 084 gaps make the hub tier
  real code, not a recipe.)

## Consequences

**Becomes easier:**

- Teams with several repos can adopt jig-driven federation **without
  scaffolding jig into every repo** — one hub, referenced work targets.
- Federation ships a buildable-now, demand-real tier grounded in a running
  project instead of blocking on an unstarted 16-slice distributed tier.
- Multi-host access is respected (MCP / SSH / token / `gh`) instead of
  assuming one global GitHub identity.
- Simple users get an even simpler mental model than "central + members":
  a hub plus a list of repos it points at.

**Becomes harder:**

- Two topologies must be documented distinctly so teams do not reach for
  peer-members machinery when the hub shape suffices (and vice versa).
- The reference manifest + `scope:`→track binding + multi-host checkout is
  new code, not just convention.
- **The hub tier must close ADR-0033's explicitly-deferred gaps** —
  multi-jig-per-repo coordination, subtree-aware git anchoring (per-track
  reserve/land), and migrate-into-subtree — the first flagged by ADR-0033 as
  possibly a *category mismatch*. This is the hub tier's real risk surface,
  not "084 + conventions."
- Collision radar in the hub must reason over referenced-repo paths
  (`repo:path`), not just tracks — a hub-local *subset* of cross-repo
  awareness, computed without the peer tier's network / distributed hooks.
- The provider boundary must cleanly separate "checkout a referenced repo"
  (hub) from "coordinate a member's jig state" (peer).

**Does not change:**

- Standalone projects install no Tier 2 skills.
- Federation stays local-first: no daemon, no hosted service, no live
  lock server.
- Collision radar remains advisory by default (cross-track in the hub
  tier; cross-repo in the peer tier).

## Open questions

- Is the hub tier genuinely a spec (new reference/access code) or just a
  documented recipe over 084 + a small status aggregator? (First kill
  criterion; decide during hub-tier slicing.)
- Which `RepoAccessProvider` operations are MVP for the *hub* tier
  (checkout / raw file read / default-branch lookup) versus peer-only
  (open_pr, branch creation)?
- Should true multi-federation membership be supported for shared
  libraries, or is `scope:`-tagging inside one hub enough until a second
  real user asks? (Tracked in refinement-todo.)
- Which inventory importers ship first for the hub tier beyond a
  proposed-YAML and a workspace-manifest example?
- **Hub-local collision has a coverage floor:** it sees only cross-repo
  work routed *through hub touchsets*. A branch pushed directly to a shared
  referenced repo outside hub coordination is invisible to the radar (a gap
  the peer tier's per-repo state wouldn't have). At hub-tier slicing (034-13),
  confirm the exemplar funnels cross-repo work through hub specs, and
  document the direct-push blind spot so the advisory scope isn't oversold.
