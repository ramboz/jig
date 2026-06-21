---
status: Proposed
dependencies: [docs/specs/034-federation-tier/spec.md, docs/decisions/adr-0012-scaffold-tier-gated-install.md]
last_verified: 2026-06-21
frame_review: true
---

# ADR-0028: Federation composes with existing repo operating models and access providers

## Status

Proposed (2026-06-21)

## Context

Federation must compose with mature multi-repo operating models instead
of replacing them. The first concrete Tier 2 adopter shape is a
Spacecat/Mysticat-style org: 30+ repos, a workspace repo with
`mani.yaml` / `workspace.yaml`, split authority for architecture,
guidelines, org RFCs, and workspace operations, and multiple GitHub auth
routes. That org is the validation fixture for scale and realism, not
the normative product shape. Other adopters may organize around
Backstage/service catalogs, package workspaces, Terraform/IaC inventory,
GitHub org/team discovery, or a hand-maintained registry.

Spec 034 originally assumed one central repo and a `gh --hostname`
adapter as the v1 primitive. External review against the Spacecat repos,
followed by a portability pass, surfaced three adoption blockers:

- Existing repo inventory sources may already carry repo names, tags,
  host/auth hints, and local paths. A hand-maintained `docs/repos.yaml`
  can duplicate the source of truth unless provenance and sync are
  explicit.
- Repo access is a project policy. Some orgs may prefer MCP, some
  GitHub API tokens in CI, some SSH aliases, and some `gh`; `gh
  --hostname` is not a safe universal primitive.
- Cross-repo work is governed by contract and deploy-order surfaces
  (npm packages, OpenAPI, DB/RPCs, events, deploy units), not just file
  overlap.

The local-first/no-service shape of spec 034 still holds. The disputed
boundary is what federation treats as source input, how helpers read
repos, and which verification policy a project chooses.

## Options Considered

### Option A: Keep one central repo and `gh` as the v1 adapter

Simple to implement and enough for greenfield teams that do not already
have an existing inventory source. It fails mature adopter shapes when
it creates duplicate registry state and assumes an auth path the project
explicitly discourages.

### Option B: Replace existing repo-operating systems with jig federation

This would make jig the clone manager, MCP/secrets config surface,
workspace bootstrapper, service catalog, and local-dev harness. It is
too large and misplaced: teams often already have the right substrate
for those jobs.

### Option C: Compose with existing repo operating models and introduce repo access providers

Treat existing inventory sources as importable source input, normalize
them into jig's federation metadata, and read repos through a provider
boundary. Simple installs still use a single central repo; mature
installs can declare split authority repos, importer provenance,
provider-specific access, and optional verification policy.

## Recommended Decision

Adopt **Option C**.

Federation uses one portable workflow:

1. **Discover** existing inventory, authority, provider, contract, and
   verification signals through importer-specific adapters.
2. **Decide** project policy: source of truth, authority mapping, repo
   access provider, and optional verification requirements.
3. **Normalize** the accepted shape into jig federation metadata
   (`repos.yaml`, generated caches, optional verification profile).
4. **Sync/audit** normalized metadata against the chosen source of truth.

That workflow has two initial entry paths:

1. **Simple central.** A team without an existing inventory source can
   author `docs/repos.yaml` directly in one central repo.
2. **Inventory import.** A team with an existing repo source starts with
   a read-only discovery/import pass. v1 can include a
   workspace-manifest importer for `mani.yaml` / `workspace.yaml` plus a
   manual/proposed-registry importer; future service catalog, package
   workspace, Terraform/IaC, GitHub org/team, or hand-registry importers
   should plug into the same pipeline. The pass emits a reviewable
   adoption report and proposed federation metadata.

The normalized federation registry remains useful, but it is not always
the source of truth. It records import provenance and can be regenerated
or audited against the chosen source inventory.

Repo reads/writes go through a `RepoAccessProvider` boundary. Providers
include at least MCP, `gh`, GitHub API with token env, git-over-SSH, and
local worktree. Federation helpers never invoke `gh auth switch`, and
`gh --hostname` is only the implementation of one provider, not the
federation contract.

Authority can be split inside one federation. Built-in examples include
`workspace_ops`, `architecture`, `guidelines`, `org_rfcs`, and
`product_specs`, but projects may define other authority keys. This is
not multi-federation membership; it is one federation with multiple
read-only authority homes.

Verification remains project policy. `docs/federation/verification.yaml`
is optional and can be seeded from importer hints, but no testing
strategy is required merely because Spacecat/Mysticat uses one.

## Consequences

**Becomes easier:**

- Mature multi-repo orgs can adopt federation without re-entering every
  repo by hand or flattening existing workspace/service-catalog
  structures. Spacecat/Mysticat proves the fixture is realistic.
- Federation can respect MCP/SSH/token routing instead of assuming one
  global GitHub CLI identity.
- Cross-repo status, collision, and review guidance can reason about
  real contract surfaces, not only touched files.
- Simple users still get the one-central mental model.

**Becomes harder:**

- The registry schema needs provenance and provider fields.
- Discovery needs an importer boundary instead of one baked-in manifest
  parser.
- Tests need multiple realistic fixture shapes, not only tiny
  hand-authored `repos.yaml` examples or one Spacecat-shaped fixture.
- Helpers must report unsupported provider operations cleanly instead of
  shelling out to a universal `gh` fallback.
- Documentation must distinguish "central" from split authority repos so
  teams do not mistake inventory import for governance consolidation.

**Does not change:**

- Standalone projects install no Tier 2 skills.
- Federation stays local-first: no daemon, no hosted service, no live
  lock server.
- Collision radar remains advisory by default.

## Open questions

- Should true multi-federation membership be supported for shared
  libraries, or is split authority inside one federation enough until a
  second real user asks?
- Which provider operations are required for MVP versus optional
  (`open_pr`, branch creation, default-branch lookup, raw file read)?
- Which inventory importers ship in v1 beyond proposed YAML and the
  workspace-manifest example?
- Should `docs/federation/verification.yaml` graduate into core
  federation, or remain an optional project-policy profile?
