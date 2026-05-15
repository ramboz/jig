# Refresh jig's local plugin install

Single-page runbook for the dev-loop friction described in
[CONTRIBUTING.md "Refreshing the install after edits"](../CONTRIBUTING.md)
and [docs/inbox.md, 2026-05-13 install-snapshot-lag entry](../docs/inbox.md).

## TL;DR

**The Desktop plugin manager installs jig as a snapshot copy, not a
path-link.** When you edit jig's source, the installed copy stays
stale until you refresh it. To see your edits in a `subagent_type:
"reviewer"` Task call, refresh the install AND start a fresh Claude
Code session.

## When to refresh

| You changed... | Need a refresh? |
|---|---|
| `agents/*.md` (reviewer / implementer / architect definitions) | **Yes.** Subagent tool restrictions / persistent rules live here. |
| `skills/*/SKILL.md` (skill auto-trigger descriptions, instructions) | **Yes** if you want auto-trigger or the rewritten body to take effect. |
| `skills/*/*.py` (helper code — `review.py`, `workflow.py`, etc.) | **Yes** if you want the installed plugin's hooks / SKILL.md to use the new code. Helpers invoked via direct `python3` calls from your worktree use the worktree copy regardless. |
| Top-level `scripts/`, `.claude-plugin/marketplace.json`, `docs/` | **No.** These aren't loaded by the Claude Code plugin runtime; your edits take effect immediately when re-run from the worktree. |
| `templates/` (scaffold-init source templates) | **Yes** if you want a future `scaffold-init` invocation to use the new templates — though typically you just re-run scaffold-init directly via `python3` from the worktree. |
| `docs/specs/`, `docs/architecture.md`, `CLAUDE.md` | **No.** These are read-only context, not plugin-loaded code. |

Rule of thumb: if it lives under `skills/`, `agents/`, or `hooks/` AND
you want the installed plugin's runtime to use it, refresh.

## How to refresh

### From a Claude Code session (recommended)

```text
/plugin uninstall jig@jig
/plugin install jig@jig
```

Then **exit the session and start a new one.** The available-agents
list (what `subagent_type: "reviewer"` resolves against) is fixed at
session start; an already-running session won't see the refreshed
subagent definitions even after re-install. `/reload-plugins` reloads
skill content but does NOT make new subagent types reachable in the
current session.

### From the graphical plugin manager

1. **Settings → Plugins → jig → Uninstall**
2. **+ button → Plugins → Add plugin → select jig from the local
   marketplace**
3. Exit and restart Claude Code.

This regenerates the install path
(`~/.claude/plugins/marketplaces/local-desktop-app-uploads/jig/`) from
your current worktree state.

## How to verify the refresh took effect

```bash
# Compare a known-changed file's content
diff <(grep -c subagent-type skills/independent-review/review.py) \
     <(grep -c subagent-type ~/.claude/plugins/marketplaces/local-desktop-app-uploads/jig/skills/independent-review/review.py)
```

A `0` difference (after `diff` returns nothing) means the install
matches the worktree.

Alternatively, run the headless verify:

```bash
python3 scripts/verify_install.py
```

Four `PASS` lines + `summary: 4/4 passed` confirms the install
footprint is on disk. Note: this does NOT verify the install is
current — only that the four canonical files exist. For currency,
use the `diff` check above.

## Why this is annoying, and what would fix it

The fundamental issue is that the Desktop app's plugin install is a
copy, not a symlink. This is by design for distribution (the
marketplace doesn't have to trust live paths), but it's friction for
dev. See [docs/inbox.md, 2026-05-13 install-snapshot-lag entry](../docs/inbox.md)
for proposed fixes — they're not implemented yet.

If you find yourself running this loop often, consider:

1. **Running the helper directly from the worktree** (e.g.,
   `python3 skills/spec-workflow/workflow.py transition ...`) for any
   workflow that doesn't need the runtime plugin context. Most jig
   work falls in this category.
2. **Reserving the install refresh for reviewer-subagent dogfood
   sessions specifically** — i.e., when you need to spawn `Task` with
   `subagent_type: "reviewer"` and have it read your latest changes.
   For everything else, the install is just there for
   `subagent_type` resolution.
