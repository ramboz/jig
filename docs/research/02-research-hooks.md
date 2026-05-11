# Research: Hooks — the Deterministic Spine

> Reference notes from the design phase. Pull into context only when relevant.

## Mental model

Hooks fire **deterministically**; skills are **probabilistic**. Combine them:

- Skills carry the workflows and reasoning.
- Hooks enforce gates that don't require judgment.

If you need something to **always happen**, it's a hook. If you need something to happen **when relevant**, it's a skill.

## Hook events we use (Claude Code v2.1+)

| Event | Fires | Can block? | Notes |
|---|---|---|---|
| `SessionStart` | startup, resume, clear, compact | no | Inject context, run setup. Re-inject critical context after compact. |
| `UserPromptSubmit` | when user submits a prompt, before Claude processes | yes (via `additionalContext`) | Validate or enrich prompts. |
| `PreToolUse` | before any tool execution | **yes** (only blocking hook) | Security gates, file protection, mandatory review enforcement. Can also rewrite tool input silently. |
| `PostToolUse` | after tool success | no (can't undo) | Format, lint, validate, provide feedback. |
| `PostToolUseFailure` | after tool failure | no | Add context for Claude about the cause. |
| `Stop` | when Claude finishes responding | yes (force continue via exit 2) | Final checks, "verify before done" enforcement. |
| `SubagentStop` | when subagent finishes, before returning | yes | **Where the independent reviewer pattern fires.** |
| `PreCompact` / `PostCompact` | around context compaction | no | Save/restore state. |

## Configuration

Hooks live in `hooks/hooks.json` (project) or `~/.claude/hooks/hooks.json` (user). Plugins **auto-load** `hooks/hooks.json` — do NOT also declare `hooks` in `plugin.json` or you get "Duplicate hooks file" errors (ECC hit this three times before adding a regression test).

Basic structure:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit|MultiEdit",
        "hooks": [
          {
            "type": "command",
            "command": "/absolute/path/to/script.sh",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

Hook handlers can also be `http` (POST to endpoint, get JSON back) — useful for centralized team policy. Same JSON contract as command hooks.

## Patterns we'll use

### 1. Spec gate before implementation

```json
{
  "matcher": "Write|Edit",
  "command": "/path/to/check-spec-status.sh"
}
```

PreToolUse hook on `Write|Edit` that checks if the file being touched has a corresponding spec status of `READY_FOR_IMPLEMENTATION`. If not, exit 2 with feedback: "No approved spec for this change. Run the spec workflow first."

### 2. Independent review enforcement

Stop hook that checks if recently-modified files have been reviewed (state tracked in `.claude/scaffold.json`) since their last edit. If not, exit 2 with feedback: "Spawn reviewer subagent before completing."

This is the deterministic enforcement layer that makes the probabilistic `independent-review` skill actually fire reliably.

### 3. Reconciliation gate

Stop hook that checks: implementation marked complete + tests green + reviewer pass + reconciliation done? Block completion if reconciliation hasn't happened.

### 4. Contract validation

PostToolUse on contract / schema / type files. Runs the schema validator. If contract changes, hook surfaces "this is a breaking change — update callers or version the contract."

### 5. Skill usage telemetry

PreToolUse on Task tool logs invocations to `.claude/skill-usage.jsonl`. Two-week feedback loop.

### 6. Context budget warning

SessionStart hook that warns if too many MCPs are enabled. Research finding: above 40% context fill is the "dumb zone" — keep under 10 MCPs and 80 active tools.

## Hook strictness profiles

Same hooks, three enforcement levels (borrowed from ECC):

- `minimal` — telemetry only, no blocking
- `standard` — blocks on spec gates and reconciliation; warns on contract changes
- `strict` — blocks on everything including style/lint failures

Controlled via env var: `SCAFFOLD_HOOK_PROFILE=standard`. Wizard picks default based on team maturity signals (existing CI? team size? answers to a few wizard questions?).

## Gotchas

- **Hooks run in parallel, not sequentially.** Order is non-deterministic. Don't have two hooks modify the same input.
- **Use absolute paths.** `$HOME` and `~` cause failures. `$CLAUDE_PROJECT_DIR` is available.
- **Exit code 2 = block with feedback.** Other non-zero codes are errors that don't block but cause noise.
- **PreToolUse can deny even in `--dangerously-skip-permissions` mode.** This is the "rules users can't bypass" knob.
- **MCP tools use different naming:** `mcp__<server>__<tool>`. Regex matcher for "all tools from a server": `mcp__github__.*`.
- **The `if` field accepts permission-rule patterns:** `"Bash(git *)"`, `"Edit(*.ts)"`. Use declarative filtering instead of writing shell logic.

## Communication via stdin/stdout

Hook receives JSON on stdin:

```json
{
  "session_id": "abc123",
  "hook_event_name": "PostToolUse",
  "tool_name": "Write",
  "tool_input": {"file_path": "/path", "content": "..."},
  "tool_response": {"filePath": "/path", "success": true}
}
```

Hook writes to stdout (for JSON output) or stderr (for messages to Claude / debug log).

For blocking with feedback:

```bash
echo "Reason for blocking" >&2
exit 2
```

For adding context without blocking:

```bash
jq -n --arg ctx "Useful context" '{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": $ctx
  }
}'
exit 0
```

For modifying tool input (v2.0.10+):

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "updatedInput": {"command": "modified-command"}
  }
}
```

## Why hooks matter for our north star

The product goal is **intuitive automated triggering at the right moments**. Skills handle "when the user describes work that looks like X, fire skill X." But skills can't enforce "this MUST happen before completion" because they're probabilistic. Hooks fill that gap.

Pattern: every workflow we want enforced has both a skill (carries the reasoning, auto-triggers on relevant prompts) AND a hook (deterministic gate that blocks if the skill was skipped or the work isn't done).

Source signals:

- Official docs: <https://code.claude.com/docs/en/hooks-guide>
- Disler's hook mastery repo: <https://github.com/disler/claude-code-hooks-mastery>
- ClaudeLog hook reference: <https://claudelog.com/mechanics/hooks/>
