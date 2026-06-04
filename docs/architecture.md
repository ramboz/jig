> Status: Draft (technical mechanics; vision and design principles live in [product-vision.md](product-vision.md))
>
> This document evolves as we make decisions. Open questions are explicit, not papered over.

# Architecture: jig

> For *what jig is*, *who it's for*, and *why it works the way it does*, see
> [product-vision.md](product-vision.md). This document covers the technical
> mechanics: plugin structure, hook spine, subagent roster, module boundaries,
> open architectural questions.

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

## Runtime wiring

How a session actually flows in plugin-install mode. The LLM layer (user →
Claude → skill router → SKILL.md → helper or subagent → on-disk state) is
non-deterministic; the nine hooks form the deterministic spine that fires on
fixed events and can inject context or block tool calls.

```mermaid
flowchart TB
    user([User message])
    claude[Claude]
    router{{Skill router<br/>auto-trigger by description}}
    skill["SKILL.md body<br/>(progressive load)"]

    user --> claude
    claude --> router
    router --> skill
    skill -->|bash recipe| helpers["scripts/*.py<br/>workflow · review · adr · tdd<br/>land · migrate · scaffold"]
    skill -->|Task tool| subs["Subagents<br/>implementer (writes)<br/>reviewer (read-only)<br/>architect (rare)"]

    helpers --> jig[(.jig/scaffold.json)]
    helpers --> adrs[(docs/decisions/)]
    helpers --> specs[(docs/specs/)]
    subs --> specs
    subs --> memory[(CLAUDE.md<br/>+ docs/memory/)]

    subgraph hookspine["Deterministic spine — 9 hooks"]
        direction TB
        h1["SessionStart · UserPromptSubmit · PreToolUse·Read<br/>jig-context-check<br/>context-fill + in-session growth/compact nudge"]
        h2["UserPromptSubmit<br/>jig-memory-scan<br/>surface unknown references"]
        h3["PreToolUse · Task<br/>jig-telemetry<br/>async log, never blocks"]
        h4["PreToolUse · Skill<br/>jig-skill-trace<br/>async skill-routing log, never blocks"]
        h5["PreToolUse · Edit/Write<br/>jig-spec-gate<br/>blocks conventions.md edits"]
        h6["PreToolUse · Edit/Write<br/>jig-secret-scan<br/>blocks high-confidence secrets"]
        h7["PostToolUse · Edit/Write<br/>jig-post-edit-verify<br/>same-turn edit-landed check"]
        h8["PostToolUse · Edit/Write<br/>jig-boundary-change-warn<br/>nudge ADR on contract-artifact edit"]
        h9["Stop<br/>jig-task-capture<br/>surface TODOs next turn"]
    end

    h1 -. additionalContext .-> claude
    h2 -. additionalContext .-> claude
    h5 -. exit 2 = blocks Edit .-> claude
    h6 -. exit 2 = blocks Edit .-> claude
    h7 -. additionalContext .-> claude
    h8 -. additionalContext .-> claude
    h9 -. next-turn context .-> claude
```

- **Skill router** is a Claude Code internal — it auto-matches the user's message against every `SKILL.md` `description` field and loads the first match. Skills marked `disable-model-invocation: true` are skipped.
- **`bash recipe` arrow**: most `SKILL.md` bodies end with a deterministic bash block that calls the matching `.py` helper. Skills without a helper (`pr-review`, `arch-review`, `contracts`, `vision-elicitation`, plus the slice-to-spec workflow inside `migrate`) are judgment-only. `pr-review` and `arch-review` stay judgment-only as skills, but are *invoked* deterministically from the post-implementation flow via `review.py pr-review` / `review.py arch-review` prompt builders (see [skills/spec-workflow/SKILL.md](../skills/spec-workflow/SKILL.md) § "After implementation").
- **`Task tool` arrow**: `SKILL.md` can dispatch a fresh subagent via the `Task` tool. The three roles in `agents/` (`implementer`, `reviewer`, `architect`) are real `subagent_type` values when jig is installed as a plugin; outside the plugin they fall back to `general-purpose`.
- **Hook spine** intercepts at five Claude Code event types (SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, Stop) via nine hook scripts. Two are async log-only — never block, never inject (`telemetry`, `skill-trace`); five inject `additionalContext` (`context-check`, `memory-scan`, `post-edit-verify`, `boundary-change-warn`, `task-capture`); two can block tool calls with exit-code 2 (`spec-gate`, `secret-scan`).

Scaffold-mode wiring is identical in shape — only path strings differ
(`${CLAUDE_PROJECT_DIR}/.claude/...` instead of `${CLAUDE_PLUGIN_ROOT}/...`).
See the **Dual-distribution** decision below for the rewrite details.

## Core architecture decisions

### Hooks are the deterministic spine; skills are the LLM layer
*Principle:* see [product-vision.md § Design principles](product-vision.md#design-principles) (#1).
*Mechanics:* hook entries live in `hooks/hooks.json` and run unconditionally on their declared event; skill entries live in `skills/<name>/SKILL.md` and auto-trigger via description matching against user messages.

### Hook scripts: Python 3, never jq
`jq` is not installed by default on macOS. All hook scripts use inline `python3 -c` for JSON parsing. Python 3 is reliably available.

### Hook command paths: `${CLAUDE_PLUGIN_ROOT}/hooks/scripts/...`
Plugin `bin/` PATH injection is Bash-tool only, not hook commands. All hook `command` fields use the full `${CLAUDE_PLUGIN_ROOT}` path.

### Dual-distribution: plugin install AND scaffolded install
*Principle:* [product-vision.md § Design principles](product-vision.md#design-principles) (#7) — dev owns the scaffolding, not the plugin runtime.

As of [spec 016-scaffold-mode](specs/016-scaffold-mode/spec.md) (slices
016-01 + 016-02 + 016-03 all DONE; 016-04 deferred), `scaffold-init` copies the
runtime machinery (`skills/`, `agents/`, `hooks/scripts/`) into the
user's `.claude/` directory under `jig-` prefixed names
(`.claude/skills/jig-<name>/`, `.claude/agents/jig-<name>.md`,
`.claude/hooks/scripts/jig-*.sh`), and generate/merge
`.claude/settings.json` to register the nine jig hooks against the
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
*Principle:* see [product-vision.md § Design principles](product-vision.md#design-principles) (#2).
*Mechanics:* the `jig-context-check` hook warns at session start when fill approaches the ~40% threshold, and nudges again on in-session growth as context crosses configurable bands (40/60/80%, plus a higher active-compaction band per spec 057-02). Skills use progressive disclosure — body loads only on trigger; supporting files load only when referenced.

### Three subagents, no more
*Principle:* see [product-vision.md § Design principles](product-vision.md#design-principles) (#3) — subagents are defined by what context they need isolated from, not by job title.

*Roster:*
- `implementer`: TDD discipline, writes deliverables
- `reviewer`: read-only, fresh context per review. Fires 1–3 times per slice under the multi-perspective post-implementation flow: once for compliance, once for craft (`pr-review`), and once for arch (`arch-review`) when the slice's frontmatter declares `arch_review: true`. Reused as the agent shape for all three passes — no `pr-reviewer` or `arch-reviewer` agent.
- `architect`: rare, ADR-style output

As of [spec 011-01 (plugin-self-install)](specs/011-plugin-self-install/spec.md),
all three are reachable as real `subagent_type` values when jig is installed
as a Claude Code plugin (the bundled `jig` marketplace — renamed from
`jig-dev` in slice 013-04 — or any future public install). Pre-spec-011, every caller fell back to
`subagent_type: "general-purpose"`. Slice 011-02 added
`review.py subagent-type` so SKILL.md's bash recipe picks the real
`reviewer` deterministically when installed and degrades to
`general-purpose` when running from source.

## Module boundaries

Six top-level concerns, named in [product-vision.md § Core features](product-vision.md#core-features-prioritized) at the vision layer:

- `skills/` — auto-triggering LLM behaviors (one `SKILL.md` + supporting files per skill)
- `agents/` — three subagent definitions (`implementer` / `reviewer` / `architect`)
- `hooks/` — deterministic spine (`hooks.json` + Python 3 scripts under `hooks/scripts/`)
- `templates/` — source templates that `scaffold-init` copies into new projects (CLAUDE.md, docs/, brief)
- `scripts/` — Python helpers invoked by skills, one per skill where the work is mechanical: `workflow.py`, `review.py`, `adr.py`, `tdd.py`, `land.py`, `migrate.py`, `scaffold.py`, plus `usage.py` (per-spec token/cost reporting, spec 056)
- `.claude-plugin/` — plugin manifest (`plugin.json`) + marketplace descriptor (`marketplace.json`)

Interface contracts between these modules are deliberately deferred — today's coupling is read-only and one-directional (skills read templates; helpers read specs; hooks read events; nothing writes across the module boundary). Will tighten when the first bidirectional case appears.

## Data model

Jig is a workflow layer, not a data application (per [product-vision.md](product-vision.md) non-goals). Relevant on-disk state is small:

- `.jig/scaffold.json` — install manifest: which tiers chosen, when, by which jig version (per [ADR-0001](decisions/adr-0001-scaffold-stable.md))
- `.claude/skill-usage.jsonl` — append-only log written by `jig-telemetry.sh` (Task spawns) and `jig-skill-trace.sh` (Skill invocations; `event: skill_invoked`); read via [docs/skill-routing-verification.md](skill-routing-verification.md). Histogram consumer is `workflow.py routing-stats` (slice 041-02)
- `docs/specs/**/spec.md` — the only project-level state jig owns; everything else lives in the dev's repo, owned by the dev

## Contract surfaces

<!-- elicited: 2026-05-15 / status: skipped -->

_Skipped: jig does not currently expose schema-shaped external interfaces. It is a Claude Code plugin — the only external surfaces are SKILL.md frontmatter (consumed by the Claude Code router) and CLI argparse interfaces on the `.py` helpers (consumed by humans + scripts). Neither warrants an OpenAPI / JSON Schema / AsyncAPI / `.proto` / GraphQL SDL artifact. If jig later grows an HTTP / events / RPC surface (e.g. a telemetry sink endpoint, a remote-spec-status query API), this section gets filled per the `/jig:contracts` skill's per-surface recommendation table._

_Self-coherence note (spec 022-02): this slot exists so the `/jig:independent-review` reviewer-prompt's conditional contract-surface check stays quiet on jig's own slice reviews — the `status: skipped` marker + the no-bullet body together signal "no surfaces to check" to the detector. See [skills/contracts/SKILL.md](../skills/contracts/SKILL.md) for the per-surface recommendation table the elicitation references._

## Open questions

- `SubagentStart` hook event: documented in changelog (v2.0.43) but absent from official plugin docs. Deferred — see `docs/refinement-todo.md`.
- Hook strictness profiles (`SCAFFOLD_HOOK_PROFILE`): deferred — unread env var is worse than no env var.
- Does the `additionalContext` format differ between `UserPromptSubmit` and `Stop` hooks? Verify during implementation of 002-03.
