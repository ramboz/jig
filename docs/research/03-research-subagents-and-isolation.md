# Research: Subagents and Context Isolation

> Reference notes from the design phase. Pull into context only when relevant.

## The critical caveat (read first)

**Claude Code subagents do not give you true context isolation for independent review.** The Task tool passes parent conversation context to spawned subagents. Open Anthropic GitHub issue #20304 explicitly requests an `isolated: true` parameter because this gap makes adversarial review patterns impossible.

> "When a human sees '5 agents reviewed this and agreed,' they assume 5 independent checks occurred. Without isolation, they got 1 check repeated 5 times — but paid for 5 and trusted the result as if it were 5."

What subagents actually give you:

- **Output isolation:** parent only sees the subagent's final result, not its intermediate noise. ✅ Useful for research, verbose tasks.
- **Input isolation:** subagent does NOT see parent's reasoning history. ❌ Not currently available out of the box.

## What's actually available

| Mechanism | Output isolation | Input isolation | Use case |
|---|---|---|---|
| Standard subagent via Task | yes | no | Research, verbose work, "go find X" |
| Fork mode (`CLAUDE_CODE_FORK_SUBAGENT=1`) | yes | partial (cache reuse, same prompt) | Optimized for repeated similar tasks |
| Agent Teams (experimental) | yes | yes | Closest to true isolation, but experimental |
| Filesystem-based subagents (`.claude/agents/*.md`) | yes | configurable via system prompt | The pragmatic workaround we'll use |

## Our pattern: pragmatic context isolation

For the independent reviewer pattern, the practitioner workaround is:

1. **Implementer writes deliverable to disk** (code + spec status + acceptance criteria).
2. **Reviewer is a filesystem-based subagent** defined in `.claude/agents/reviewer.md`.
3. **Reviewer's system prompt explicitly forbids referring to prior context:** "You are seeing this work for the first time. You have not previously discussed this task. Evaluate the code itself, not any reasoning about it."
4. **Reviewer reads only:** the spec, the deliverable, the acceptance criteria. Not the implementation chat history.
5. **Reviewer is invoked via Task with a fresh prompt** that gives it only the file paths to read.

This is imperfect (the reviewer technically has access to parent context), but it works well in practice if system prompts are sharp. cc-sdd uses this exact pattern.

## Sub-agent count for our skill pack

After research, our v1 count:

1. **`implementer`** — fresh context per spec slice. TDD discipline. Narrow tool access. Writes deliverable + tests + status file.
2. **`reviewer`** — fresh context per review. Sees only spec + deliverable + acceptance criteria. System prompt forbids referencing prior context.
3. **`architect`** — rare invocation, only for ADR-worthy decisions. Sees question + relevant code regions. Outputs ADR-style proposals with alternatives.

Optional 4th: **`researcher`** for spec discovery — only used in the wizard's discovery phase. Returns synthesized findings, not raw research dumps.

That's 4 max, often 2 in practice. **Defined as markdown files in `.claude/agents/`** with sharp system prompts and tool restrictions.

## Lessons from Anthropic's multi-agent system

Source: <https://www.anthropic.com/engineering/multi-agent-research-system>

### Most important findings

1. **The win is parallel context windows, not better instruction-following.** Anthropic's BrowseComp evaluation: token usage explained 80% of performance variance. Multi-agent works because each subagent has its own 200K window.

2. **Effort-scaling rules belong in the prompt.** Anthropic explicitly embeds: "1 agent for simple fact-finding, 2-4 subagents for direct comparisons, 10+ for complex research." Without explicit rules, the orchestrator over-spawns ("50 subagents for a simple question").

3. **Coding tasks are *less* parallelizable than research.** Direct quote: "most coding tasks involve fewer truly parallelizable tasks than research, and LLM agents are not yet great at coordinating and delegating to other agents in real time." For our skill pack: **lean conservative on parallelism in coding workflows.**

4. **Subagents are intelligent filters.** They consume verbose tool output and return distilled summaries. The lead agent never sees the noise.

### Failure modes Anthropic hit

- Spawning excessive subagents for simple queries
- Endless loops searching for sources that don't exist
- Constant status-update interruptions between agents
- Redundant searches across subagents
- Failing to coordinate (each thinking the other is handling X)

### Fixes

- Strict logic in lead agent prompts about when enough info has been gathered
- Explicit delegation patterns
- Structured reasoning via extended thinking BEFORE action
- Effort-scaling rules baked into the prompt

## The "dumb zone"

From Dex Horthy's 12-Factor Agents talk (validated by Manus and Anthropic research):

- Context windows aren't storage — they're **attention budgets**.
- Above ~40% context fill, model recall degrades and reasoning falters.
- "Lost in the middle" effect: LLMs perform best when relevant info is at the beginning or end of context.
- The more tools an agent has, the dumber it gets (each tool description consumes tokens).

**Implication for our design:** subagent invocations should preserve the parent's context economy. A reviewer subagent that returns a brief verdict + diff is doing its job; one that returns a 5K-token review essay is not.

## Subagent definition format

`.claude/agents/reviewer.md`:

```markdown
---
name: reviewer
description: Performs independent review of implemented work against spec
tools: ["Read", "Grep", "Glob"]
model: opus
---

You are an independent reviewer. You are seeing this work for the first time.
You have not previously discussed this task with anyone.

Your job:
1. Read the spec at the path provided.
2. Read the deliverable at the path provided.
3. Read the acceptance criteria.
4. Evaluate whether the deliverable meets the spec, independently.

Do NOT:
- Refer to any prior reasoning or discussion about this task.
- Assume context that is not in the files you've been pointed at.
- Soften feedback to match what you think the implementer intended.

Output format:
- VERDICT: pass | fail | needs-changes
- REASONING: <2-4 sentences>
- SPECIFIC ISSUES: <bulleted list, file:line references where applicable>
```

Note the narrow tool list — `Read`, `Grep`, `Glob`. No `Write`, no `Edit`. Reviewer can't modify code, only report.

## Source signals

- Official subagent docs: <https://code.claude.com/docs/en/sub-agents>
- Anthropic multi-agent research writeup: <https://www.anthropic.com/engineering/multi-agent-research-system>
- Context isolation issue: <https://github.com/anthropics/claude-code/issues/20304>
- 12-Factor Agents (Horthy): <https://paddo.dev/blog/12-factor-agents/>
