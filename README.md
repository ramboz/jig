# jig

> A Claude Code plugin that scaffolds AI-native development practices into new projects.

**jig** (noun): a tool that guides other tools to work accurately and consistently.

## What it does

jig installs a focused, opinionated workflow layer into your project:

- **Spec-driven development** — SPIDR-split vertical slices with Definition of Done per slice
- **Independent review** — a reviewer subagent with fresh context evaluates every implementation
- **Typed contracts** — enforced boundaries at module interfaces for AI-legible codebases
- **Memory layer** — cross-session continuity via hot cache + deep storage + inbox
- **Deterministic gates** — hooks enforce "this MUST happen"; skills handle "when relevant"

## Design philosophy

> Intuitive automated triggering at the right moments, over explicit command surfaces.

- 5 Tier 0 skills (not 100+)
- 3 subagents (not 48 like ECC)
- Hooks are the spine; skills are the LLM layer
- 8-12 skills total when complete

See [docs/architecture.md](docs/architecture.md) for the full reasoning.

## Extension points

> **Bring your own depth; jig provides the floor.**

Some jig skills ship as **lightweight baselines** designed to defer to
richer user-level skills when both are present. The auto-triggering
description for each such skill includes an explicit deferral hint, so
the Claude Code skill router picks a more specific user skill over
jig's baseline.

Example: `/jig:pr-review` ships a slim four-section PR review (scope /
blockers / nits / strengths). Its deferral is **category-based, not
name-specific** — any user-installed skill whose description identifies
it as handling PR review, code review, or diff review wins, regardless
of what the user named it. The common location is
`~/.claude/skills/pr-review/`, but a skill named `code-reviewer`,
`team-pr`, or anything else in that category beats jig's baseline too.
The one carve-out is the bundled `review` skill — jig does not defer to
that one (it stays below jig's baseline as the generic fallback).

This keeps jig opinionated about *workflow* (spec-driven, reviewer-gated,
deterministic helpers) while staying out of the way of *judgment skills*
you've already invested in.

## Installation

```bash
# Via Claude Code plugin manager
claude plugins install github:ramboz/jig
```

> Not yet on the plugin marketplace. Install from source for now.
>
> **Contributors:** see [CONTRIBUTING.md](CONTRIBUTING.md) for the local
> dev install via the bundled `jig-dev` marketplace — it's the path that
> makes the three subagents (`implementer` / `reviewer` / `architect`)
> reachable while developing jig itself.

## Getting started

Once installed, open a new project directory in Claude Code and say:
> "Set up this project for AI-native development"

The `scaffold-init` skill will run and produce the docs/ scaffolding.

## Repository structure (for contributors)

```
.claude-plugin/plugin.json       # Plugin manifest
.claude-plugin/marketplace.json  # Local dev marketplace descriptor
skills/                          # Skill definitions (SKILL.md per skill)
agents/                          # Subagent definitions
hooks/                           # Hook configuration + Python scripts
scripts/                         # Top-level dev scripts (verify-install, …)
templates/                       # Source templates scaffold-init generates from
docs/                            # Dev docs for jig itself (dogfooded workflow)
  specs/                         # Specs for jig's own features
  memory/                        # jig's own memory layer
  decisions/                     # Architectural decisions (ADRs)
```

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) for the local install + verify
flow, then [docs/workflow.md](docs/workflow.md) for the spec lifecycle.
Every change to jig starts with a spec.

## Status

Tier 0 skills are in spec/draft phase. First implementation slice: `001-01 greenfield-scaffold`.

Check [docs/specs/README.md](docs/specs/README.md) for the current status board.
