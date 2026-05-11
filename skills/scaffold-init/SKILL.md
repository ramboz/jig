---
name: scaffold-init
description: >
  Initialize an AI-native development workspace with spec-driven workflow infrastructure.
  Use when starting a new project, setting up Claude Code on a codebase for the first
  time, or when the user says scaffold, initialize, set up AI workflow, onboard this
  repo, or similar. Do not use for adding an individual skill or config to an already-
  scaffolded project — that is handled by the relevant tier skill directly.
user-invocable: true
---

> **Status: DRAFT — spec at [docs/specs/001-scaffold-init/spec.md](../../docs/specs/001-scaffold-init/spec.md)**
>
> Slice 001-01 (greenfield-scaffold) is the next slice to implement.

## What this skill does (when implemented)

Runs a discovery wizard that:
1. Detects project signals (LLM/agent work, CI presence, existing tests, team size)
2. Selects appropriate tiers to install (Tier 0 always; Tier 1 default; Tier 2 opt-in)
3. Scaffolds `docs/` structure, `CLAUDE.md` with Hot Cache section, `hooks/`, and `scaffold.json`
4. Produces `brief.md` summarizing what was scaffolded and what decisions were deferred
5. Populates `docs/refinement-todo.md` with explicit deferred decisions and resolution triggers

## Gotchas

- The spec-gate hook for `docs/conventions.md` activates AFTER scaffold-init completes —
  it cannot gate its own creation.
- `templates/CLAUDE.md.template` is the source template. The project's own `CLAUDE.md`
  is a live document. scaffold-init reads from the template, never from the live file.
- `docs/memory/people.md` is only created when ≥2 git contributors OR user confirms team context.
