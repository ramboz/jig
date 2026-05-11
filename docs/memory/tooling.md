# Tooling

> Idiosyncratic tool choices and the reasoning behind them.
> Why we use X instead of Y, even when Y is more common.
>
> Update via `/jig:memory-sync`.

## Python 3 for hook scripts (not jq, not Node, not bash-only)

**Why not jq:** Not installed by default on macOS. Homebrew dependency is a non-starter for hooks that must work on fresh installs.
**Why not Node:** Startup overhead for short-lived scripts. Python 3 is faster for small JSON tasks.
**Why not bash-only:** JSON parsing in pure bash is error-prone and unreadable. Python 3 is clearer and more maintainable.
**Why Python 3:** Available everywhere (macOS ships with it, Linux has it, Homebrew users have it). `import json` is stdlib.

## Claude Code plugin format (not commands directory)

We use the plugin format (`.claude-plugin/plugin.json` + `skills/*/SKILL.md`) rather than the older `.claude/commands/` directory.
**Why:** Skills add auto-triggering capability on top of slash commands. Everything as a skill, not a command.

## Inline Python in bash scripts (heredoc pattern)

```bash
python3 - <<'EOF'
...
EOF
```

Not a separate `.py` file. Keeps the hook self-contained in one file.
**Why not a separate .py:** Avoids file path juggling. One script file = one hook.
