# Research: Lessons from ECC (everything-claude-code)

> Reference notes from the design phase. Pull into context only when relevant.

## TL;DR

ECC is a kitchen sink built over 10+ months of daily use. **It's a catalog you graze from, not a system you adopt.** Our skill pack is a system — opinionated, small, composable, auto-triggered — with the catalog impulse held back for v2+ once we've earned the right to add surface area.

## Where ECC validates our design

### Skill pack > monolithic install

ECC's pain proves this. The README splits "minimal," "core," and "full" profiles and warns against mixing install paths. They have a doctor + repair + uninstall trio in their quickstart because people accidentally install it twice. When your scaffold has those tools front-and-center, the surface area has outgrown the cognitive budget.

Our 8-12 skills with tiered installs is the right correction.

### Auto-triggering > explicit invocation

ECC's default flow leans on explicit `/commands` (`/code-review`, `/build-fix`, `/security-scan`, etc.). This creates the cognitive load we explicitly want to avoid. Our instinct to flip this is correct.

### Small, focused subagents > role-titled sprawl

ECC has 48 agents, many near-duplicates (`go-reviewer`, `python-reviewer`, `typescript-reviewer`, `java-reviewer`, `kotlin-reviewer`, `rust-reviewer`, `cpp-reviewer`...). One generic `reviewer` skill with language-aware behavior would have served better. Validates our 3 subagents max.

### Generate project-tailored skills

ECC's `continuous-learning-v2` + `/skill-create` + `/evolve` pipeline is the same idea as our "generate skills from project context" — just retrofitted later. Building this in from day one (our wizard) is cleaner.

## What to steal

### 1. Iterative retrieval for subagents

ECC explicitly calls out "the context problem" with subagents and has a skill for progressive context refinement. This is the failure mode we worried about (subagents drowning in context). **Worth studying their implementation when we build our reviewer subagent.**

### 2. Hook runtime profiles

`ECC_HOOK_PROFILE=minimal|standard|strict` lets one install scale from "barely intrusive" to "strict gates." Maps directly onto our tiered scaffold idea. We adopt this as `SCAFFOLD_HOOK_PROFILE`.

### 3. Search-first skill

Research-before-coding as an explicit, auto-triggered behavior. Cheap to include, high leverage. **Worth adding as a Tier 1 skill.** Auto-triggers on substantive new work; surfaces existing patterns / prior art before the agent starts inventing.

### 4. Continuous learning / instinct extraction

ECC auto-extracts patterns from sessions into reusable skills. **Useful as inspiration for v1.5 / v2** — the wizard generates tailored skills upfront, then continuous learning grows them. Non-trivial machinery (confidence scoring, pruning, evolution into skills) but the pattern is right.

### 5. Strategic compact / memory persistence

Session lifecycle hooks that save and load context across sessions. Solves a real problem (cross-session continuity) without forcing developers to think about it. Matches our seamless-flow preference. **Tier 0 candidate.**

### 6. Skill stocktake

A meta-skill that audits the other skills for quality. Reviewer pattern applied to the skill pack itself. **Worth borrowing for our dogfooding loop and Tier 2 inclusion.**

### 7. The "no hooks in plugin.json" lesson

Three duplicate fix/revert cycles in ECC's history (#29, #52, #103) before they added a regression test. Concrete reminder: **bake CI tests for our skill pack from day one**, especially around install/uninstall idempotence.

### 8. Cross-harness translation pattern

Core logic + thin per-harness adapters. Overkill for v1, but the *pattern* of "shared `scripts/hooks/` with a thin adapter per harness" is worth keeping in mind for v2+.

### 9. Install state manifest

ECC has a SQLite state store recording what's installed, so it can do incremental updates and clean uninstalls. We need *something* like this even at small scale — at minimum, a `.claude/scaffold.json` manifest the wizard writes to track what was scaffolded. Critical for v2 migration ("this project was scaffolded by us" vs "this is foreign").

## What to skip

### 1. 48 agents

We have 3 (maybe 4). Sub-agents should be defined by *what context they need to be isolated from*, not by job title.

### 2. 182 skills

We have 8-12. Each skill description has to earn its context cost.

### 3. Multi-harness adapters (in v1)

Cursor, Codex, OpenCode, Gemini, Antigravity, Trae — ECC supports all of them. We support Claude Code only in v1.

### 4. Dashboards

ECC has a Tkinter desktop dashboard. We have a `.claude/scaffold.json` file and grep.

### 5. Separate security tools

AgentShield is a separate product bolted onto ECC. We don't ship a security scanner.

### 6. Language-specific reviewer agents

`typescript-reviewer`, `go-reviewer`, etc. — these should be one `reviewer` agent that adapts to context. Less surface area, more consistency.

### 7. Rust control-plane prototype

ECC v2.0 has a Rust binary doing process orchestration. Out of scope for our v1.

## The cautionary tale

ECC's README has multiple warnings about "duplicate skill" failures, conflicting install paths, and a `/uninstall --dry-run` flow because **people accidentally install it twice**. Their own quickstart includes:

```bash
node scripts/ecc.js doctor
node scripts/ecc.js repair
node scripts/ecc.js uninstall --dry-run
```

If our scaffold's quickstart starts looking like that, we've drifted from the design.

## The mental anchor

When tempted to add a feature, ask:

1. Does this earn its context cost? (Skills consume tokens just by existing.)
2. Does this require a new skill, or does it fit an existing one?
3. Does this auto-trigger reliably, or does it require explicit invocation?
4. Is there a deterministic way to enforce this (hook) instead of a probabilistic one (skill)?
5. Would a senior engineer at a small team find this useful, or would they roll their eyes at the overhead?

If the answer to 5 is "roll their eyes," we're building ECC.

## Source signals

- ECC repo: <https://github.com/affaan-m/everything-claude-code>
- The longform guide referenced in ECC has good content on token optimization, parallelization, and verification loops — worth reading for inspiration, not adoption
