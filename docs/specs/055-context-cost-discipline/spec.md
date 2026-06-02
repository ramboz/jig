---
status: IN_PROGRESS
skill: spec-workflow
tier: workflow
adr_required: false
---

# Spec 055: Context-cost discipline

## Overview

A token-cost analysis of 37 days of jig's own development (88 local
transcripts; ~$5,003 machine-wide via `ccusage`, ~$3,360 attributable to
jig) showed that **cost is overwhelmingly the orchestrator's context size ×
number of turns**: ~97% of token *volume* is `cache_read` — the long-lived
main session re-reading its accumulated context on every turn. Two findings
frame this spec:

1. **In-session growth, not the baseline, is the cost.** The always-loaded
   primer (CLAUDE.md + `docs/memory/*`) measured ~17K tokens — only ~4% of a
   heavy session's cache-reads. The other ~96% is content that *accumulates
   during the session* (file reads, command output, edits, reasoning) and is
   re-read on every subsequent turn.
2. **The orchestrator is ~90% of cost; subagents are ~8%.** Subagents are
   cheap precisely because they run in bounded, short-lived, isolated
   contexts. Delegating work to them is itself a cost optimization.

Orchestrator context composition (one-time tokens added, all jig sessions):
Read 26%, Bash 26% (output 19%), Edit 18%, Agent 9.6%, Write 8%, reasoning
6%. The worked anti-pattern is the **"$540 session"** (spec 008's
`quizzical-moore` worktree): a codebase-gap review run entirely in the
orchestrator — 985 turns, **1** context reset, context climbing to 840K —
that should have delegated its reading to an isolated subagent.

jig already has cost machinery, but it targets the **baseline** only
(spec 025 claude-md-hygiene; spec 026 context-fill-telemetry's SessionStart
warning). This spec owns the **growth-control gap**: the in-session best
practices a developer experiences during a jig session.

Full findings: memory file `token-cost-findings.md`.

## Goals

1. **Make delegation the default for file-heavy work.** Establish the
   thin-orchestrator principle: the orchestrator coordinates and keeps
   summaries; file-heavy reading/analysis is delegated to an isolated
   read-only subagent — the **built-in `Explore` / `general-purpose`**
   agents (context isolation, *not* parallelism — consistent with
   `docs/research/03-research-subagents-and-isolation.md`'s conservative
   stance on coding-task parallelism).
2. **Nudge against unchecked in-session growth.** Surface a timely, soft,
   non-blocking signal when accumulated context crosses the dumb-zone line —
   extending the existing context-fill seam from baseline-only to in-session.
3. **Codify read-once / read-lean discipline.** Discourage re-reading files
   already in context and whole-file reads where a range suffices (Read is
   the single biggest context source).
4. **Keep verbose command output out of the orchestrator.** Route test
   suites, builds, and verbose VCS commands into subagents and surface only
   results.
5. **Document the discipline as standing guidance** in `docs/workflow.md`,
   with a Hot-Cache pointer, so the practices are legible and durable.

## Non-goals

- **Baseline / primer trimming** — owned by spec 025 (claude-md-hygiene) and
  spec 026 (context-fill-telemetry). This spec does not change the
  SessionStart baseline warning; it adds the in-session dimension.
- **External output-compression tooling (rtk)** — owned by spec 044
  (rtk-integration-spike), parked. This spec is the *internal* discipline
  that should precede any external tool.
- **Hard enforcement / blocking gates.** Consistent with jig's soft-hook
  philosophy, every signal here is a non-blocking nudge. Lifecycle
  enforcement is spec 045's concern.
- **A bespoke jig explorer agent.** Decided: reuse the built-in `Explore` /
  `general-purpose` agents rather than ship our own (see Decisions).
- **The token-usage tracker (step 1).** Per-spec cost measurement is a
  separate effort; this spec can land without it, though the tracker is what
  later *proves* each practice's impact.

## SPIDR analysis

Axis: **Rules (R)** — a set of context-cost rules made real, sliced
highest-measured-impact first. Each slice is vertical: it changes what a
developer experiences in a jig session (guidance they read + a mechanism
that nudges/enables it + tests) and delivers end-to-end value independently.

| Slice | Rule (cost driver) | Measured share | Mechanism |
|---|---|---|---|
| 055-01 | Delegate file-heavy reading to isolated subagents (thin orchestrator) | Read+Edit+Write ≈ 52% | workflow.md principle + delegation pattern targeting built-in `Explore` |
| 055-02 | Nudge on unchecked in-session growth | the ×turns multiplier (985 turns, 1 reset) | `jig-context-check.sh` extended to `UserPromptSubmit`, reading the transcript tail; dumb-zone threshold; scaffolded into targets |
| 055-03 | Read-once / read-lean | Read ≈ 26% | `PreToolUse` duplicate/large-read nudge + guidance |
| 055-04 | Keep verbose Bash out of the orchestrator | Bash output ≈ 19% | implementer-agent prompt + guidance |

**Spike was considered and rejected** — the mechanisms are known; nothing
requires a timeboxed investigation. **Anti-horizontal check:** no slice is
docs-only — each pairs guidance with a mechanism a developer observes (a
nudge, a delegation pattern, or an agent-prompt behavior change).

## Design principle

**The orchestrator's context is the most expensive real estate in the
system** — it is re-read every turn for the whole session. Every token that
enters it should earn its place; anything that can be done in an isolated,
disposable context (reading, searching, analyzing, running verbose commands)
should be. This is a *cost* argument that happens to align with the existing
"dumb zone" *quality* argument — both say keep the orchestrator lean.

## Decisions (resolved during authoring)

1. **Delegation target — RESOLVED: reuse the built-in `Explore` /
   `general-purpose` agents.** jig does not ship its own explorer/analyst
   agent. Rationale: the built-ins are read-only and capable; adding a jig
   agent would duplicate them. Revisit only if their return contract proves
   insufficient for jig's summary needs. Recorded inline in `docs/workflow.md`
   (no ADR — the choice is low-stakes and reversible). → shapes 055-01.
2. **In-session signal — RESOLVED.** A `UserPromptSubmit` hook (the per-turn
   analog of the `SessionStart` baseline hook) reads the **last assistant
   turn's `cache_read_input_tokens` from the transcript tail** (O(1) — no
   full scan) as the current-context-size proxy, and nudges when it crosses a
   threshold defaulting to **0.40 of the context window** (the dumb-zone
   line), configurable via the `JIG_CONTEXT_*` env convention. → shapes
   055-02.
3. **Noise budget — RESOLVED (accepted).** Nudges fire **at most once per
   threshold band** per session (40 → 60 → 80%), tracked in a per-session
   state file; transcript reads are bounded (tail only). → shapes 055-02 /
   055-03.

## Open questions

- **Threshold bands & exact env-var name** for 055-02 (40/60/80 vs. a single
  threshold; `JIG_CONTEXT_GROWTH_WARN_PCT` vs. reuse) — fine-tune at slice
  planning.
- **Read-lean size threshold** for 055-03 (what counts as a "large" whole-file
  read worth nudging on `offset`/`limit`).

## Slices

- `slice-01-delegate-reads.md` — thin orchestrator / delegate file-heavy reading
- `slice-02-in-session-growth-nudge.md` — in-session context-growth nudge
- `slice-03-read-once-discipline.md` — read-once / read-lean
- `slice-04-verbose-bash-containment.md` — keep verbose command output out of the orchestrator

## Clarifications

### Q1: Do the new nudge hooks (055-02 in-session growth, 055-03 read-once) get scaffolded into target projects, or ship jig-repo-only for now?
_(category: Scope & Boundaries)_

**Scaffold to targets too** — wire the nudge hooks into scaffold-init's generated `settings.json` so every jig-scaffolded project gets them from day one. (Expands 055-02 / 055-03 scope to touch scaffold-init's generated settings.)

### Q2: Where should the in-session growth nudge (055-02) live relative to the existing SessionStart baseline hook (`jig-context-check.sh`, spec 026)?
_(category: Dependencies & Blockers)_

**Extend `jig-context-check.sh`** — one script handles both `SessionStart` and `UserPromptSubmit`; a single home for all context warnings.

### Q3: After a `/compact` resets context (cache_read drops), should the per-band rate-limit re-arm so a later long stretch can warn again?
_(category: Edge Cases & Failure Modes)_

**Re-arm on context drop** — if cache_read falls back below a band, clear the warned-state so a subsequent climb past it nudges again.

### Q4: How should the hook nudges be tested?
_(category: Acceptance Criteria Testability)_

**Synthetic JSONL fixtures** — mirror `test_jig_context_check.py`: feed crafted transcript JSONL to the hook script, assert nudge text vs. silence and exit 0.

### Coverage summary

| Category | Status |
|---|---|
| Scope & Boundaries | Resolved |
| Acceptance Criteria Testability | Resolved |
| Dependencies & Blockers | Resolved |
| Non-functional Requirements | Partial — threshold bands, env-var name (055-02), and read-lean size threshold (055-03) left to fine-tune at slice planning |
| Edge Cases & Failure Modes | Resolved |
| Terminology Consistency | Clear |
