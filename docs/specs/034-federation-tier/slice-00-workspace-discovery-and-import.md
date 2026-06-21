---
status: DRAFT
dependencies: []
last_verified:
arch_review: true
---

## Slice 034-00 — discovery-and-import-framework

**Goal:** Ship a read-only federation discovery/adoption pass that makes
existing multi-repo teams immediately useful to jig without over-fitting
to one workspace shape: inventory their repo sources, host/auth routing,
authority repos, existing spec homes, contract surfaces, and validation
signals, then emit a reviewable adoption report plus a draft normalized
registry.

**DoR:**
- Spec 034 overview accepts existing repo-operating models as input
  substrates, not something federation replaces.
- At least two fixture shapes are available: a simple central/manual
  registry shape and one mature imported-inventory target for dogfooding
  (for example `mysticat-workspace` with `mani.yaml` and
  `workspace.yaml`).

**Acceptance Criteria:**

1. **`jig:repo-registry discover <inventory-root>` runs read-only.**
   The helper accepts a workspace repo root, central repo root, or
   explicit inventory-source config and never writes to member repos. It
   may write generated artifacts only under the current jig repo /
   federation central draft area.
2. **Inventory importers are selected explicitly.** Discovery exposes a
   small importer contract so project-specific sources can feed the same
   pipeline. v1 includes a manual/proposed-registry importer plus a
   workspace-manifest importer that reads `mani.yaml` when present (repo
   names, URLs, tags, local path hints) and `workspace.yaml` when present
   (host groups, SSH aliases, org-specific auth notes, secret/MCP routing
   hints). Missing optional files produce warnings, not fatal errors.
   Future importers such as Backstage/service catalog, Terraform/IaC,
   package workspace, and GitHub org/team discovery should not require a
   new federation workflow.
3. **Authority repos are detected and explicitly modeled.** The report
   identifies likely authority homes from `AGENTS.md`/`CLAUDE.md`,
   imports, manifest tags, service-catalog metadata, or explicit config.
   Built-in authority keys include `workspace_ops`, `architecture`,
   `guidelines`, `org_rfcs`, and `product_specs`; custom keys are allowed
   when a project has a different operating model. Ambiguous or missing
   authorities are marked `needs_decision`; nothing is guessed silently.
4. **Existing spec substrate is inventoried tolerantly.** For each repo,
   the helper records whether `docs/specs/`, `docs/decisions/`,
   `docs/plans/`, OpenAPI/AsyncAPI/proto/schema artifacts, and project
   `AGENTS.md`/`CLAUDE.md` exist. Non-jig or legacy shapes are reported
   as `external_spec_home` / `legacy_specs`, not treated as failures.
5. **Repo access provider plan is generated.** For each repo/host, the
   report proposes a provider (`mcp`, `gh`, `github-api`, `git-ssh`, or
   `local-worktree`) and explains unresolved auth gaps. It must preserve
   project-specific constraints such as "prefer MCP over `gh`", "use
   GitHub API tokens in CI", or SSH aliases instead of normalizing
   everything to `gh --hostname`.
6. **Contract-surface candidates are generated where cheap.** The helper
   surfaces likely npm packages, OpenAPI paths/files, event/queue naming
   hints, database migration/RPC files, and deploy-unit clues from
   manifests and well-known docs. Generated contract surfaces are marked
   `discovered`; hand-authored registry entries remain `declared`.
7. **Outputs are reviewable and deterministic.** The pass writes:
   - `docs/federation/adoption-report.md` with findings, warnings, and
     required human decisions.
   - `docs/federation/repos.proposed.yaml` as a draft normalized
     registry, including import provenance and unresolved fields.
   Re-running with the same input is stable.
8. **No federation behavior is activated by discovery alone.**
   Discovery does not install Tier 2 skills, change `.jig/scaffold.json`,
   open PRs, or modify `docs/repos.yaml`. Slice 034-01 consumes the
   accepted schema/provider decisions; slice 034-02 turns the proposal
   into registry operations.
9. **Portable fixture coverage.** Tests include at least one simple
   central/manual fixture and one Spacecat/Mysticat-style fixture with
   `mani.yaml`, `workspace.yaml`, split authority repos, GitHub + GHEC
   host hints, local `AGENTS.md`/`CLAUDE.md`, and at least one repo with
   legacy/non-jig specs. The Spacecat/Mysticat fixture proves realism; it
   is not the only accepted input shape.

**DoD:**
- [ ] All ACs pass; full test suite green.
- [ ] Implementer test coverage exercises manifest present, manifest
      absent, manual/proposed-registry import, split authorities,
      ambiguous authorities, legacy spec shapes, and provider-plan
      generation.
- [ ] Reviewed by `reviewer` subagent.
- [ ] Implementation review passed.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were deferred
      during implementation.

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated by `workflow.py status-board`.
- [ ] `docs/architecture.md` updated to show discovery/import as the
      first federation entry path for mature multi-repo installs.
- [ ] Dogfood evidence recorded from both a portable fixture and a real
      or fixture-backed Spacecat/Mysticat-style workspace.

### Deviation log (after reconciliation)
