# Research: Claude Code Skills and Auto-Triggering

> Reference notes from the design phase. Pull into context only when relevant.

## Core mechanic

Skills are **auto-discovered, not always-on**. Claude reads the descriptions of every skill it can see (in `.claude/skills/` or `~/.claude/skills/`), compares the user's message to those descriptions, and pulls in the matching skill's full content. If nothing matches, no skill loads.

This means **the description does most of the work**. It's the only thing Claude has to decide whether the skill applies. A vague description ("Helps with tests") rarely fires. A specific one ("Runs the project's pytest suite when the user asks to run, check, or verify tests") fires reliably.

## Description template that works

```text
description: <verb-led summary>. Use when <specific triggers — file patterns,
user phrases, tool events>. Do not use for <common false positives>.
```

Examples:

- **Good:** "Extract text and tables from PDF files, fill forms, merge documents. Use when working with PDF files or when the user mentions PDFs, forms, or document extraction."
- **Good:** "Remove unused imports and sort the rest. Use any time the user asks to clean imports, sort imports, or tidy imports in a file."
- **Bad:** "Helps with code"
- **Bad:** "For testing work"

The negative clause matters more than people realize. It's what stops `tdd-workflow` from triggering on "let me test something quickly."

## Five principles for our skill pack

1. **One skill, one job.** Mega-skills hurt triggering accuracy. The most common authoring mistake in the community is the "kitchen sink" skill that tries to handle commits, PRs, branch naming, and changelog updates all at once. Split aggressively.

2. **Progressive disclosure.** Skills load in stages: frontmatter scanned for triggering → SKILL.md body loaded → linked files loaded as needed. So "skill folders" with supporting files (`FORMS.md`, `REFERENCE.md`, scripts) outperform monolithic skills. Token economics matter — every loaded skill consumes context whether it helps or not.

3. **Frontmatter flags for invocation control:**
   - `disable-model-invocation: true` — skill only triggered explicitly. Use for actions with side effects (deploy, commit) where you don't want Claude deciding.
   - `user-invocable: false` — only Claude can invoke. Use for background knowledge / context that isn't a meaningful user action (e.g., "legacy-system-context").
   - Default: both can invoke.

4. **Skills and slash commands have merged.** As of late 2025/early 2026, custom commands are skills. `.claude/commands/deploy.md` and `.claude/skills/deploy/SKILL.md` both create `/deploy`. Skills add the auto-trigger capability on top. **Treat everything as a skill.**

5. **Each skill has a Gotchas section.** Highest-signal content. Accumulates failure points over time. The skill description tells Claude *when* to fire; the Gotchas section tells Claude *what tends to go wrong*. Worth reserving as a required heading in our skill template.

## What to put in SKILL.md body

- **Don't** state the obvious or restate what the model already knows. Focus on what pushes Claude out of its default behavior.
- **Don't** railroad with prescriptive step-by-step instructions. Give goals and constraints.
- **Do** include negative instructions ("Do not touch import side effects"). These are how you stop Claude from drifting back to defaults.
- **Do** include scripts and libraries so Claude composes rather than reconstructs boilerplate.
- **Do** embed `!command` for dynamic shell output (Claude runs it on invocation, model sees only the result).

## Testing skill descriptions

A practical test loop:

1. Write the description.
2. Read it out loud. Does it start with a verb and end with a clear trigger?
3. Open a fresh Claude Code session. Type the kind of thing you'd actually say (not "trigger my skill"). Watch whether it loads.
4. If it doesn't, the description is too vague — tighten with concrete triggers.
5. If it fires on unrelated things, the description is too broad — add a negative clause.

## Telemetry pattern

A PreToolUse hook on the Task tool that logs every skill invocation to `.claude/skill-usage.jsonl`:

```json
{"timestamp":"2026-05-11T...","skill":"spec-workflow","prompt_snippet":"..."}
```

After a week of real use, you can grep this log to find:

- Skills that never fire (description too vague — rewrite or delete)
- Skills that fire on irrelevant prompts (description too broad — add negative clause)
- Skills that fire together (might want to be one skill, or might need to be more clearly differentiated)

This is the **feedback loop** that prevents description-rot over time.

## Source signals

- Official docs: <https://code.claude.com/docs/en/skills>
- Anthropic skill authoring best practices: <https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices>
- Practitioner consensus from multiple 2026 guides: description is load-bearing; the description is a *trigger*, not a *summary*.
