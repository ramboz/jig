---
dependencies: ["adr-0015-worktree-aware-reservation"]
last_verified: 2026-06-05
---

# ADR-0018: Dual-host generated plugin artifacts

## Status

Accepted (2026-06-05)

> **Revision note (2026-06-05).** This ADR was first drafted selecting
> *generated, uncommitted* `dist/<host>-plugin/` artifacts (former Option B).
> Before any implementation landed, the decision was revised to **committed,
> source-derived per-host packages under `hosts/<host>/`** so that the
> canonical remote install path — `marketplace add <repo>` with **no local
> build step** — works symmetrically for both hosts. The uncommitted variant
> is retained below as a rejected alternative (now Option B). No code shipped
> against the original selection, so the record is corrected in place rather
> than superseded.

## Context

Spec 033 made Codex a supported host alongside Claude. Spec 059 closed the
practical Codex parity gaps: Codex scaffold output, Codex plugin packaging,
hook trust language, skill override wording, role-agent TOML rendering,
install smoke tests, and a watch point for future plugin-native custom-agent
discovery.

After that work the runtime support story is strong, but the *delivery*
architecture is lopsided and, in one place, actively wrong:

- Claude release/install treats the **repository root** as the plugin tree.
  The root `.claude-plugin/marketplace.json` points its plugin `source` at
  `git-subdir` `path: "."` — so `claude /plugin marketplace add ramboz/jig`
  installs the **entire repository**, including `scripts/`, `docs/`,
  `.github/`, tests, and fixtures, as the plugin. That is not a clean runtime
  payload.
- Codex packaging already builds a generated marketplace root under
  `dist/codex-plugin/`, so Codex looks like the special case even though its
  generated shape is the cleaner one.
- The release zip name `jig-vX.Y.Z.zip` reads as host-neutral even though the
  direct-zip install path is Claude-shaped.
- Codex does not document direct zip plugin installation; its documented local
  install path is a marketplace root added with `codex plugin marketplace add`.

The target the maintainers want is a **symmetric three-peer layout**: a
host-neutral canonical source at the root, a Claude package, and a parallel
Codex package — each installable the native way for its host, including the
**remote one-command install** (`marketplace add <repo>` with no clone-and-build
step). For Claude that one-liner requires the install payload to be present in
the git repo, because the host clones the repo and reads its manifest; it
cannot read a gitignored `dist/`. That requirement is what rules out the
originally-drafted uncommitted-`dist/` shape.

The decision affects release packaging, install docs, scaffold helper paths,
smoke validation, the remote-install contract, and how future host adapters are
added, so it belongs in an ADR.

## Decision options considered

### Option A: Keep Claude root-as-artifact and Codex generated dist

Leave `scripts/build_release_zip.py` building directly from the source root for
Claude, and keep `scripts/build_codex_plugin.py` generating a Codex marketplace
tree under `dist/`.

- **Pros:** Smallest change. Preserves the historical Claude release flow.
- **Cons:** Keeps one host privileged as "the real tree"; mixes source and
  install-artifact concerns; keeps release naming ambiguous; **ships the whole
  repo** (scripts/docs/tests) as the Claude plugin; makes future host support
  copy the asymmetry.

### Option B: Generate one artifact per host into an uncommitted `dist/`

Treat the repository root as canonical source only. Generate
`dist/claude-plugin/` and `dist/codex-plugin/` as disposable, **gitignored**
host artifacts. Release archives are built from those generated artifacts.

- **Pros:** Clean source/output boundary; nothing generated lives in git; no
  drift risk.
- **Cons:** **Breaks the canonical remote install.** `marketplace add ramboz/jig`
  cannot read a gitignored `dist/` from a fresh clone, so the easy one-command
  install would no longer work for either host — users would have to clone and
  build first, or fall back to the release zip. This is the option the ADR was
  first drafted around; the remote-install requirement reverses it.

### Option C: Put the Codex marketplace directly under `.codex-plugin/`

Add Codex's marketplace descriptor and plugin tree under `.codex-plugin/`,
analogous to `.claude-plugin/marketplace.json`.

- **Pros:** Superficially symmetrical folder names at source root.
- **Cons:** Conflates a Codex plugin manifest directory with a Codex
  marketplace root (different shape: `.agents/plugins/marketplace.json` plus
  `plugins/jig/...`). It makes the source root *more* artifact-shaped, not less.

### Option D: Move all host manifests into `manifests/<host>/`

Relocate `.claude-plugin` and `.codex-plugin` source manifests into a neutral
`manifests/` hierarchy and generate both host artifacts from there.

- **Pros:** Maximum source/artifact separation at the manifest level.
- **Cons:** Broad churn across release-please, version derivation, validators,
  docs, and tests for little additional user value. Deferred; can be revisited
  if the root source-manifest location stays confusing after this lands.

### Option E (chosen): Committed, source-derived per-host packages

Keep the repository root as canonical source, and commit one **built** package
per host under `hosts/<host>/`. The root keeps only the thin host *marketplace
pointer(s)* needed for remote install; each committed package is the clean,
runtime-only install payload for its host.

- **Pros:** Symmetric three-peer layout; remote one-command install works for
  both hosts with no build step; the Claude payload is finally runtime-only
  (no more shipping `scripts/`/`docs/`/tests); release zips are just the
  committed packages zipped; future hosts follow one pattern.
- **Cons:** Built content lives in git, so source↔package duplication must be
  fenced by a **drift guard** (CI regenerates both packages and fails on a
  dirty `git diff`); automated version bumps must regenerate the committed
  packages in the same change (coordination with Spec 013 / release-please).

## Decision

Adopt **Option E: committed, source-derived per-host packages**.

The repository root remains the source of truth for skills, agents, hooks,
templates, tests, docs, and the host *source* manifests. Each host's installable
payload is a **committed, generated** package built from that source:

```text
repo root/                       canonical source + dev tooling
  skills/ agents/ hooks/ templates/      canonical source (Claude-reference shape)
  scripts/ docs/ .github/                dev-only — never shipped to either host
  .claude-plugin/
    marketplace.json             remote-install pointer; plugin source -> ./hosts/claude
    plugin.json                  Claude source manifest (version source of truth)
  .codex-plugin/plugin.json      Codex source manifest
  hosts/
    claude/                      COMMITTED Claude plugin package (built from source)
      .claude-plugin/plugin.json
      skills/ agents/ hooks/ templates/  (runtime-only subset) + README + LICENSE
    codex/                       COMMITTED Codex marketplace package (built from source)
      .agents/plugins/marketplace.json
      plugins/jig/.codex-plugin/plugin.json + rendered skills / agent TOMLs / hooks
  dist/                          generated, gitignored — release ZIPS ONLY
    jig-claude-vX.Y.Z.zip
    jig-codex-vX.Y.Z.zip
```

**Canonical source stays Claude-reference-shaped.** The Claude package is a
*filtered copy* of the runtime subset (the same include/exclude logic the
release-zip builder already encodes); the Codex package is the *rendered*
derivation (`build_codex_plugin.py`'s existing host rewrite). Making the root
source fully host-token-neutral so both hosts are equally "rendered" is **not**
adopted here — it is a large prose migration for little payoff while Claude is
the reference shape. It can be revisited later (relates to Option D).

**Install surfaces by host:**

- Claude, remote: `claude /plugin marketplace add ramboz/jig` → the root
  `.claude-plugin/marketplace.json` resolves the plugin to `./hosts/claude`.
- Claude, zip: `jig-claude-vX.Y.Z.zip` is `hosts/claude/` zipped flat at root
  (`.claude-plugin/plugin.json` at the zip root), directly drag-droppable into
  Claude Desktop / loadable via `--plugin-dir`.
- Codex, local/remote: `codex plugin marketplace add <hosts/codex>` then
  `codex plugin add jig@jig`. Codex has no direct zip-drop, so
  `jig-codex-vX.Y.Z.zip` is documented as an **extract-then-add** marketplace
  bundle:

  ```text
  unzip jig-codex-vX.Y.Z.zip -d <dir>
  codex plugin marketplace add <dir>
  codex plugin add jig@jig
  ```

**Drift guard.** Because the packages are both generated *and* committed, a
single builder regenerates `hosts/claude` and `hosts/codex` from source, and CI
runs it and fails on a dirty `git diff`. Contributors regenerate after touching
any source that feeds a package. This is defense-in-depth like ADR-0011 /
ADR-0013: the guard catches staleness, it does not replace review.

**Version source coordination.** Release-please bumps the source manifest(s);
the same release change must regenerate the committed packages so their pinned
versions match. The exact version-source location and the regenerate step are
coordinated with Spec 013's release-please config.

**Host-explicit release and verification.** A successful Codex build or probe is
not proof that Claude installs correctly, and vice versa. The implementing spec
includes one final verification slice per host, each run in that host's own
environment (or the closest deterministic substitute, recorded honestly).

`manifests/<host>/` relocation (Option D) is explicitly **not** part of this
decision.

## Consequences

**Becomes easier:**
- Both hosts get a clean, runtime-only, remotely-installable package and a
  host-named release zip; users no longer guess whether `jig-vX.Y.Z.zip`
  applies to their host, and the Claude plugin stops shipping `scripts/`,
  `docs/`, and tests.
- Release tests validate exactly the artifact a user installs.
- Codex docs stay honest about marketplace (extract-then-add) installation.
- Future host adapters follow one pattern: canonical source in root, committed
  `hosts/<host>/` package, host-named zip.

**Becomes harder:**
- Generated content lives in git, so a **drift guard** is mandatory and
  contributors must regenerate packages after source edits.
- Automated version bumps must regenerate the committed packages in the same
  change (release-please coordination).
- Release workflows must build and upload multiple archives; smoke tests run
  per host, adding surface area.
- The root carries a thin host marketplace pointer plus a built `hosts/<host>/`
  copy of much of the runtime, i.e. deliberate, drift-guarded duplication.

**Invariants:**
- The repository root is canonical source; `hosts/<host>/` packages are
  generated build outputs that happen to be committed and are kept in sync by
  the drift guard.
- `dist/` is generated output, **not** checked in, and holds release zips only.
- The root host marketplace pointer resolves the plugin payload to the
  committed `hosts/<host>/` package — never to the repo root and never to a
  gitignored path.
- Codex's explicit custom-agent install helper remains required until official
  Codex plugin-native custom-agent discovery exists.
- Each host gets a concrete install/build verification path in its own
  environment, or the closest deterministic substitute when that host surface
  is unavailable.
