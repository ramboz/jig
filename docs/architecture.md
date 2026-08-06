> Status: Stable

# Architecture: jig

> For *what jig is*, *who it's for*, and *why it works the way it does*, see
> [product-vision.md](product-vision.md). This document covers the technical
> mechanics: plugin structure, hook spine, subagent roster, module boundaries,
> open architectural questions.

## Plugin structure

```
jig/
├── .claude-plugin/plugin.json     # Manifest
├── .codex-plugin/plugin.json      # Codex plugin manifest
├── skills/                        # Claude Code skills (auto-trigger + /menu)
├── agents/                        # Subagent definitions (implementer, reviewer, architect)
├── hooks/                         # Deterministic enforcement layer
│   ├── hooks.json
│   └── scripts/                   # shell/Python hook helpers (no jq dependency)
├── templates/                     # Source templates scaffold-init reads
└── docs/                          # Dev docs for building jig itself (dogfooded)
```

This is still the canonical source tree. Claude plugin mode reads these
files directly from the installed plugin; Claude and Codex scaffold modes
materialize host-native copies into the target project. Codex plugin mode
materializes a plugin package from the same source via
`scripts/build_codex_plugin.py`, rewriting only the staged skill copies.
Future host adapters should render from the same source rather than fork
the workflow model.

## Host support matrix

| Host | Distribution | Status | Notes |
|---|---|---|---|
| Claude Code | Plugin | v1 supported | Existing `.claude-plugin` package remains valid. |
| Claude Code | Scaffold | v1 supported | Existing `.claude/` scaffold output remains the default ownership model. |
| Codex | Scaffold | v2 supported | Project-local output lives under `AGENTS.md` and `.codex/`. |
| Codex | Plugin | v2 supported | `.codex-plugin/plugin.json` plus rendered Codex skills, root `hooks/hooks.json`, templates, and canonical agent prompts are produced by `scripts/build_codex_plugin.py`. |
| Other harnesses | Any | out of scope | Future adapters need their own real user signal and spec slices. |

### Lifecycle entry gate — host capability (spec 098 / ADR-0044)

The `PostToolUse` entry gate (`jig-entry-gate.sh` + `lib/entry_gate.py`) nudges on
an out-of-lifecycle source edit. Its logic is one host-agnostic Python helper; the
build applies the standard Codex substitutions (`CLAUDE_PROJECT_DIR` →
`CODEX_PROJECT_DIR`, infra dir `.claude` → `.codex`), while the host-agnostic
`.jig/spec-ref` marker path is preserved.

Cell states (same legend as 083-08): **supported** = verified on this host;
**degraded** = works via shared/host-neutral code but not independently
runtime-probed on this host, and degrades in the safe direction (fail-open, never
a false block) if the host differs; **unsupported** = the mechanism cannot work.

| Mechanism | Claude | Codex | Fallback for `degraded` |
|---|---|---|---|
| Packaging (hook + `lib/` + registration) | supported | supported | — (built + `--check`-verified for both) |
| Detection logic (claim + status + boundary) | supported | supported | — (same helper; Codex substitutions verified by `test_codex_entry_gate_parity.py`) |
| Opt-out `JIG_ENTRY_GATE` / fail-open | supported | supported | — (env + `except`-swallow are host-neutral) |
| `PostToolUse` payload (`tool_input.file_path`, `session_id`) | supported (probed 2026-07-30) | degraded — not re-probed on the Codex runtime | Shares the exact payload contract of `jig-boundary-change-warn.sh`, which already ships in the same Codex matcher; if Codex omits a field the gate fails open (silent), never errors. |
| Once-per-session cadence (`$TMPDIR` state) | supported | degraded — depends on Codex's session model | If Codex reuses/omits `session_id`, cadence degrades to safe over-fire (never global silence — see `entry_gate._cadence_allows`). |

Runtime confirmation of the two `degraded` rows needs the Codex host in hand
(the 083-08 constraint); they are recorded honestly rather than claimed as
`supported`. Both degrade in the safe direction, so neither is `unsupported`.

**AC3 boundary caveat — dual-host projects.** The two-part source boundary
resolves identically on both hosts for a single-host project. For a project that
carries *both* `.claude/` and `.codex/` adapter dirs, coverage is asymmetric: the
Claude gate lists both dirs as infra (`_INFRA_DIRS` = `.jig`/`.claude`/`.codex`/`.git`),
but the Codex build's blind `.claude`→`.codex` rewrite collapses them, so a Codex
session still nudges on a `.claude/` edit. This is an accepted limit — advisory,
fail-open, safe-over-fire — pinned by `test_codex_entry_gate_parity.py`; closing
it fully needs a build change, deferred until a real dual-host project reports it.

## Host adapter boundary

The architecture boundary is between jig's **logical workflow model**
and a host's **materialized runtime files**. Jig keeps one source for
skills, agent instructions, hook scripts, docs templates, and helper
code; each host adapter renders the files that a specific harness knows
how to load.

Every adapter must account for the same logical operations:

1. **Primer rendering.** Produce the project primer files the host reads
   at session start. New scaffolded projects use `AGENTS.md` as the
   canonical primer; Claude v1 keeps `CLAUDE.md` as the Claude Code adapter.
2. **Skill installation.** Copy or render jig skills into the host's
   project-scoped skill directory, rewriting helper paths only inside
   the adapter.
3. **Agent installation.** Render `implementer`, `reviewer`, and
   `architect` into the host's custom-agent format while preserving the
   intended capability shape.
4. **Hook installation.** Register the fifteen logical jig hooks against
   host-native lifecycle events.
5. **Hook protocol translation.** Convert jig-level results into the
   host protocol. The logical outcomes are `continue`,
   warning context, and blocking reasons; exit codes and JSON shapes are
   host-specific.
6. **Path/environment binding.** Bind project root and jig runtime root
   through host-neutral `JIG_*` conventions or self-location, with tiny
   host adapters translating from host-specific environment variables
   such as `CLAUDE_PLUGIN_ROOT`.
7. **Managed-file metadata.** Mark or manifest generated files so future
   update tooling can distinguish untouched jig-managed files from
   user-edited copies.
8. **Verification fixtures.** Provide stable generated-tree and hook
   protocol fixtures so adapter behavior can be tested without opening
   an interactive host session.

The implementation keeps Claude behavior in place while defining this
boundary. Codex scaffold generation writes `.codex/` project-local
runtime files. Codex plugin packaging uses the same source tree and a
build-time renderer so plugin users get Codex-shaped skill prose without
checking in a second skill tree.

## Claude runtime wiring

How a session actually flows in Claude plugin-install mode. The LLM layer
(user → Claude → skill router → SKILL.md → helper or subagent → on-disk
state) is non-deterministic; the fifteen hooks form the deterministic spine
that fires on fixed events and can inject context or block tool calls.

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

    subgraph hookspine["Deterministic spine — 16 hooks"]
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
        h10["SessionStart<br/>jig-semantic-index<br/>ready opted-in provider or suggest once"]
        h11["Stop<br/>jig-decision-capture<br/>surface decision candidates next turn"]
        h12["PostToolUse·AskUserQuestion · UserPromptSubmit<br/>jig-decision-inflight<br/>async write-only: in-flight decision stubs to scratch"]
        h13["Stop<br/>jig-claim-check<br/>flag unresolved spec/slice/ADR claims next turn"]
        h14["SessionStart<br/>jig-project-orient<br/>bounded lifecycle orientation hint"]
        h15["PostToolUse · Edit/Write<br/>jig-entry-gate<br/>nudge on out-of-lifecycle source edit"]
        h16["SessionStart<br/>jig-git-freshness<br/>nudge when branch is behind its integration base"]
    end

    h1 -. additionalContext .-> claude
    h2 -. additionalContext .-> claude
    h5 -. exit 2 = blocks Edit .-> claude
    h6 -. exit 2 = blocks Edit .-> claude
    h7 -. additionalContext .-> claude
    h8 -. additionalContext .-> claude
    h10 -. additionalContext .-> claude
    h9 -. next-turn context .-> claude
    h11 -. next-turn context .-> claude
    h13 -. next-turn context .-> claude
    h14 -. additionalContext .-> claude
    h15 -. additionalContext .-> claude
    h16 -. additionalContext .-> claude
```

- **Skill router** is a Claude Code internal — it auto-matches the user's message against every `SKILL.md` `description` field and loads the first match. Skills marked `disable-model-invocation: true` are skipped.
- **`bash recipe` arrow**: most `SKILL.md` bodies end with a deterministic bash block that calls the matching `.py` helper. Skills without a helper (`pr-review`, `arch-review`, `contracts`, `vision-elicitation`, plus the slice-to-spec workflow inside `migrate`) are judgment-only. `pr-review` and `arch-review` stay judgment-only as skills, but are *invoked* deterministically from the post-implementation flow via `review.py pr-review` / `review.py arch-review` prompt builders (see [skills/spec-workflow/SKILL.md](../skills/spec-workflow/SKILL.md) § "After implementation").
- **`Task tool` arrow**: `SKILL.md` can dispatch a fresh subagent via the `Task` tool. The three roles in `agents/` (`implementer`, `reviewer`, `architect`) are real `subagent_type` values when jig is installed as a plugin; outside the plugin they fall back to `general-purpose`.
- **Hook spine** intercepts at five Claude Code event types (SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, Stop) via sixteen hook scripts. Two are async log-only — never block, never inject (`telemetry`, `skill-trace`); one is async write-only, capturing in-flight decision stubs to a per-session scratch log without blocking or injecting (`decision-inflight`); eleven can inject `additionalContext` (`context-check`, `memory-scan`, `post-edit-verify`, `boundary-change-warn`, `entry-gate`, `task-capture`, `decision-capture`, `jig-semantic-index`, `claim-check`, `project-orient`, `git-freshness`); two can block tool calls with exit-code 2 (`spec-gate`, `secret-scan`). `entry-gate` (spec 098 / ADR-0044) nudges when an edit to project source happens outside a live working-lifecycle claim held by this checkout — the teeth-not-trust gate for lifecycle *entry*; fail-open, once-per-session. `git-freshness` (spec 103 / ADR-0048) is the SessionStart sibling that fires at *time-zero*: it fetches (timeout-guarded, best-effort) the branch's integration base and nudges to sync when `HEAD` is behind, before the agent forms a stale premise — the earlier tripwire that bug 001's command-time warning could not provide; fail-open, opt-out `JIG_GIT_FRESHNESS`. `project-orient` emits one self-labeled, bounded headline from scaffold/spec lifecycle artifacts at SessionStart and fails open; it never infers application state from a shallow source-tree listing. The three Stop hooks (`task-capture`, `decision-capture`, `claim-check`) are siblings — the same scan-and-surface pattern applied to a different signal: tasks, decisions, and spec/slice/ADR claims that don't resolve on disk. `decision-inflight` is the deterministic fast path feeding `decision-capture`'s triage.

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

In scaffold mode, `scaffold-init` copies the runtime machinery (`skills/`,
`agents/`, `hooks/scripts/`, and `templates/`) into the
user's `.claude/` directory under `jig-` prefixed names
(`.claude/skills/jig-<name>/`, `.claude/agents/jig-<name>.md`,
`.claude/hooks/scripts/jig-*.sh`), and generate/merge
`.claude/settings.json` to register the ten jig hooks against the
project-local script paths. SKILL.md path strings are rewritten from
`${CLAUDE_PLUGIN_ROOT}/skills/<name>/` to
`${CLAUDE_PROJECT_DIR}/.claude/skills/jig-<name>/`, and hook command
paths from `${CLAUDE_PLUGIN_ROOT}/hooks/scripts/` to
`${CLAUDE_PROJECT_DIR}/.claude/hooks/scripts/`, both at copy time.

The settings.json merge follows an **append-with-marker** strategy:
every jig-managed hook entry carries
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

### Codex plugin packaging
*Principle:* same workflow model, host-native materialization.

Codex plugin mode uses `.codex-plugin/plugin.json` and the same root
`hooks/hooks.json` default path that Codex documents for plugins. Codex
sets `PLUGIN_ROOT` for plugin hooks and keeps `CLAUDE_PLUGIN_ROOT`
compatible, so the canonical hook registrations remain unchanged for
Claude plugin mode and continue to work in Codex plugin mode.
Codex still treats plugin-bundled command hooks as non-managed hooks:
users must review and trust them through `/hooks` before jig's hook gates
run, and changed hook definitions require renewed trust.

`scripts/build_codex_plugin.py` produces the installable Codex plugin
directory plus a generated `.agents/plugins/marketplace.json` beside it.
It copies `.codex-plugin/`, `hooks/`, `templates/`, and `agents/` from
the shared source, then renders `skills/**/SKILL.md` into Codex wording
and plugin-root helper paths in the staged copy only. It also renders
TOML custom-agent templates from the canonical Markdown prompts. The
checked-in `skills/` and `agents/` trees stay the canonical source for
Claude plugin, Claude scaffold, Codex scaffold, and Codex plugin packaging.

Codex's current custom-agent discovery uses TOML files under project-local
or user-local `.codex/agents/`. Plugin packaging therefore does not add an
unsupported `agents` field to `.codex-plugin/plugin.json`; plugin users run
an explicit post-install helper to copy the generated `jig-*.toml` files into
their chosen Codex agents directory.

**Codex plugin agent-discovery spike.** The Codex manual documents
`.codex-plugin/plugin.json` with `skills`, describes plugin bundles as skills,
apps, and MCP servers, and documents custom agents as standalone TOML files
under `.codex/agents/` or `~/.codex/agents/`. Probing the Codex CLI through
`scripts/codex_agent_discovery_probe.py` with an isolated marketplace and
temporary `CODEX_HOME`, the installed plugin cache retained `agents/jig-*.toml`,
but `codex debug prompt-input` did not expose those plugin-bundled TOML files as
custom agents. The explicit `--install-codex-agents` helper remains the
supported plugin contract until official docs or the probe show plugin-native
discovery.

### Context economy (the "dumb zone")
*Principle:* see [product-vision.md § Design principles](product-vision.md#design-principles) (#2).
*Mechanics:* the `jig-context-check` hook warns at session start when fill approaches the ~40% threshold, and nudges again on in-session growth as context crosses configurable bands (40/60/80%, plus a higher active-compaction band). Skills use progressive disclosure — body loads only on trigger; supporting files load only when referenced.

### Three subagents, no more
*Principle:* see [product-vision.md § Design principles](product-vision.md#design-principles) (#3) — subagents are defined by what context they need isolated from, not by job title.

*Roster:*
- `implementer`: TDD discipline, writes deliverables
- `reviewer`: read-only, fresh context per review. Fires once per review pass under the multi-perspective flow — always compliance + craft (`pr-review`) + reconciliation, plus the frontmatter-gated passes: arch (`arch_review: true`), code-health (`code_health_review: true`), design-review (`design_review: true`, REVIEWED stage), and frame-critique (`frame_review: true`, the pre-implementation READY_FOR_REVIEW gate). Reused as the agent shape for every pass — no per-pass `pr-reviewer` / `arch-reviewer` agent. The verdicts are durable evidence artifacts that gate the next transition.
- `architect`: rare, ADR-style output

All three are reachable as real `subagent_type` values when jig is installed as
a Claude Code plugin (the bundled `jig` marketplace, or any future public
install). When jig runs from source rather than an installed plugin, every
caller falls back to `subagent_type: "general-purpose"`. `review.py
subagent-type` lets SKILL.md's bash recipe pick the real `reviewer`
deterministically when installed and degrade to `general-purpose` otherwise.

### Later structural decisions

The decisions above are the original load-bearing spine. The architecture has
grown several more since — the review-evidence gate (review verdicts are durable
artifacts that gate the REVIEWED / RECONCILED / DONE transitions), the shared
lifecycle-family spine behind spec-workflow / bug-fix / refactor, the attest-only
boundary to an external eval, and the scaffolded security floor. The
[ADR index](decisions/) is the canonical, current record of these; they are not
re-derived here.

### Autonomy governance plane (spec 106 / ADR-0051)

`scaffold-init` scaffolds the *scaffoldable half* of an out-of-band governance
firewall and a checkable autonomy precondition. New surfaces:

- **Scaffold output** (written by `_write_governance_plane`, dual-wired into
  `scaffold()` and `copy_machinery` like `_write_gitignore_managed_blocks`): a
  root `CODEOWNERS`, `.github/workflows/jig-governance.yml` (a `pull_request` job
  that *flags* any diff touching a protected path so owner review is required),
  and `<docs>/governance.md` (the branch-protection arming checklist). The
  scaffolded material states plainly that these files are **inert until branch
  protection is armed** — scaffold-init writes files, not the server-side
  branch-protection settings that make them enforce.
- **`governance.PROTECTED_PATHS`** is the single source of truth for the
  protected-glob set (it includes `.github/workflows/**` and `CODEOWNERS` itself,
  so the self-reference holds by construction). It is mirrored into
  `scaffold.json.protected_paths` by `_scaffold_manifest` (a computed key, like
  `installed_tiers`).
- **Hook read contract:** `hooks/scripts/lib/protected_paths.py` reads
  `scaffold.json.protected_paths` and, via `jig-boundary-change-warn.sh` (its
  single owner — one hook, one merged JSON object per invocation), soft-nudges an
  in-boundary edit (`JIG_PROTECTED_PATHS` opt-out, independent of the contract
  nudge's `JIG_BOUNDARY_CHECK`). CI + branch protection enforce out-of-boundary;
  the hook only nudges in-boundary (ADR-0011 posture).
- **Identity/capability separation:** `governance.check_identity_separation`
  keys on merge *capability* (not identity name), is deterministic over
  supplied/attested inputs (jig does not observe GitHub merge permissions
  in-process), and fails safe (not-ready) when the capability signal is absent.
  The `governance.py identity-check` CLI is the cross-repo boundary the servo
  readiness gate (servo 023 / ADR-0029) subprocess-invokes: stdout `IdentityVerdict`
  JSON (`ready` authoritative), exit `0` ready / `3` not-ready / `2` usage.

## Module boundaries

Six top-level concerns, named in [product-vision.md § Core features](product-vision.md#core-features-prioritized) at the vision layer:

- `skills/` — auto-triggering LLM behaviors (one `SKILL.md` + supporting files per skill)
- `agents/` — three subagent definitions (`implementer` / `reviewer` / `architect`)
- `hooks/` — deterministic spine (`hooks.json` + shell/Python hook helpers under `hooks/scripts/`)
- `templates/` — source templates that `scaffold-init` copies into new projects (`AGENTS.md`, `CLAUDE.md`, docs/, brief)
- skill helpers — Python helpers live **next to the skill that owns them** (`skills/<name>/*.py`), one per skill where the work is mechanical: `workflow.py`, `review.py`, `adr.py`, `tdd.py` (+ `quality.py`), `land.py`, `migrate.py`, `scaffold.py` (+ `stocktake.py`), `health.py` (code-health), `bug.py` (bug-fix), and `memory.py`. `scaffold-init` also owns `governance.py` (spec 106 / ADR-0051 — the autonomy governance plane: protected-path renderers + the identity/capability-separation check). Shared stdlib-only helpers live in `skills/_common/` (`parsing.py`, `review_evidence.py`, `lexicon.py`, `team_signal.py`, `use_cases.py`, `scaffold_state.py`, `atomic_io.py`)
- `scripts/` — top-level repo tooling, not skill helpers: `usage.py` (per-spec token/cost reporting), `verify_install.py`, `spec_lint.py`, `validate_manifests.py`, `skill_routing.py` (skill-routing eval), `build_release_zip.py`, `build_codex_plugin.py`, the `*_contract.py` builders, and `run_tests.py`
- `.claude-plugin/` — Claude plugin manifest (`plugin.json`) + marketplace descriptor (`marketplace.json`)
- `.codex-plugin/` — Codex plugin manifest (`plugin.json`)
- `scripts/build_codex_plugin.py` — produces Codex plugin package output plus its generated marketplace descriptor

The host adapter boundary sits inside the scaffold/runtime-rendering
concern: shared helper logic stays source-centralized, while host
renderers own path rewrites, primer choice, agent format, hook
registration, and hook protocol translation.
`skills/scaffold-init/scaffold.py` currently exposes this boundary as a
host-neutral `HostRenderer` interface plus concrete renderers for Claude
(`ClaudeScaffoldRenderer`) and Codex (`CodexScaffoldRenderer`). Claude
scaffold mode writes `AGENTS.md`, `CLAUDE.md`, `.claude/skills/`,
`.claude/agents/`, `.claude/hooks/scripts/`, `.claude/templates/`, and
`.claude/settings.json`. Codex scaffold mode writes `AGENTS.md`,
`.codex/skills/`, `.codex/agents/*.toml`, `.codex/hooks/scripts/`,
`.codex/templates/`, and `.codex/hooks.json` without producing Claude-only
files. **Both** scaffold hosts copy `templates/`: it is runtime support for
scaffolded helpers whose source fallback resolves template paths relative to
the materialized jig runtime (`parents[2]/templates/` — `decisions.py`,
`adr.py`, `migrate.py seed-decisions`, `workflow.py`'s slice-template render,
and `memory.py`'s people.md bootstrap all read it there). Codex
has copied templates since its adapter shipped, because its rewrite table
redirects `${CLAUDE_PLUGIN_ROOT}/templates/` into `.codex/templates/`; the
Claude side copies them too, which is what makes record-seeding work in a
scaffolded project with no plugin root. Codex also installs
non-discoverable unprefixed helper aliases under `.codex/skills/<name>/`
without `SKILL.md`; these preserve existing peer-helper imports such as
`skills/scaffold-init/scaffold.py` without registering duplicate skills.
Codex agent files are generated TOML custom-agent definitions with the
closest supported `sandbox_mode` for each role; the canonical source prompts
remain the Markdown files in `agents/`.

**Codex role capability dogfood.** The generated role files use this
mapping: `jig-implementer` -> `workspace-write`, `jig-reviewer` ->
`read-only`, and `jig-architect` -> `read-only`. The Codex CLI
validates those sandbox modes through `scripts/codex_role_capability_probe.py`:
the documented `:read-only` permissions profile blocks a scratch-project write
with `PermissionError: [Errno 1] Operation not permitted`, while `:workspace`
allows the same write inside the scratch workspace. Codex custom agents are
spawned only when explicitly requested and inspected through `/agent`;
`codex debug prompt-input` does not currently expose project custom-agent
entries, so noninteractive review automation should keep using generated
`review.py` prompts with a read-only runner unless the user is intentionally
dogfooding an interactive `jig-reviewer` custom-agent thread.

## Managed-File Metadata Policy

Scaffolded files are tracked with a **manifest-only** default: `scaffold.json`
records each managed file's relative path, source template/path, jig version,
host renderer, and `sha256` content hash. This keeps large prompt/prose files
such as `AGENTS.md`, `CLAUDE.md`, `docs/**`, skill `SKILL.md` bodies, and
agent prompts readable for LLMs instead of adding noisy per-file metadata
banners.

Inline markers are reserved for native host merge safety when the host file is
itself a structured merge surface. Today that means Claude hook entries inside
`.claude/settings.json` carry `metadata: {managed_by_jig: true}` so jig can
replace its own hook registrations without clobbering user-owned hooks. The
file-level source/hash record for `.claude/settings.json` still lives in
`scaffold.json`. Codex hook registration is generated as a whole
`.codex/hooks.json` file using Codex's native top-level `hooks` schema;
scaffold treats generated jig command paths under
`.codex/hooks/scripts/jig-*.sh` as the overwrite-safety marker and refuses
to overwrite an existing unrecognized Codex hook config unless the user passes
`--force`.

On a force re-run, scaffold checks manifest hashes before writing. Untouched
managed files may be regenerated; edited managed files cause a clear refusal
so the user can move or merge their change first. Missing managed files may be
regenerated. `scaffold.json` is the completion sentinel and manifest root, so
it is not self-hashed.

Interface contracts between the other modules are deliberately deferred
— today's coupling is read-only and one-directional (skills read
templates; helpers read specs; hooks read events; nothing writes across
the module boundary). Will tighten when the first bidirectional case
appears.

## Data model

Jig is a workflow layer, not a data application (per [product-vision.md](product-vision.md) non-goals). Relevant on-disk state is small:

- `.jig/scaffold.json` — install manifest: which tiers chosen, when, by which jig version
- `.jig/semantic-index.json` — project-local semantic-index opt-in state: auto-attach permission, provider preference, allowed overlays, and worktree policy
- `.jig/semantic-index-events.jsonl` — content-free local activation telemetry written by the semantic-index helper; ignored by git alongside `.jig/semantic-index-claude-hook.json`, the Claude hook's one-time recommendation rate-limit file
- `.claude/skill-usage.jsonl` — append-only log written by `jig-telemetry.sh` (Task spawns; `event: task_spawned`, with optional `phase`/`spec`/`slice`) and `jig-skill-trace.sh` (Skill invocations; `event: skill_invoked`); read via [docs/skill-routing-verification.md](skill-routing-verification.md). Histogram consumer is `workflow.py routing-stats`
- `docs/specs/**/spec.md` — the only project-level state jig owns; everything else lives in the dev's repo, owned by the dev

## Contract surfaces

<!-- elicited: 2026-05-15 / status: skipped -->

_Skipped: jig does not currently expose schema-shaped external interfaces. It is a dual-host plugin/scaffold package — the external surfaces are host plugin manifests, skill frontmatter/bodies consumed by Claude Code or Codex routers, Codex custom-agent TOML, hook configuration files, and CLI argparse interfaces on the `.py` helpers consumed by humans + scripts. None warrants an OpenAPI / JSON Schema / AsyncAPI / `.proto` / GraphQL SDL artifact. If jig later grows an HTTP / events / RPC surface (e.g. a telemetry sink endpoint, a remote-spec-status query API), this section gets filled per the `/jig:contracts` skill's per-surface recommendation table._

<!-- The `status: skipped` marker plus the no-bullet body above are load-bearing: together they signal "no surfaces to check" to the independent-review reviewer prompt's conditional contract-surface detector, keeping it quiet on jig's own slice reviews. -->

## Open questions

- `SubagentStart` hook event: documented in changelog (v2.0.43) but absent from official plugin docs. Deferred — see `docs/refinement-todo.md`.
- Hook strictness profiles (`SCAFFOLD_HOOK_PROFILE`): deferred — unread env var is worse than no env var.
