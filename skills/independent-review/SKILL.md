---
name: independent-review
description: >
  Spawn a fresh reviewer subagent to evaluate implemented work against its spec,
  acceptance criteria, and Definition of Done — without access to the implementation
  conversation. Use after an implementer subagent completes a spec slice, when the
  spec status transitions to REVIEWED, or when the user asks for a code review on
  a spec-driven deliverable.
  Do not use for ad-hoc code review unrelated to a spec, or for reviewing the spec
  itself (that is the READY_FOR_REVIEW transition in spec-workflow).
disable-model-invocation: true
user-invocable: true
---

> **Status: DRAFT — not yet implemented.**
> This skill is planned in the jig roadmap but not ready for use.

## What this skill does (when implemented)

1. Reads the spec, deliverable path, and acceptance criteria
2. Spawns the `reviewer` subagent with a system prompt that forbids referencing
   prior implementation context ("You are seeing this work for the first time")
3. Reviewer reads ONLY: spec, deliverable files, acceptance criteria
4. Returns a structured verdict: `VERDICT: pass|fail|needs-changes` + reasoning + issues
5. Triggers reconciliation if verdict is `pass`
6. Also handles reconciliation review (second reviewer pass on doc changes)

## Context isolation pattern

Implementer writes deliverable to disk → reviewer spawned via Task with a fresh
system prompt → reviewer reads only what it's pointed at. This is imperfect (parent
context technically accessible) but works reliably when system prompts are sharp.

## Gotchas

- Reviewer subagent tool list is read-only (`Read`, `Glob`, `Grep`). No `Write` or `Edit`.
- Reviewer system prompt MUST include: "You have not previously discussed this task."
- Reviewers do not write to `docs/memory/` — defining the glossary is not their job.
- Reconciliation review (second pass on doc changes) is also this skill's responsibility,
  not a separate skill.
