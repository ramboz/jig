# Research: 12-Factor Agents and Operational Principles

> Reference notes from the design phase. Pull into context only when relevant.

## The core insight

From Dex Horthy's 12-Factor Agents talk and writeup:

> Most successful AI products aren't purely agentic. They combine deterministic code with strategically placed LLM decision points.

This is the **deepest validation of our hook + skill architecture**:

- **Hooks are the deterministic spine** — gates that don't require judgment.
- **Skills are the LLM layer** — where reasoning lives.

Horthy's analysis of 100+ founders/CTOs building production agents found that the top 1% mostly **roll their own stack** — they don't depend on agent frameworks. They use LLM steps sprinkled into traditional software at the right points.

## The 12 factors (condensed)

1. **Natural language → tool calls.** Don't try to make the LLM do everything; convert intent to structured operations.
2. **Own your prompts.** Don't rely on framework defaults you can't see.
3. **Own your context window.** This is the most important. (See "dumb zone" below.)
4. **Tools are structured outputs.** Every tool call is a typed contract.
5. **Unify execution state and business state.** Don't have separate "agent state" and "app state."
6. **Launch / pause / resume with simple APIs.** Agents are interruptible processes.
7. **Contact humans with tool calls.** Human-in-the-loop is a structured operation, not a hack.
8. **Own your control flow.** Don't let the framework decide what runs when.
9. **Compact errors into context window.** Don't dump raw stack traces; summarize.
10. **Small, focused agents.** This is why we have 3 subagents, not 30.
11. **Trigger from anywhere, meet users where they are.** Hooks, CLI, webhooks — multiple entry points.
12. **Make your agent a stateless reducer.** Same inputs → same outputs (modulo LLM stochasticity).

## The "dumb zone" — context economics

The most actionable single insight from the research:

- Context windows aren't storage — they're **attention budgets**.
- Above ~40% context fill, model recall degrades and reasoning falters.
- "Lost in the middle" effect: LLMs perform best when relevant info is at the start or end.
- **The more tools an agent has, the dumber it gets.** Every tool description consumes tokens.

This validates several of our design choices:

- 8-12 skills (not 100+) — keep the available-skill description budget under control
- Progressive disclosure in skills — only load body when triggered, only load supporting files when needed
- Subagents as filters — they consume verbose work and return distilled summaries, preserving parent context
- Aggressive deferral in the wizard — empty sections marked "deferred" rather than filled with plausible-but-fictional content

Practical guidance from Anthropic and Manus AI: **keep under 10 MCPs and under 80 active tools.**

## Owning the control flow

This is what makes "auto-trigger" different from "automatic." We're not relinquishing control flow to the LLM — we're encoding the right triggers in deterministic places (hooks, skill descriptions) so the right thing happens at the right time without the user manually orchestrating.

Pattern in our scaffold:

- **Deterministic gates** (hooks) enforce "this MUST happen."
- **Probabilistic triggers** (skill descriptions) handle "fire when relevant."
- **Explicit invocations** (slash commands) reserved for things the user wants to control timing on (`disable-model-invocation: true`).

The skill pack is the control flow, made legible.

## Operational patterns we adopt

### Compact errors

PostToolUseFailure hook that captures the error, summarizes it, returns useful context to Claude. Not the raw stack trace — a 1-3 sentence summary of what went wrong and likely cause.

### Resumable workflows

Spec slice state lives in `docs/specs/NNN/spec.md`. Implementation state in `.claude/scaffold.json`. A session crash or restart should resume cleanly because state is on disk, not in conversation history.

### Human approval points

Specific operations require explicit human approval, marked with `disable-model-invocation: true`:

- Conventions changes (project-wide)
- ADR acceptance (architectural decisions)
- Phase transitions that flip scaffolding from Draft → Stable
- Anything that touches production infrastructure

### Telemetry

Every interesting event logged to `.claude/` files (gitignored). Skill invocations, hook firings, review verdicts. Two-week feedback loop catches misbehaving descriptions and overly noisy hooks.

## Why this matters for the build

The 12-factor framing is the answer to "why does this scaffold work where ECC doesn't?"

ECC tried to be **everything**. We're trying to be a **focused, opinionated harness** with clear separation between the deterministic layer (hooks, contracts, file state) and the probabilistic layer (skills, agents, LLM reasoning). The deterministic layer makes the probabilistic layer reliable.

## Source signals

- 12-Factor Agents talk (Horthy): <https://www.youtube.com/watch?v=2yi4mAN3CtE>
- 12-Factor writeup: <https://paddo.dev/blog/12-factor-agents/>
- Original GitHub repo: <https://github.com/humanlayer/12-factor-agents>
- Context engineering for agents (Manus AI)
