> Status: Draft (wizard-generated equivalent — manually seeded for jig itself)
>
> This document evolves as we make decisions. Open questions are explicit, not papered over.

# Architecture: jig

## What jig is

An installable Claude Code plugin that scaffolds AI-native development practices into new projects. Tier 0 skills always install; Tier 1 installs by default; Tier 2 opts in by signal.

## Plugin structure

```
jig/
├── .claude-plugin/plugin.json     # Manifest
├── skills/                        # Claude Code skills (auto-trigger + /menu)
├── agents/                        # Subagent definitions (implementer, reviewer, architect)
├── hooks/                         # Deterministic enforcement layer
│   ├── hooks.json
│   └── scripts/                   # Python 3 scripts (no jq dependency)
├── templates/                     # Source templates scaffold-init reads
└── docs/                          # Dev docs for building jig itself (dogfooded)
```

## Core architecture decisions

### Hooks are the deterministic spine; skills are the LLM layer
- Skills carry workflows and reasoning. Auto-trigger via description matching.
- Hooks enforce gates that don't require judgment. Always run.
- Everything that MUST happen is a hook. Everything that should happen when relevant is a skill.

### Hook scripts: Python 3, never jq
`jq` is not installed by default on macOS. All hook scripts use inline `python3 -c` for JSON parsing. Python 3 is reliably available.

### Hook command paths: `${CLAUDE_PLUGIN_ROOT}/hooks/scripts/...`
Plugin `bin/` PATH injection is Bash-tool only, not hook commands. All hook `command` fields use the full `${CLAUDE_PLUGIN_ROOT}` path.

### Dual-distribution: plugin install AND scaffolded install
As of [spec 016-scaffold-mode](specs/016-scaffold-mode/spec.md) (slices
016-01 + 016-02 + 016-03 all DONE; 016-04 deferred), `scaffold-init` copies the
runtime machinery (`skills/`, `agents/`, `hooks/scripts/`) into the
user's `.claude/` directory under `jig-` prefixed names
(`.claude/skills/jig-<name>/`, `.claude/agents/jig-<name>.md`,
`.claude/hooks/scripts/jig-*.sh`), and generate/merge
`.claude/settings.json` to register the five jig hooks against the
project-local script paths. SKILL.md path strings are rewritten from
`${CLAUDE_PLUGIN_ROOT}/skills/<name>/` to
`${CLAUDE_PROJECT_DIR}/.claude/skills/jig-<name>/`, and hook command
paths from `${CLAUDE_PLUGIN_ROOT}/hooks/scripts/` to
`${CLAUDE_PROJECT_DIR}/.claude/hooks/scripts/`, both at copy time.

The settings.json merge follows an **append-with-marker** strategy
(slice 016-02): every jig-managed hook entry carries
`metadata: {managed_by_jig: true}`. Pre-existing non-hook top-level
fields (`permissions`, `env`, etc.) pass through verbatim;
pre-existing non-jig hooks survive; jig entries replace in place on
re-run (idempotent). A safety check (`UnmanagedHooksError`, exit 3)
refuses to write when the existing settings.json has hooks but none
carry the jig marker — `--force` is the documented escape.

The plugin distribution (zip + marketplace) is unchanged; the source
SKILL.md files and `hooks/hooks.json` keep their `${CLAUDE_PLUGIN_ROOT}`
paths. Only the scaffold path rewrites. Coexistence between scaffolded
and plugin installs falls under Claude Code's normal
project-scoped-wins precedence; jig introduces no new arbiter.

### Context economy (the "dumb zone")
Above ~40% context fill, model recall degrades. Practical ceiling: 8 MCP servers, ~80 active tools. The `jig-context-check` hook warns at session start. Skills use progressive disclosure — body loads only on trigger; supporting files load only when needed.

### Three subagents, no more
- `implementer`: TDD discipline, writes deliverables
- `reviewer`: read-only, fresh context per review
- `architect`: rare, ADR-style output
Subagents are defined by what context they need isolated from, not by job title.

As of [spec 011-01 (plugin-self-install)](specs/011-plugin-self-install/spec.md),
all three are reachable as real `subagent_type` values when jig is installed
as a Claude Code plugin (the bundled `jig` marketplace — renamed from
`jig-dev` in slice 013-04 — or any future public install). Pre-spec-011, every caller fell back to
`subagent_type: "general-purpose"`. Slice 011-02 added
`review.py subagent-type` so SKILL.md's bash recipe picks the real
`reviewer` deterministically when installed and degrades to
`general-purpose` when running from source.

## Module boundaries

> **Deferred — no signal yet on what modules jig itself will have.**
> Will be decided in the first implementation spec (001-scaffold-init, slice 001-01).

## Data model

> **Deferred — jig is a skill pack, not a data application.**
> Relevant state: `scaffold.json` manifest (install state), `skill-usage.jsonl` (telemetry), spec files.

## Open questions

- `SubagentStart` hook event: documented in changelog (v2.0.43) but absent from official plugin docs. Deferred — see `docs/refinement-todo.md`.
- Hook strictness profiles (`SCAFFOLD_HOOK_PROFILE`): deferred — unread env var is worse than no env var.
- Does the `additionalContext` format differ between `UserPromptSubmit` and `Stop` hooks? Verify during implementation of 002-03.
