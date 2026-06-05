---
status: IN_PROGRESS
skill: release-pipeline, scaffold-init
tier: host-adapter
adr_required: true
adr: ../../decisions/adr-0018-dual-host-generated-plugin-artifacts.md
---

# Spec 061: Dual-host plugin packages

## Overview

Spec 033 made Codex a supported host and Spec 059 polished the Codex
runtime contract. The remaining imbalance is **delivery shape**, and in
one place it is actively wrong:

- Claude installs from the **repository root**: the root
  `.claude-plugin/marketplace.json` points its plugin `source` at
  `git-subdir` `path: "."`, so `claude /plugin marketplace add ramboz/jig`
  ships the **whole repo** — `scripts/`, `docs/`, `.github/`, tests — as
  the plugin.
- Codex already builds a clean generated marketplace tree under
  `dist/codex-plugin/`, so Codex looks like the special case even though
  its shape is the cleaner one.
- The release zip `jig-vX.Y.Z.zip` reads as host-neutral but is
  Claude-shaped.

The target is a **symmetric three-peer layout**: a canonical source root,
a Claude package, and a parallel Codex package — each installable the
native way for its host, **including the remote one-command install**
(`marketplace add <repo>` with no clone-and-build step). Per
[ADR-0018](../../decisions/adr-0018-dual-host-generated-plugin-artifacts.md),
that one-liner requires the install payload to live in git, so the host
packages are **committed, source-derived** build outputs — not a
gitignored `dist/`:

```text
repo root/                       canonical source + dev tooling
  skills/ agents/ hooks/ templates/      canonical source
  .claude-plugin/marketplace.json        remote-install pointer -> ./hosts/claude
  .claude-plugin/plugin.json             Claude source manifest
  .codex-plugin/plugin.json              Codex source manifest
  hosts/
    claude/   COMMITTED Claude plugin package      (built from source)
    codex/    COMMITTED Codex marketplace package   (built from source)
  dist/       generated, gitignored — release ZIPS ONLY
```

Because the packages are both generated *and* committed, a **drift
guard** (CI regenerate-and-diff) is the linchpin that keeps them honest.

The architectural decision — including why the originally-drafted
uncommitted-`dist/` shape (Option B) was reversed — is recorded in
[ADR-0018](../../decisions/adr-0018-dual-host-generated-plugin-artifacts.md).

## Goals

1. **Commit one runtime-only package per host.** Build
   `hosts/claude/` and `hosts/codex/` from canonical source; the Claude
   package stops shipping `scripts/`/`docs/`/tests.
2. **Make remote one-command install work for both hosts.** Repoint the
   root Claude marketplace pointer at `hosts/claude`; keep Codex's
   `marketplace add` flow against `hosts/codex`.
3. **Guard committed packages against drift.** A single builder
   regenerates both packages; CI fails on a dirty `git diff`.
4. **Ship host-explicit release zips.** `jig-claude-vX.Y.Z.zip` (flat,
   drag-droppable) and `jig-codex-vX.Y.Z.zip` (extract-then-add
   marketplace bundle), both built from the committed packages.
5. **Point docs and scaffold examples at the host packages.** Install,
   scaffold, and release docs reference `hosts/claude/...` and
   `hosts/codex/plugins/jig/...` — never the repo root by accident.
6. **Verify each host in its own environment.** Claude and Codex each get
   a dedicated final verification slice so a spec authored in one host
   does not stand in for proof the other host installs and runs.
7. **Preserve honest Codex delivery semantics.** Codex has no direct
   zip-drop; its zip is an extract-then-add marketplace bundle.

## Non-goals

- **No direct Codex zip install claim.** Codex does not document direct
  zip plugin installation. This spec must not imply otherwise.
- **No plugin-native Codex agent discovery.** Spec 059-06 confirmed the
  explicit `--install-codex-agents` helper remains the supported
  contract.
- **No host-token-neutral source migration.** Canonical source stays
  Claude-reference-shaped; the Claude package is a filtered copy, the
  Codex package the rendered derivation. Making the root fully
  host-neutral (both hosts rendered) is deferred (ADR-0018 / Option D).
- **No `manifests/<host>/` relocation.** Root keeps the host source
  manifests plus the thin marketplace pointer (ADR-0018 / Option D
  deferred).
- **No change to scaffolded project contents.** The host packages are
  install sources; scaffold output stays host-shaped exactly as Specs 033
  and 059 define it.
- **`dist/` holds release zips only** and stays gitignored.

## Current state verified 2026-06-05

- `.claude-plugin/marketplace.json` resolves the `jig` plugin via
  `source: git-subdir`, `path: "."` — i.e. the repo root *is* the Claude
  plugin tree today.
- `scripts/build_release_zip.py` creates `jig-vX.Y.Z.zip` directly from
  the source root, including both `.claude-plugin/` and `.codex-plugin/`
  plus shared runtime folders. `_INCLUDE_ROOTS` already encodes the
  runtime subset the Claude package needs.
- `.github/workflows/release.yml` uploads only `dist/jig-vX.Y.Z.zip`.
- `scripts/build_codex_plugin.py` materializes
  `dist/codex-plugin/plugins/jig/` and the marketplace descriptor at
  `dist/codex-plugin/.agents/plugins/marketplace.json`, with safe-output
  guards (`_validate_output_dir`) and the host rewrite
  (`render_codex_plugin_skill_body`, `_render_codex_agent_templates`).
- `scripts/install_contract.py` is the shared plugin/release contract;
  `scripts/codex_install_smoke.py` validates the Codex package + probes a
  live Codex CLI when present.
- `skills/scaffold-init/scaffold.py` already has a `ClaudeScaffoldRenderer`
  base class, so a Claude package builder is mostly a filtered copy.
- No committed `hosts/` packages exist yet; README documents
  `codex plugin marketplace add dist/codex-plugin` and a host-neutral
  `jig-vX.Y.Z.zip`.

## Decomposition

**Suggested SPIDR axis: Interface.** Each slice stabilizes one external
interface: the committed Claude package + remote-install pointer, the
committed Codex package, the drift guard, host-named release zips,
symmetric docs, and host-specific install verification.

## Slices

- [061-01 - committed Claude package + repoint marketplace](slice-01-claude-committed-package.md)
- [061-02 - committed Codex package peer](slice-02-codex-committed-package.md)
- [061-03 - host-package drift guard](slice-03-package-drift-guard.md)
- [061-04 - host-explicit release zips](slice-04-host-explicit-release-zips.md)
- [061-05 - symmetric install + scaffold docs](slice-05-symmetric-install-docs.md)
- [061-06 - Claude install verification](slice-06-claude-install-verification.md)
- [061-07 - Codex install verification](slice-07-codex-install-verification.md)

## Dependencies / coordination

- Implements [ADR-0018](../../decisions/adr-0018-dual-host-generated-plugin-artifacts.md).
- Coordinate with [Spec 013](../013-release-pipeline/spec.md): it owns
  release zip creation and GitHub release upload, and its release-please
  config must regenerate the committed packages when it bumps the version
  manifests.
- Coordinate with [Spec 033](../033-host-adapter-portability/spec.md): it
  introduced the Codex build artifact and host renderer boundary the
  Codex package reuses.
- Coordinate with [Spec 047](../047-install-contract-verification/spec.md)
  so `install_contract.py` checks the committed `hosts/claude` package
  (which carries `.claude-plugin/plugin.json` only, not the root
  marketplace.json or `.codex-plugin/`).
- Coordinate with [Spec 059](../059-codex-port-polish/spec.md) so Codex
  docs keep the hook trust and explicit agent-install caveats.

## References

- [scripts/build_release_zip.py](../../../scripts/build_release_zip.py)
- [scripts/build_codex_plugin.py](../../../scripts/build_codex_plugin.py)
- [scripts/install_contract.py](../../../scripts/install_contract.py)
- [scripts/codex_install_smoke.py](../../../scripts/codex_install_smoke.py)
- [skills/scaffold-init/scaffold.py](../../../skills/scaffold-init/scaffold.py)
- [.claude-plugin/marketplace.json](../../../.claude-plugin/marketplace.json)
- [.github/workflows/release.yml](../../../.github/workflows/release.yml)
- [README.md](../../../README.md)
- [ADR-0018: Dual-host generated plugin artifacts](../../decisions/adr-0018-dual-host-generated-plugin-artifacts.md)
