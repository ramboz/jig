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

Second example: `/jig:arch-review` ships a slim four-section
architecture / design-doc / RFC / ADR-draft review (summary / strengths
/ concerns / open questions). Same category-based deferral: any
user-installed skill whose description identifies it as handling
architecture, design, RFC, or technical-design review wins. The pattern
is reusable, not a one-off — `/jig:pr-review` and `/jig:arch-review`
are the two current instances.

This keeps jig opinionated about *workflow* (spec-driven, reviewer-gated,
deterministic helpers) while staying out of the way of *judgment skills*
you've already invested in.

## Installation

### From this repository (Claude Code CLI)

In a Claude Code session:

```text
/plugin marketplace add ramboz/jig
/plugin install jig@jig
```

This is the recommended path. The repo is itself a single-plugin
marketplace — no separate registry is needed. Restart Claude Code (or
open a fresh session) after install so the three subagents
(`implementer` / `reviewer` / `architect`) become reachable as
`subagent_type` values.

### From a release zip (Claude Code Desktop)

1. Download `jig-vX.Y.Z.zip` from the
   [Releases page](https://github.com/ramboz/jig/releases).
2. Drag the zip into the Desktop app's `/plugin` UI.

For a one-shot session install via the CLI without a marketplace:

```bash
claude --plugin-dir path/to/jig-vX.Y.Z.zip
```

### From source (contributors)

See [CONTRIBUTING.md](CONTRIBUTING.md) for the local-marketplace
workflow used during development.

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

PRs are merged via **squash merge** so that release-please reads clean
conventional-commit subjects on `main`. The `pr-title.yml` workflow
enforces conventional-commit shape on PR titles
(`feat(scope): …` / `fix(scope): …` / etc.). See CONTRIBUTING.md
"Releasing" for the version-bump effect of each prefix.

## Status

Tier 0 skills are in spec/draft phase. First implementation slice: `001-01 greenfield-scaffold`.

Check [docs/specs/README.md](docs/specs/README.md) for the current status board.
