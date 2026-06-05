---
dependencies: ["adr-0015-worktree-aware-reservation"]
last_verified: 2026-06-05
---

# ADR-0018: Dual-host generated plugin artifacts

## Status

Accepted (2026-06-05)

## Context

Spec 033 made Codex a supported host alongside Claude. Spec 059 closed the practical Codex parity gaps: Codex scaffold output, Codex plugin packaging, hook trust language, skill override wording, role-agent TOML rendering, install smoke tests, and a watch point for future plugin-native custom-agent discovery.

After that work, the runtime support story is strong, but the delivery architecture is lopsided:

- Claude release packaging still treats the repository root as the plugin install tree.
- Codex packaging already builds a generated marketplace root under `dist/codex-plugin/`.
- The release zip name `jig-vX.Y.Z.zip` reads as host-neutral even though the direct-zip install path is Claude-shaped.
- Codex does not currently document direct zip plugin installation; its documented local install path is a marketplace root added with `codex plugin marketplace add`.

That makes the source tree carry two jobs at once: canonical source and Claude install artifact. It also makes Codex look like the special case even though the generated-artifact pattern is cleaner for both hosts. The decision affects release packaging, install docs, scaffold helper paths, smoke validation, and how future host adapters should be added, so it belongs in an ADR.

## Decision Options Considered

### Option A: Keep Claude root-as-artifact and Codex generated dist

Leave `scripts/build_release_zip.py` building directly from the source root for Claude, and keep `scripts/build_codex_plugin.py` generating a Codex marketplace tree.

- **Pros:** Smallest change. Preserves the historical Claude release flow.
- **Cons:** Keeps one host privileged as "the real tree"; leaves source and install-artifact concerns mixed; keeps release naming ambiguous; makes future host support copy the asymmetry.

### Option B: Generate one artifact per host from canonical source

Treat the repository root as canonical source only. Generate `dist/claude-plugin/` and `dist/codex-plugin/` as disposable host artifacts. Release archives are built from those generated artifacts.

- **Pros:** Balanced architecture; one source of truth; clear source vs. output boundary; easier smoke validation; future hosts get the same pattern.
- **Cons:** Adds a Claude build step that did not exist before; release tooling and docs must stop assuming the source root is installable.

### Option C: Put the Codex marketplace directly under `.codex-plugin/`

Keep host folders next to each other in the source root by adding Codex's marketplace descriptor and plugin tree under `.codex-plugin/`, analogous to `.claude-plugin/marketplace.json`.

- **Pros:** Superficially symmetrical folder names at source root.
- **Cons:** Conflates a Codex plugin manifest directory with a Codex marketplace root. The marketplace root has a different shape (`.agents/plugins/marketplace.json` plus `plugins/jig/...`) and is a generated install container, not just source metadata. It would make the source root more artifact-shaped, not less.

### Option D: Move all host manifests into `manifests/<host>/`

Make the root even more source-pure by relocating `.claude-plugin` and `.codex-plugin` source manifests into a neutral `manifests/` hierarchy, then generate both host artifacts from there.

- **Pros:** Maximum source/artifact separation.
- **Cons:** Broad churn across release-please, version derivation, validators, docs, and tests before it provides additional user value. It can remain a future cleanup if root source manifests stay confusing after the generated artifact boundary lands.

## Recommended Decision

Adopt **Option B: generate one artifact per host from canonical source**.

The repository root remains the source of truth for skills, agents, hooks, templates, tests, docs, and host manifest source files. It is not the install artifact for either host. Build output is disposable and lives under `dist/`:

```text
dist/
  claude-plugin/
  codex-plugin/
```

`dist/claude-plugin/` is the Claude plugin artifact. It contains the Claude manifest, shared runtime assets, and Claude-shaped skill prose. Claude release archives are built from this artifact and named `jig-claude-vX.Y.Z.zip`.

`dist/codex-plugin/` is the Codex marketplace root. It contains `.agents/plugins/marketplace.json` plus the nested plugin at `plugins/jig/.codex-plugin/plugin.json`. Codex release archives are built from this marketplace root and named `jig-codex-vX.Y.Z.zip`. Because Codex does not currently document direct zip plugin installation, the Codex zip is documented as an extract-then-add marketplace bundle:

```text
codex plugin marketplace add <extracted-jig-codex-dir>
codex plugin add jig@jig
```

Scaffold examples and maintainer docs should point at the generated host artifact paths, not the source root:

- Claude: `dist/claude-plugin/skills/scaffold-init/scaffold.py`
- Codex: `dist/codex-plugin/plugins/jig/skills/scaffold-init/scaffold.py`

Release and verification must be host-explicit. A successful Codex build or install probe is not proof that Claude installs correctly, and a successful Claude probe is not proof that Codex installs correctly. The implementing spec therefore includes one final verification slice per host.

Do not move source manifests into `manifests/` as part of this decision. That can be reconsidered later if the source-manifest location continues to confuse the source/artifact boundary after `dist/` becomes the documented install surface.

## Consequences

**Becomes easier:**
- Users see host-specific install artifacts and release assets instead of guessing whether `jig-vX.Y.Z.zip` applies to their host.
- Release tests can validate exactly the artifact a user installs.
- Codex documentation can stay honest about marketplace installation and avoid implying unsupported direct zip install behavior.
- Future host adapters have a clear pattern: canonical source in root, generated host artifact under `dist/<host>-plugin/`.

**Becomes harder:**
- Claude gains an explicit build artifact and must stop relying on the source root as its plugin tree.
- Release workflows must build and upload multiple archives.
- Backward compatibility for the old `jig-vX.Y.Z.zip` name needs a deliberate transition choice, not accidental continuation.
- Smoke tests need to run per host, which adds time and surface area.

**Invariants:**
- `dist/` is generated output and is not checked in.
- Host source manifests may remain in the root for now, but generated artifacts are the documented install surface.
- Codex's explicit custom-agent install helper remains required until official Codex plugin-native custom-agent discovery exists.
- Each host gets a concrete install/build verification path in its own environment or the closest deterministic substitute when that host surface is unavailable.
