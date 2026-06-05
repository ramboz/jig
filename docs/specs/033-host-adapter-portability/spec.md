---
status: IN_PROGRESS
---

# Spec 033: Host adapter portability

## Overview

Jig started as a Claude Code plugin, then recovered its original
"own the scaffolding" framing by copying skills, agents, hooks, and
helpers into a project's `.claude/` directory. The next portability
step is to separate jig's workflow model from any one host's wiring.

This spec introduces a host-adapter architecture: jig keeps one
canonical source tree, but scaffolds materialized, host-native files for
each supported LLM harness. The initial v1 work preserved Claude plugin
mode and Claude scaffold mode; after the Codex trigger fired, slice
033-05 added Codex scaffold mode. Slice 033-06 adds Codex plugin
packaging through a generated Codex-native plugin package, and slice
033-07 added the Codex TOML custom-agent adapter.

The guiding rule is: **copy prose, share code**. Skills, primers, and
agent instructions are rendered into local host-native files so each
model reads concise instructions in its own expected shape. Mechanical
logic stays centralized in Python helpers and small hook wrappers. No
universal runtime import layer is introduced in v1.

## Why now

- **A concrete portability question surfaced.** The AGENTS.md sibling
  decision in `docs/refinement-todo.md` named Codex interest as the
  trigger for revisiting cross-harness support. That signal arrived first
  as a design question, then as direct implementation requests for Codex
  scaffold and plugin packaging.
- **Codex now has compatible primitives.** Codex supports repo
  `AGENTS.md`, skills, custom agents, hooks, and plugin packaging. That
  means the future port can be a real adapter, not just a docs-only
  bridge.
- **The Claude surface should stay stable.** Before adding a second
  host, jig needs a seam around the existing Claude renderer so v1 can
  prove there is no behavior drift for current users.
- **Materialized copies need update metadata.** If jig generates more
  host-native files, it should mark managed files and prepare for future
  update safety before the copied surface grows again.

## Goals

1. **Support matrix is explicit.** Document that v1 supports Claude
   plugin and Claude scaffold modes, and that v2 adds Codex scaffold
   and Codex plugin packaging after their deferred triggers fired.
2. **Logical adapter contract.** Define the host-neutral operations jig
   expects every adapter to provide: render project primer, install
   skills, install agents, install hooks, rewrite helper paths, translate
   hook input/output, and advertise invocation hints.
3. **AGENTS.md route.** Make `AGENTS.md` the canonical cross-agent
   project primer in scaffold mode. `CLAUDE.md` becomes the Claude
   adapter surface rather than the only source of truth.
4. **Source-centralized, runtime-materialized.** Keep one source in the
   jig repo, but scaffold concrete files into the target project. Do not
   add a universal runtime include/import mechanism in v1.
5. **Claude behavior preserved.** Current Claude plugin mode and Claude
   scaffold mode continue to produce equivalent behavior, with tests
   pinning the generated tree and key file contents.
6. **Host-neutral helper assumptions.** Shared Python helpers stop
   depending directly on Claude-only environment names where a
   host-neutral self-location or `JIG_*` convention is sufficient.
7. **Logical hook semantics.** Classify hooks by jig-level semantics
   (`warn` vs. `block`) and let host adapters translate those semantics
   into each host's native hook protocol.
8. **Subagent capability model.** Record what isolation guarantees jig
   needs (`writes`, `read-only fresh review`, `architecture judgment`)
   and define fallback behavior when a host cannot enforce the exact
   capability.
9. **Codex path staged by demand.** Codex scaffold support was
   implemented only after the direct trigger fired; Codex plugin support
   follows after a real install-and-forget distribution ask.

## Non-goals

- **Implementing Codex support before a real trigger.** The initial v1 work
  created the adapter boundary and preserved Claude behavior. Slices 033-05
  and 033-06 implement Codex scaffold and plugin packaging only after direct
  user requests fired their deferred triggers.
- **Universal runtime embedding.** No shared instruction file that every
  host must import at runtime. Generated files should be boring,
  local, and host-native.
- **A cross-host skill router.** Jig will not emulate Claude's or
  Codex's skill-routing behavior. It will render host-native skill
  metadata and let the host route.
- **Changing the jig workflow.** SPIDR, review passes, reconciliation,
  memory-sync, ADR workflow, and status-board semantics remain the same.
- **Full update/migration tooling.** This spec adds metadata needed for
  a future safe update path, but does not implement `jig update` or
  conflict resolution for edited scaffolded files.
- **Support for Cursor, Gemini, Aider, or other harnesses.** The adapter
  shape should not preclude them, but no files are generated for them.

## Support matrix

| Host | Distribution | Status in this spec | Notes |
|---|---|---|---|
| Claude Code | Plugin | v1 supported | Existing `.claude-plugin` package remains valid. |
| Claude Code | Scaffold | v1 supported | Existing `.claude/` scaffold output preserved, with `AGENTS.md` added as canonical primer. |
| Codex | Scaffold | v2 supported | Target shape verified against local Codex 0.133: `AGENTS.md`, `.codex/skills/`, `.codex/hooks.json`, `.codex/agents/*.toml`, plus `.codex/templates/` and non-discoverable helper aliases for copied runtime support. |
| Codex | Plugin | v2 supported | `.codex-plugin/plugin.json`; generated package with rendered Codex skills, `hooks/hooks.json`, templates, bundled canonical agent prompts, and generated TOML custom-agent templates for explicit install. |
| Other harnesses | Any | out of scope | Future adapters may be added after real user signal. |

## Logical adapter contract

Each host adapter should implement the same conceptual operations:

1. **Primer rendering.** Produce the files the host loads at session
   start. For Claude scaffold mode this includes `CLAUDE.md`; for
   Codex this will include `AGENTS.md`.
2. **Skill installation.** Copy/render jig skills into the host's
   project-scoped skill directory, rewriting helper paths as needed.
3. **Agent installation.** Render `implementer`, `reviewer`, and
   `architect` into the host's agent format, preserving capability
   intent.
4. **Hook installation.** Register the seven logical jig hooks against
   host-native lifecycle events.
5. **Hook protocol translation.** Convert jig-level results
   (`continue`, `additional_context`, `block_reason`) into the host's
   required JSON shape and exit-code behavior.
6. **Path/environment binding.** Provide a host-neutral project root and
   jig runtime root to helpers, either via self-location or `JIG_*`
   environment variables.
7. **Managed-file metadata.** Mark generated files so future update
   tooling can distinguish untouched managed files from user-edited
   copies.
8. **Verification fixtures.** Expose stable fixtures for the generated
   tree and hook protocol so behavior is testable without opening an
   interactive Claude or Codex session.

## SPIDR analysis

| Technique | Question | Decision |
|---|---|---|
| **S** - Spike | Do we need a research spike before designing this? | **No for v1.** Claude behavior is already implemented, and Codex's public primitives are now close enough to sketch v2. The uncertain Codex edge cases stay in deferred slices. |
| **P** - Path | Should this ship as one dual-host port or in phases? | **Phased path.** v1 refactors around Claude plugin + scaffold without changing behavior. v2 adds Codex support when demand arrives. |
| **I** - Interface | Where is the portability boundary? | **Host adapters.** The shared workflow model stays in source; adapters render host-native primers, skills, agents, hooks, and manifests. |
| **D** - Data | What generated data needs drift control? | Project primers, skill files, agent files, hook registrations, copied hook scripts, and plugin manifests all need managed metadata or manifest entries. |
| **R** - Rules | What rule keeps token use low? | Materialize host-native prose at scaffold time. Do not require runtime include chains. Shared logic belongs in helpers and hook wrappers, not in multi-host prose abstractions. |

## Known constraints

- **Claude plugin mode is still Claude-specific.** `.claude-plugin`,
  `CLAUDE_PLUGIN_ROOT`, Claude hook event names, and Claude subagent
  type resolution remain valid in the Claude adapter.
- **Codex support can still drift.** Codex scaffold surfaces were verified
  locally against Codex 0.133 for slice 033-05. Codex plugin packaging was
  re-checked against the current official plugin docs for slice 033-06. Future
  scaffold or plugin changes must re-check the exact hook, skill, agent, and
  plugin contracts before changing generated files.
- **Codex custom agents need TOML files.** Slice 033-05 originally
  materialized Markdown role prompts under `.codex/agents/`; current Codex
  custom-agent docs define discoverable custom agents as TOML files. Slice
  033-07 renders TOML from the canonical Markdown prompts for scaffold mode
  and adds an explicit plugin helper for global Codex agent installation.
- **`AGENTS.md` may already be present in target repos.** Scaffold changes must
  avoid clobbering user-owned or pre-existing `AGENTS.md` content.
- **Generated-file headers consume tokens.** Metadata should be compact
  and machine-readable, preferably centralized in a manifest when a
  per-file banner would meaningfully increase prompt load.
- **Host isolation differs.** A "reviewer" can be described in every
  host, but enforcement of read-only tools or fresh context may vary.
  The adapter must document the fallback, not pretend guarantees exist.
- **No changes to `docs/conventions.md` without explicit approval.**
  If this spec needs convention changes, that must be called out before
  implementation.

## Clarifications

| Question | Answer |
|---|---|
| What is v1 vs. v2? | v1 is Claude plugin + Claude scaffold only. v2 introduces Codex support. |
| Should jig centralize runtime instructions with imports/embedding? | No. Centralize source, then materialize host-native files at scaffold time. |
| Should `AGENTS.md` be used? | Yes. `AGENTS.md` becomes the cross-agent route; Claude keeps its adapter surface. |
| Should generated outputs be tested? | Yes. Use golden fixtures for generated trees and hook protocol payloads. |
| Should generated files carry metadata? | Yes, compactly, so future update tooling can detect managed vs. edited files. |
| Should helper logic depend on Claude env vars? | Shared logic should not. Tiny Claude adapters can translate to host-neutral values. |
| How should hooks be modeled? | Jig-level `warn` and `block` semantics first; host adapters translate to native hook JSON/exit behavior. |
| How should subagents be handled? | Preserve the three capability shapes and define fallback behavior when a host cannot enforce them. |

## Slices

- [033-01 - support-matrix-and-adapter-contract](slice-01-support-matrix-and-adapter-contract.md)
- [033-02 - agents-md-canonical-primer](slice-02-agents-md-canonical-primer.md)
- [033-03 - scaffold-host-renderer-boundary](slice-03-scaffold-host-renderer-boundary.md)
- [033-04 - generated-file-metadata](slice-04-generated-file-metadata.md)
- [033-05 - codex-scaffold-adapter](slice-05-codex-scaffold-adapter.md)
- [033-06 - codex-plugin-packaging](slice-06-codex-plugin-packaging.md)
- [033-07 - codex-custom-agent-toml-adapter](slice-07-codex-custom-agent-toml-adapter.md)
