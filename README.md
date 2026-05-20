# jig

> A Claude Code plugin that scaffolds AI-native development practices into new projects.

**jig** (noun): a tool that guides other tools to work accurately and consistently.

## Why jig exists

Two years of vibe coding surfaced the same scars on every non-trivial project:

- **Horizontal drift.** LLMs prefer to refactor whole layers before delivering anything end-to-end. By the time the flow lands, it's broken — and the tokens are gone. [SPIDR](https://www.mountaingoatsoftware.com/blog/five-simple-but-powerful-ways-to-split-user-stories) (Mike Cohn) splits work into thin vertical slices the model can actually hit.
- **Invisible scope creep.** Without explicit acceptance criteria in the repo, "done" is whatever the model decided it meant. [Spec-driven development](https://github.com/github/spec-kit) makes the contract verifiable.
- **Manual workflow repetition.** Spec → plan review → SPIDR alignment → implement → verify → reconcile docs. Every session. Encoding the loop as skills + hooks removes the manual babysitting.
- **Implementers grade their own homework.** Sessions routinely end with "done" claims over partial work. A fresh subagent with only the spec and the diff — no chat history — catches the gaps ([LLM-as-judge](https://arxiv.org/abs/2306.05685)).
- **Review depth shouldn't be locked in a private repo.** Internal PR/arch review skills can't ship publicly, but the workflow still needs a floor. jig's extension points defer to richer user-installed skills when present.
- **Contracts parallelise work.** Strong interface contracts let frontend and backend (human or LLM) progress independently, and give the model a precise target instead of one it has to infer.
- **Sessions are short; projects aren't.** A memory layer (hot cache + deep storage + inbox) means a new session picks up where the last left off without a re-briefing.

jig encodes all of this so you don't rediscover it session by session.

## What it does

jig installs a focused, opinionated workflow layer into your project:

- **Spec-driven development** — SPIDR-split vertical slices with Definition of Done per slice
- **Multi-perspective review** — every slice runs through compliance (`jig:independent-review`, always) + craft (`pr-review`, always) + architecture (`arch-review`, on-demand via `arch_review: true` slice frontmatter). The craft + arch passes defer to richer user-installed skills when present.
- **Typed contracts** — enforced boundaries at module interfaces for AI-legible codebases
- **Memory layer** — cross-session continuity via hot cache + deep storage + inbox
- **Deterministic gates** — hooks enforce "this MUST happen"; skills handle "when relevant"

## Design philosophy

> Intuitive automated triggering at the right moments, over explicit command surfaces.

- 5 Tier 0 skills (not 100+)
- 3 subagents (not 48 like ECC)
- Hooks are the spine; skills are the LLM layer
- 8-12 skills total when complete

See [docs/product-vision.md](docs/product-vision.md) for the full vision (target users, competitive landscape, design principles) and [docs/architecture.md](docs/architecture.md) for the technical mechanics.

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

The `pr-review` and `arch-review` skills are not just on-demand — the
`spec-workflow` skill auto-triggers them as part of the post-implementation
review for every slice (craft pass always; arch pass on-demand via
`arch_review: true` in the slice's frontmatter). Your installed skill wins
the dispatch automatically.

## Installation

jig ships in two install shapes. Both are served from the same repo;
pick the one that matches how you intend to relate to the machinery.

### Scaffold into your repo (recommended — own the machinery)

> **Scaffold to own and edit the machinery in version control.**

The default `scaffold-init` flow copies jig's skills, agents, hooks,
and helper scripts into your project's `.claude/` directory, so you
can edit any `SKILL.md` or helper under version control and
customize jig per-project. The Claude Code skill router auto-discovers
the scaffolded skills as project-scoped — no plugin install required.

In a Claude Code session at your project root:

```text
/jig:scaffold-init
```

This produces `<your-project>/.claude/skills/jig-*/`,
`.claude/agents/jig-*.md`, `.claude/hooks/scripts/jig-*.sh`, and
`.claude/settings.json` registering the seven jig hooks against the
project-local paths. The pre-016-03 docs-only behavior is preserved
via `python3 scaffold.py --plugin-only <target>` if you want to
combine scaffolded docs with a plugin-installed runtime.

Verify the scaffold succeeded:

```bash
python3 scripts/verify_install.py --mode scaffold --project-root .
```

Expected output is four `PASS` lines and `summary: 4/4 passed`.

### From this repository (Claude Code CLI — install-and-forget)

> **Plugin install to install-and-forget; the machinery stays under
> `${CLAUDE_PLUGIN_ROOT}` and upgrades centrally.**

In a Claude Code session:

```text
/plugin marketplace add ramboz/jig
/plugin install jig@jig
```

The repo is itself a single-plugin marketplace — no separate registry
is needed. Restart Claude Code (or open a fresh session) after install
so the three subagents (`implementer` / `reviewer` / `architect`)
become reachable as `subagent_type` values.

### From a release zip (Claude Code Desktop)

1. Download `jig-vX.Y.Z.zip` from the
   [Releases page](https://github.com/ramboz/jig/releases).
2. In the Desktop app: **Customize → Personal Plugins (+) → Create Plugin → Upload plugin**, then drop the zip.

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
