> Decisions the initial setup explicitly deferred. Each item has a resolution trigger.
> Resolve items by writing an ADR and linking it here.

# Refinement Todo: jig

## Architecture

### Decision: Hook strictness profiles
**Deferred:** Shipping an unread `SCAFFOLD_HOOK_PROFILE` env var creates false expectations. Need to define values AND implement profile-switching logic before exposing.
**Resolution trigger:** First spec that touches hook enforcement behavior (likely 001-03 or a dedicated Tier 1 spec).
**Valid values to define:** `minimal | standard | strict`

### Decision: SubagentStart hook event
**Deferred:** `SubagentStart` is documented in the changelog (v2.0.43) but absent from the official plugin docs' hook events list. Risk of API instability.
**Resolution trigger:** First time we need to react to subagent start (e.g., reviewer logging, effort-scaling enforcement).
**Risk:** Event name or behavior may differ from expectations. Test before relying on it.

### Decision: additionalContext format for Stop vs UserPromptSubmit hooks
**Deferred:** Confirmed `{ "continue": true, "additionalContext": "..." }` for these events, but the plan review flagged this as needing empirical verification.
**Resolution trigger:** Slice 002-03 (auto-detect-hooks) — test both hooks against real sessions.

## Conventions

### Decision: Skill telemetry granularity
**Deferred:** `jig-telemetry.sh` logs Task tool spawns as a proxy for skill invocations. This is imprecise — skills can trigger without spawning a Task.
**Resolution trigger:** After two weeks of telemetry data. If the log is too sparse to be useful, explore the `SubagentStart` / `InstructionsLoaded` events as alternatives.

## Operations

### Decision: scaffold-stable ADR trigger
**Deferred:** The mechanism to flip docs from `Draft` to `Stable` (after 3-5 reconciled specs) is described but not implemented.
**Resolution trigger:** After 3 reconciled specs in a dogfood project. Write the `scaffold-stable` ADR then.

### Decision: Scaffold.json manifest format
**Deferred:** The `scaffold.json` install-state manifest is referenced in the design but its schema is undefined.
**Resolution trigger:** Slice 001-01 (greenfield-scaffold). The implementer defines the schema as the first deliverable.
