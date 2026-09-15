---
status: DRAFT
skill: scaffold-init
use_cases: []
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 113: GitHub Copilot CLI as a third committed host

> Implements [ADR-0061](../../decisions/adr-0061-copilot-third-host.md).
> Extends the dual-host model of
> [ADR-0018](../../decisions/adr-0018-dual-host-generated-plugin-artifacts.md)
> to a tri-host layout.

## Overview

Adobe disables Claude Code on **2026-09-28** and makes GitHub Copilot the
primary coding agent. To survive the cutover, jig must ship as a first-class
**GitHub Copilot CLI** host alongside Claude and Codex: a committed,
drift-guarded `hosts/copilot/` package rendered from the same canonical source,
installable via `/plugin`, with a host-explicit `jig-copilot-vX.Y.Z.zip`
release archive.

Per ADR-0061, Copilot CLI reads Claude-format `SKILL.md` skills, `CLAUDE.md`,
and `.mcp.json` directly and installs Claude-format plugins from marketplaces —
so much carries over — but jig-specific behavior breaks or degrades as-is:
skill-loader limits (names with `:`, descriptions >1024 chars), a *different*
hook model (14 camelCase events with differing payloads/response schemas),
agents rendered to `.github/agents/`, and permission syntax. This spec builds a
`CopilotScaffoldRenderer` that absorbs those differences in the **render layer**
(leaving Claude/Codex output untouched) and wires it into the existing host
build/drift/release pipeline.

**Scope:** GitHub Copilot **CLI** only (matching Adobe's guide and jig's
CLI-first nature). IDE-surface parity is out of scope. This spec covers **jig**;
servo and shaper adopt the same pattern via their own repos' specs (jig-first).

## Assumptions

<!-- Spec 064-02 / ADR-0020 — grounding-by-probe (risk-gated). -->

- **Copilot capability facts come from Adobe's internal migration guide +
  terminology map** (read 2026-09-15), reflecting Copilot CLI ~1.0.84 — not from
  a jig-run probe of Copilot itself. The guide warns behavior changes quickly.
  **Slice 113-01 (spike) re-verifies the load-bearing ones against a live
  `copilot` session + GitHub's own docs before the rendering slices commit to a
  shape.**
- **Skill-loader exposure — probed 2026-09-15** (see ADR-0061): 2 of 20 source
  skills exceed the 1024-char description limit (`memory-sync`,
  `vision-elicitation`); 0 source names contain `:`. Whether the `jig:`
  invocation namespace surfaces as a `:`-bearing loaded name under Copilot is
  **unverified** (spike 113-01).
- **The Copilot plugin/marketplace manifest shape** a committed `hosts/copilot/`
  package must present for `/plugin` is **unverified** (spike 113-01).

## Decomposition

This is host-adapter infrastructure, so "vertical" means **a Copilot user can
install and use progressively more of jig** — not "one layer at a time." The
split is primarily **Interface** (capability slices: install+skills → agents)
and **Rules** (hooks split simple→edge: advisory nudges → enforcing gates +
permissions), with **one Spike** for the genuinely-external Copilot-contract
unknowns ADR-0061 flagged, and a final packaging/release **parity** slice.

- **S (113-01)** — resolve the external unknowns (plugin manifest, agent file
  form, `/plugin` install of the Claude-format package, skill namespace/colon
  behavior). Spike is justified here because the unknowns are external to jig
  and gate the render shape; it is tightly time-boxed and nested in this spec.
- **I (113-02)** — walking skeleton: `CopilotScaffoldRenderer` +
  `renderer_for_host` wiring + a minimal committed `hosts/copilot/` rendering
  **skills + instructions** that load under Copilot (loader-compat invariant).
- **I (113-03)** — custom **agents** render to `.github/agents/` (model-neutral).
- **R (113-04)** — **advisory** hooks translated to Copilot events (the
  additionalContext nudges: git-freshness, boundary-warn, entry-gate).
- **R (113-05)** — **enforcing** hooks + **permissions** floor (the
  permission-decision gates: spec-gate, review-evidence, bug-closure), with the
  mapped-or-explicitly-unmappable inventory invariant.
- **Parity (113-06)** — commit the package under the single builder + drift
  guard + CI, the `jig-copilot-vX.Y.Z.zip` release archive + release-please
  coordination, and per-host install/smoke verification.

**Deadline-aware ordering.** 113-01→05 is the "actually works under Copilot"
core and lands first; 113-06 (drift/release automation) may land at or just
after 2026-09-28 without blocking a usable install.

**Anti-horizontal-phasing.** Every non-spike slice leaves a Copilot user able to
do something new end-to-end (install & run skills; use agents; get nudges; get
enforced gates; install from the marketplace with no build step). No slice
touches only an internal layer.

## Slices

- [113-01 — copilot-contract-spike](slice-01-copilot-contract-spike.md) — verify the external Copilot install/skill/hook/agent contract.
- [113-02 — renderer-and-skeleton](slice-02-renderer-and-skeleton.md) — `CopilotScaffoldRenderer` + minimal `hosts/copilot/` (skills + instructions load).
- [113-03 — agents](slice-03-agents.md) — render custom agents to `.github/agents/` (model-neutral).
- [113-04 — advisory-hooks](slice-04-advisory-hooks.md) — translate advisory/context hooks to Copilot events.
- [113-05 — enforcing-hooks-and-permissions](slice-05-enforcing-hooks-and-permissions.md) — translate enforcing hooks + permissions floor; mapped-or-unmappable inventory.
- [113-06 — committed-package-and-release](slice-06-committed-package-and-release.md) — drift guard + CI + release archive + per-host verification.
