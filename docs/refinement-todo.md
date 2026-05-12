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

### ~~Decision: scaffold-stable ADR trigger~~ — RESOLVED 2026-05-12
~~**Deferred:** The mechanism to flip docs from `Draft` to `Stable` (after 3-5 reconciled specs) is described but not implemented.~~
**Resolved by:** [ADR-0001: scaffold-stable trigger](adrs/0001-scaffold-stable.md). Threshold is **3 reconciled slices**; flip mechanism remains manual for now (one-liner sed; a `stabilize.py` helper is a candidate for a future slice if needed).

### Decision: Scaffold.json manifest format
**Deferred:** The `scaffold.json` install-state manifest is referenced in the design but its schema is undefined.
**Resolution trigger:** Slice 001-01 (greenfield-scaffold). The implementer defines the schema as the first deliverable.

### Decision: Signal detection time-box and resource bounds
**Deferred:** Spike 001a calls for a 3-second wall-clock time-box and "no recursion deeper than 2 levels" with skip-dirs. The current `detect_signals()` honors the depth/skip-dir rule implicitly (no rglob in detectors) but does NOT enforce a wall-clock limit. `_read_text_safe()` reads files unboundedly — a multi-GB `requirements.txt` would be fully read into memory.
**Resolution trigger:** First time a user reports a slow or hung scaffold-init on a real project, OR when adding network-touching detectors.
**Risk:** Currently theoretical — local-only scaffolder on user-owned dirs.

### Decision: jig-memory-scan + jig-task-capture firing-rate measurement
**Deferred:** Slice 002-03 tuned the heuristics deterministically (strip code blocks / URLs / absolute paths; common-acronym skiplist) but did not measure actual firing rate against real session traffic. AC #5 calls for 10–40% as the healthy band; we have no telemetry yet.
**Resolution trigger:** After ~2 weeks of jig being enabled in a real session, scan the captured stderr/stdout of these hooks (or add a lightweight counter file in `.claude/`) and either confirm we're in band, or tune the COMMON acronym set / regex specificity.
**Mitigation idea:** add a `.claude/hook-firing.jsonl` write at the bottom of each hook (one line per fire) — cheap, gitignored, easy to grep.
**Watch-list (reviewer-flagged low-priority items):**
- Schemeless URLs like `example.com/FooBar` leak `FooBar` (the strip regex requires `http(s)://`)
- Nested triple-backtick fences leak the middle content (non-greedy `.*?` pairs outermost)
- `CSS` in COMMON skiplist could mask a frontend project's `CSS Modules` term — harmless today (single capitalized word doesn't match camelCase regex) but worth watching as the skiplist grows

### Decision: Transactional writes in scaffold()
**Deferred:** `scaffold()` writes CLAUDE.md, docs/*, scaffold.json, brief.md sequentially without a transaction. A crash between steps leaves partial state; the next run (without `--force`) refuses because some files exist. Currently we rely on the `scaffold.json`-present check as the "scaffolded" sentinel; if creation crashes before scaffold.json is written, a re-run succeeds but may overwrite partial files.
**Resolution trigger:** First report of a partial-scaffold state in the wild.
**Mitigation idea:** write everything to a temp dir, then atomically rename, OR write `scaffold.json` FIRST as an in-progress marker and finalize at the end.
