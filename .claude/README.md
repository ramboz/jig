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

## Repo decision: develop jig against the in-repo machinery, not the plugin

When you work *on jig*, the installed jig **plugin** is a stale marketplace
snapshot of the very code you're editing — so this repo deliberately runs the
in-repo machinery (this adapter) instead. That is a repo-level decision, not a
per-developer preference, so it lives in the **committed** `settings.json`:

```json
{ "enabledPlugins": { "jig@jig": false } }
```

This also resolves a collision: the adapter and a locally-installed plugin both
register the same hooks, and Claude Code does not dedupe hooks across sources —
running both would fire every hook **twice** (doubled SessionStart context
injection, etc.) and surface skills twice. Disabling the plugin here is a full
deactivation (skills, hooks, and agents) for this project.

Notes:
- **Harmless everywhere else it lands.** For a contributor who never installed
  the plugin — and in cloud sessions, where the `jig` marketplace isn't
  installed at all — the entry has nothing to match and is a no-op.
- **Still overridable per-machine.** Settings precedence is
  `Managed > CLI > Local > Project > User`. This committed entry (Project) beats
  a user-scope install (User), but a developer who *wants* the plugin on for
  this repo can flip it back in their own `.claude/settings.local.json`
  (Local), which is gitignored.

Everywhere *else* (other repos), keep using the plugin normally, or adopt jig
via `scaffold-init` (which writes its own `.claude/skills/jig-*` copies).

> Note: this adapter is specific to the jig source repo. Regular jig projects
> get their `.claude/` from `scaffold-init` instead.
