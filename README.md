# jig

> A Claude Code and Codex workflow layer that scaffolds AI-native development practices into new projects.

**jig** (noun): a tool that guides other tools to work accurately and consistently.

## Why jig

Two years of AI-assisted coding leave the same scars on every non-trivial
project: LLMs refactor whole layers before anything works end-to-end, "done"
drifts because no acceptance criteria are written down, implementers grade
their own homework, and mega-packs burn the context budget before your work
loads. **jig encodes the workflow that prevents each one — so you don't
rediscover it session by session.**

→ **[The jig philosophy](docs/philosophy.md)** — the full why: the named
scars, how jig thinks, and the honest objections.

## What it does

jig installs a focused, opinionated workflow layer into your project:

- **Spec-driven development** — SPIDR-split vertical slices, each with its own
  Definition of Done.
- **Multi-perspective review** — a fresh, read-only reviewer checks every
  slice against its spec (compliance), plus a craft pass and an on-demand
  architecture pass.
- **Memory layer** — cross-session continuity via hot cache + deep storage +
  inbox.
- **Deterministic gates** — hooks enforce what *must* happen; skills carry
  judgment.

A fixed, opinionated set — **7 Tier 0 skills** at the floor and 8 more on by
default (Tier 1) — not a hundred-skill marketplace. For the full picture, see
[product-vision.md](docs/product-vision.md) (vision, target users, principles)
and [architecture.md](docs/architecture.md) (mechanics).

## Principles jig encodes

The convictions behind the mechanisms — each one wired into something concrete,
not left as advice:

- **The harness matters more than the model.** jig *is* a harness: the
  instructions an agent reads, the tools it can run, the feedback loops that
  correct it, the isolation boundaries that contain it. Swapping models won't
  close a workflow gap — the scaffold does.
- **Guardrails, not guidelines.** What *must* happen is enforced mechanically by
  hooks (secret scanning, spec gates, review-evidence gates); what takes
  *judgment* lives in skills. The line between a deterministic gate and an
  advisory nudge is drawn on purpose.
- **The context window is working memory, not a storage buffer.** Irrelevant
  context degrades reasoning, so jig keeps a lean hot cache, loads deeper docs
  on demand, and delegates file-heavy reading to subagents that return only a
  summary.
- **Designed to reduce token cost.** Beyond keeping context lean for *quality*,
  jig is built to keep token usage — and the bill — *down*: lean context,
  file-heavy reading delegated to subagents, tight output. It also measures its
  own spend rather than guessing at it.
- **Review is the bottleneck.** Agents produce faster than review capacity
  grows, so jig won't let implementers grade their own homework: a fresh,
  read-only reviewer checks every slice against its spec, and the verdicts are
  durable artifacts that gate the next state.
- **Specs and docs are code, and they ship in slices.** Specs, ADRs, and the
  memory layer are version-controlled and reconciled before a slice lands — so
  "done" never drifts, and work arrives as vertical slices instead of one big-bang
  mega-commit.

These are the outward-facing worldview; several are also load-bearing build
rules jig holds *itself* to, spec by spec — see
[product-vision § Design principles](docs/product-vision.md#design-principles)
for the operational detail.

Two more jig is building toward, honestly not yet landed: **one development
experience across AI tools** (a host-adapter layer beyond Claude Code — [spec
033](docs/specs/033-host-adapter-portability/spec.md)) and **coordination across
a multi-repo workspace** (a federation tier — [spec
034](docs/specs/034-federation-tier/spec.md)). Both are on the roadmap, not
shipped today.

## Start here

**New to jig?** Read the
**[adoption & readiness guide](docs/adoption-readiness.md)** first — who jig is
for, what your repo needs, and your first 30 minutes.

Then, in a Claude Code session at your project root:

```text
Set up this project for AI-native development.
```

(or the explicit `/jig:scaffold-init`). This copies jig's docs, skills, hooks,
and `settings.json` into your repo's `.claude/`, seeds a worked-example spec,
and runs a "scaffold complete and verified" check. Follow it with
`/jig:vision-elicitation` to set the vision every later slice is judged
against.

**Copy-paste prompts** live in the **[prompt cookbook](docs/prompts.md)**, in
the order you run them: scaffold the repo once, then repeat the idea-to-landed
loop for every feature.

### Install shapes

Two independent choices: **how you acquire the plugin**, and **where the
machinery lives** once it's installed. Full detail and how to choose in
[adoption-readiness § Choosing an install shape](docs/adoption-readiness.md#choosing-an-install-shape).

**1. Acquire the plugin** — puts the machinery under `${CLAUDE_PLUGIN_ROOT}`
and makes the `/jig:*` commands available:

| Source | How |
|---|---|
| **Marketplace** (Claude Code) | `/plugin marketplace add ramboz/jig` → `/plugin install jig@jig` |
| **Release zip** (Claude Desktop) | Download `jig-vX.Y.Z.zip` from the [latest release](https://github.com/ramboz/jig/releases/latest), then add it via Claude Desktop's plugin manager (**Settings → Plugins**). |

Running jig from a source checkout (for hacking on jig itself): see
[CONTRIBUTING § Local dev install](CONTRIBUTING.md#local-dev-install).

**2. Choose where the machinery lives** — `/jig:scaffold-init` runs the same
either way; the flag picks the shape (recorded as `scaffold_mode` in
`scaffold.json`):

| Shape | What lands in your repo | Command |
|---|---|---|
| **Own it** (default) | Docs **and** machinery (`skills/`, `agents/`, `hooks/`, `settings.json`) copied into `.claude/` — version-controlled and editable. | `/jig:scaffold-init` |
| **Central machinery** | Docs + `scaffold.json` only; machinery stays plugin-side and upgrades centrally. | `/jig:scaffold-init --plugin-only` |
| **Plugin only** (full manual) | Nothing — `/jig:*` skills and hooks come from the plugin centrally. For folks who already have their own setup and want to wire jig's workflow into it by hand. | _(skip step 2)_ |

When in doubt, scaffold and own it — that's jig's default posture
([product-vision § Design principle 7](docs/product-vision.md#design-principles)).

## Extension points

> **Bring your own depth; jig provides the floor.**

A few jig skills — `pr-review`, `arch-review`, `contracts` — ship as
lightweight baselines that **defer to a richer user-installed skill** in the
same category when one is present. The deferral is category-based, not
name-specific, so your own reviewer skill wins automatically, with no
configuration. jig stays opinionated about *workflow* and out of the way of
the *judgment skills you've already invested in*. Detail:
[product-vision § Design principles](docs/product-vision.md#design-principles).

## Codex Distribution

jig now supports four distribution modes from the same source tree:
**Claude scaffold**, **Claude plugin**, **Codex scaffold**, and **Codex plugin**.
For editable Codex project-local machinery, run:

```bash
python3 skills/scaffold-init/scaffold.py --host codex <your-project>
```

This produces `<your-project>/AGENTS.md`, `.codex/skills/jig-*/`,
`.codex/agents/jig-*.toml`, `.codex/hooks/scripts/jig-*.sh`, and
`.codex/hooks.json`. This is the Codex mode to use when you want the
workflow machinery editable in the project itself.

### Codex plugin (central install)

Build the Codex-native plugin package from the shared source tree:

```bash
python3 scripts/build_codex_plugin.py --output-dir dist/codex-plugin/plugins/jig
```

The builder writes `dist/codex-plugin/.agents/plugins/marketplace.json`
next to the plugin directory. Install that generated marketplace:

```bash
codex plugin marketplace add dist/codex-plugin
codex plugin add jig@jig
```

After `codex plugin add`, start or restart Codex and open `/hooks` in the
CLI. Codex requires non-managed command hooks, including plugin-bundled
hooks, to be reviewed and trusted before they run. Until you trust jig's
hook definitions, Codex can load the plugin skills but skips the hook gates;
after you rebuild or reinstall the plugin, revisit `/hooks` because trust is
recorded against the current hook definition hash.

The Codex plugin package includes `.codex-plugin/plugin.json`, rendered
Codex skill copies, `hooks/hooks.json`, hook scripts, templates, and the
canonical agent prompts plus generated TOML custom-agent templates.
Codex custom-agent discovery uses TOML agent files under
project-local or user-local `.codex/agents/`. Rechecked on 2026-06-05:
the official Codex manual still documents plugin manifests for skills and
plugin surfaces, not plugin-level custom agents, and local `codex-cli 0.133.0`
does not expose plugin-bundled `agents/jig-*.toml` files as custom agents
after an isolated plugin install. After installing the plugin, run the
explicit post-install step to copy jig's custom agents into the global Codex
agents directory. From the installed Codex plugin context, the helper is
addressed through the plugin root:

```bash
python3 "${PLUGIN_ROOT}/skills/scaffold-init/scaffold.py" --install-codex-agents
```

For a locally built package, the equivalent source-tree path is
`dist/codex-plugin/plugins/jig/skills/scaffold-init/scaffold.py`. The command
defaults to `~/.codex/agents`. Use `--codex-agents-dir <dir>` to target
another Codex agents directory, and `--force` only when replacing existing
user-owned `jig-*.toml` files is intentional.

To smoke-test the full generated Codex install contract locally, run:

```bash
python3 scripts/codex_install_smoke.py
```

The smoke command builds the same `codex-plugin/plugins/jig` layout in an
isolated temp workspace, validates the generated Codex package, runs the
custom-agent helper against a temp agents directory, and probes the Codex CLI
plugin surfaces when `codex` is available. It sets a temporary child
`CODEX_HOME` by default so the marketplace/plugin add probe does not touch your
real Codex config. For debugging, set `JIG_CODEX_SMOKE_CODEX_HOME=<dir>` or
pass `--codex-home <dir>`; set `JIG_CODEX_SMOKE_CODEX_BIN=<path>` or
`--codex-bin <path>` to choose a specific CLI. If Codex is not installed, the
live portion reports `UNAVAILABLE` while the static package and agent checks
still run.

To dogfood Codex role-agent capability semantics separately, run:

```bash
python3 scripts/codex_role_capability_probe.py
```

That probe validates the generated `jig-implementer`, `jig-reviewer`, and
`jig-architect` TOML files, confirms the intended `workspace-write` vs.
`read-only` posture, and probes local Codex sandbox/debug surfaces when
available. See [docs/codex-role-capability.md](docs/codex-role-capability.md)
for the interactive `/agent` dogfood prompt and noninteractive review fallback.

To re-check whether Codex has gained plugin-native custom-agent discovery, run:

```bash
python3 scripts/codex_agent_discovery_probe.py
```

The probe builds the same generated Codex plugin package, installs it through
an isolated marketplace and temporary `CODEX_HOME`, confirms the plugin cache
carries `agents/jig-*.toml`, and verifies whether Codex exposes those
plugin-bundled templates as custom agents without running the explicit helper.

### From source (contributors)

See [CONTRIBUTING.md](CONTRIBUTING.md) for the local-marketplace
workflow used during development.

## Getting started

Once installed, open a new project directory in Claude Code and say:
> "Set up this project for AI-native development"

The `scaffold-init` skill will run and produce the docs/ scaffolding.

## Repository structure (for contributors)

```
.claude-plugin/plugin.json       # Claude plugin manifest
.claude-plugin/marketplace.json  # Claude local dev marketplace descriptor
.codex-plugin/plugin.json        # Codex plugin manifest
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

Read [CONTRIBUTING.md](CONTRIBUTING.md) for the local install + verify flow,
then [docs/workflow.md](docs/workflow.md) for the spec lifecycle. **Every
change to jig starts with a spec.** PRs squash-merge with conventional-commit
titles (`feat(scope): …` / `fix(scope): …`); the `pr-title.yml` workflow
enforces the shape, and CONTRIBUTING § Releasing has the version-bump effect of
each prefix.

How jig compares against other AI-native playbooks — and where each known gap
is owned — lives in
[CONTRIBUTING § Comparison and gap response](CONTRIBUTING.md#comparison-and-gap-response).

## Status

Tier 0 and Tier 1 are complete — all 15 skills, 3 subagents, and the jig hooks
ship today, and jig is dogfooded on its own spec lifecycle. For live per-slice
state, see the **[status board](docs/specs/README.md)**.

**Supported today:** Claude Code and Codex in scaffold and plugin shapes from
the shared source tree. Codex role prompts are bundled as prompt source; TOML
custom-agent discovery remains a tracked follow-up in
[spec 033](docs/specs/033-host-adapter-portability/spec.md).
