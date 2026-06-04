---
status: IN_PROGRESS
skill: scaffold-init, migrate, release-pipeline
tier: host-adapter
adr_required: false
---

# Spec 059: Codex port polish

## Overview

Spec 033 made Codex a supported host for jig: scaffold mode renders
`AGENTS.md` plus `.codex/` runtime machinery, plugin mode builds a
Codex-native package, and role agents are materialized as Codex TOML
custom-agent files. That closes the core port.

This spec finishes the parity polish that remains after the core port:
legacy migrate commands that still speak Claude paths, Codex plugin
install/trust verification, Codex-specific skill override language,
real role-agent dogfooding, and a watch point for future plugin-native
custom-agent discovery.

The goal is not to erase every host difference. The goal is to make every
remaining difference either implemented, validated, or explicitly named
where users encounter it.

## Goals

1. **Make migrate machinery host-aware.** Codex scaffold users should not
   hit Claude-shaped `.claude/` output when they run migrated machinery
   commands from `.codex/skills/`.
2. **Verify the real Codex install contract.** A generated Codex plugin
   package should be smoke-tested through Codex's actual local plugin
   surfaces where possible, including marketplace install, hook trust,
   skill visibility, and the explicit custom-agent install helper.
3. **Document hook trust honestly.** Codex plugin hooks require user trust
   before they execute. The install path should make that step visible
   instead of implying install-and-forget behaves identically to Claude.
4. **Align skill override and deferral prose.** jig's skill docs should
   stop implying Claude-only `~/.claude/skills` override paths when a
   Codex user is reading rendered Codex skill copies.
5. **Dogfood role capability semantics in Codex.** `implementer`,
   `reviewer`, and `architect` TOML roles should be exercised in a real
   or closest-available Codex session, with any enforcement gaps recorded
   in generated docs and tests.
6. **Keep watching plugin-native agent discovery.** If Codex later
   documents plugin-level custom-agent discovery, jig should add that
   adapter without changing canonical role prompts.

## Non-goals

- **No reopening Spec 033.** Spec 033 remains the core host-adapter port.
  This spec layers polish and verification on top of its DONE state.
- **No undocumented Codex manifest fields.** Until Codex documents a
  plugin-level agent surface, jig continues to avoid unsupported
  `.codex-plugin/plugin.json` fields.
- **No broad migration rewrite.** This spec touches migrate behavior only
  where Codex parity requires it.
- **No new cross-host abstraction for its own sake.** Host-aware helpers
  should reuse the renderer boundary from Spec 033 where that is enough.
- **No false isolation claims.** If Codex cannot enforce a Claude-like
  role guarantee, the implementation should document the exact fallback.

## Current state verified 2026-05-29

- Spec 033 is DONE. jig supports Claude plugin/scaffold mode and Codex
  scaffold/plugin mode.
- Codex scaffold mode writes `.codex/agents/jig-*.toml`; Codex plugin
  packaging includes generated TOML templates and an explicit
  `--install-codex-agents` helper.
- `docs/refinement-todo.md` still records one known parity gap:
  `migrate copy-machinery` and parts of `rename-decisions` remain
  Claude-shaped in Codex scaffold mode.
- Spec 047 provides generic install contract validators. This spec
  should coordinate with it and keep Codex-specific live/plugin-trust
  checks here when they are narrower than the generic release contract.
- Official Codex plugin docs currently document plugin manifests, skills,
  MCP servers, apps, and hooks. Custom agents are documented as TOML
  files under `.codex/agents/`, not as a plugin manifest field.

## Decomposition

**Suggested SPIDR axis: Interface.** Each slice polishes one user-facing
Codex interface: migrate commands, plugin install/trust, override prose,
role agents, and future agent discovery.

### Slices

1. **`059-01 host-aware-migrate-machinery`** - Make `migrate`
   machinery operations route through host-aware primer, runtime, and
   scan-path choices so Codex users do not get Claude-only output.
2. **`059-02 codex-hook-trust-onboarding`** - Make Codex plugin hook
   trust an explicit, tested post-install step in README and generated
   plugin/user-facing guidance.
3. **`059-03 codex-install-contract-smoke`** - Add a Codex-specific
   smoke validator that builds the generated package and probes local
   Codex plugin, hook, skill, and agent-install surfaces when the Codex
   CLI is available.
4. **`059-04 codex-skill-override-deferral`** - Render or document
   Codex-appropriate override/deferral language for richer user skills
   instead of leaking Claude-only `~/.claude/skills` assumptions.
5. **`059-05 codex-role-capability-dogfood`** - Exercise jig's three
   Codex TOML role agents and record the precise capability semantics
   users can rely on.
6. **`059-06 codex-plugin-agent-discovery-spike`** - Re-check current
   Codex docs and local CLI behavior for plugin-native custom-agent
   discovery; if present, specify the adapter, otherwise preserve the
   explicit install-helper contract.

## Dependencies / coordination

- Slice 059-01 closes the host-aware migrate entry in
  `docs/refinement-todo.md`.
- Slice 059-03 should coordinate with Spec 047 so generic release
  contract validation and Codex-specific live smoke coverage do not
  duplicate each other.
- Slice 059-04 should coordinate with Specs 040 and 048 if they touch
  isolation-honesty or public onboarding prose at the same time.
- Slice 059-06 should use official Codex/OpenAI docs as the source of
  truth and should not add undocumented plugin manifest fields.
- If any slice needs to change `docs/conventions.md`, stop and ask for
  explicit human approval first.

## References

- [Spec 033: Host adapter portability](../033-host-adapter-portability/spec.md)
- [Spec 047: Install contract verification](../047-install-contract-verification/spec.md)
- [docs/refinement-todo.md](../../refinement-todo.md)
- [scripts/build_codex_plugin.py](../../../scripts/build_codex_plugin.py)
- [skills/migrate/migrate.py](../../../skills/migrate/migrate.py)
- [skills/scaffold-init/scaffold.py](../../../skills/scaffold-init/scaffold.py)
