# `.claude/` — cloud-session adapter for the jig repo

This directory makes jig's own machinery active in **Claude Code on the web /
cloud sessions**, where there is no interactive `/plugin install` step and no
plugin runtime. Everything here is committed so it travels with the fresh clone
and activates automatically (subject to the one-time workspace-trust prompt).

It is deliberately thin: it does **not** duplicate any skill, hook, or agent.
The jig repo keeps its canonical machinery at the repo root (`skills/`,
`hooks/`, `agents/`) because it *is* the plugin source. This adapter just points
Claude Code at that root layout.

## What's here

| Path | Role |
|---|---|
| `settings.json` | Registers the jig hooks against `${CLAUDE_PROJECT_DIR}/hooks/scripts/*.sh`, and a SessionStart step that exports `CLAUDE_PLUGIN_ROOT=${CLAUDE_PROJECT_DIR}` via `$CLAUDE_ENV_FILE`. |
| `skills/<name>` | Symlink → `../../skills/<name>` so project skill discovery finds each skill's `SKILL.md`. |
| `agents/<name>.md` | Symlink → `../../agents/<name>.md` so the read-only `reviewer` subagent (and `architect`/`implementer`) are reachable. |

## Why the `CLAUDE_PLUGIN_ROOT` shim

The hook scripts self-locate (via `BASH_SOURCE`) and resolve their helpers
against the repo root, so they need only `${CLAUDE_PROJECT_DIR}` — which Claude
Code always sets. The **skill recipes**, however, invoke helpers as
`python3 "${CLAUDE_PLUGIN_ROOT}/skills/<name>/<helper>.py"`, and
`${CLAUDE_PLUGIN_ROOT}` is *not* defined for settings.json-registered hooks. The
SessionStart step writes `CLAUDE_PLUGIN_ROOT=<repo root>` to `$CLAUDE_ENV_FILE`,
which the Bash shell then inherits. Because the jig repo's root layout *is* the
plugin layout, every `${CLAUDE_PLUGIN_ROOT}/skills/...` path resolves to the
live source — no recipe rewriting, no file duplication. It also satisfies
`independent-review`'s `detect_subagent_type()`, which upgrades the reviewer
subagent to the real read-only `reviewer` agent when
`${CLAUDE_PLUGIN_ROOT}/agents/reviewer.md` is present.

## The one rule for local development: disable the *plugin* for this project

This adapter and a locally-installed jig **plugin** both register the same
hooks. Claude Code does not dedupe hooks across sources, so running both means
every hook **fires twice** (doubled SessionStart context injection, etc.) and
skills appear twice. To avoid that collision, **disable the jig plugin for this
project when developing locally** — this adapter is a superset and runs against
your *live* edits, whereas the installed plugin is a stale marketplace snapshot.

Everywhere *else* (other repos), keep using the plugin normally, or adopt jig
via `scaffold-init` (which writes its own `.claude/skills/jig-*` copies).

> Note: this adapter is specific to the jig source repo. Regular jig projects
> get their `.claude/` from `scaffold-init` instead.
