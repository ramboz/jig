---
status: IN_PROGRESS
skill: spec-workflow
tier: workflow
adr_required: false
---

# Spec 056: Token-usage tracking (per-spec cost)

## Overview

This is **step 1** of the token-usage effort — spec 055 was step 2 (the
optimizations). The goal: measure **tokens and estimated cost per spec,
end-to-end**, so the team can see where cost goes and **prove** the spec-055
context-cost practices actually move the number.

The measurement substrate is already understood (from the 2026-06-01 cost
analysis that motivated spec 055). Claude Code writes per-session transcript
JSONL under `~/.claude/projects/<encoded-cwd>/*.jsonl`, with per-assistant
`usage` (input / output / `cache_read` / `cache_create`), `sessionId`,
`gitBranch`, and `cwd`. jig's worktree-per-task pattern means **cwd/worktree ≈
task ≈ spec/slice**, a natural attribution key. `ccusage` (run via
`npx ccusage@latest`, no install) converts token counts → $ with maintained
per-model pricing.

Two hard-won findings frame the design:

1. **Don't hand-roll pricing.** A hand-rolled Opus estimate was ~3× high
   (opus-4-7/4-8 blend to ~$0.71/Mtok). `ccusage` (or its pricing source) is
   the authority. The tracker stores **token counts** (stable) and converts to
   $ at report time.
2. **Subagent usage is under-recorded.** Subagent (`Agent`-tool) usage lands in
   the parent transcript's `toolUseResult` as a **final-turn-only** summary
   (`usage.iterations` length 1) plus cumulative `totalToolUseCount` /
   `totalDurationMs` — *not* per-turn records. A naive `message.usage` sum
   (what ccusage reads) misses it entirely; true subagent consumption needs a
   **peak_cacheR × toolUseCount proxy**.

## Goals

1. **Per-spec token + cost report.** A developer can ask "what did spec NNN
   cost?" and get a token breakdown + a ccusage-based $ estimate.
2. **Orchestrator vs subagent split.** Distinguish the long-lived orchestrator
   (~90% of cost in the analysis) from delegated subagents, using the
   `toolUseResult` proxy for the latter.
3. **Honest attribution.** Map transcripts → specs reliably (worktree/cwd; a
   `.jig/spec-ref` marker where ambiguous), and be explicit about what is
   *measured* vs *estimated*.
4. **Close the loop with spec 055.** The report is what lets us A/B the 055
   nudges — does a disciplined session cost less per landed slice?

## Non-goals

- **Real-time / live cost HUD.** On-demand reporting, not a live display.
- **Replacing ccusage.** We use ccusage for $ (pricing authority); the tracker
  adds the per-spec attribution ccusage doesn't do.
- **Billing-grade accuracy.** Subscription-vs-API pricing makes $ notional; the
  tracker is a *relative* optimization signal, honest about the subagent-proxy
  approximation.
- **Optimization itself.** Spec 055 owns the practices; 056 measures.

## SPIDR analysis

Axis: **Path (P)** — happy path first (orchestrator-only on-demand report),
then richer (subagent accounting, exact attribution). Each slice is vertical:
a developer runs a command and gets a number.

| Slice | Delivers | Notes |
|---|---|---|
| 056-01 | `usage.py report <spec>` — reads local transcripts, attributes by worktree, sums **orchestrator** usage, $ via `ccusage` | the MVP; on-demand (no hook/ledger needed) |
| 056-02 | + **subagent accounting** from `toolUseResult` (peak×turns proxy); orchestrator-vs-subagent split | closes the measurement gap |
| 056-03 | + **`.jig/spec-ref` attribution marker** (stamped on slice transition) for exact session→spec mapping | replaces the content heuristic |

**Spike rejected** — the substrate is known (the 055-motivating analysis
already parsed these transcripts). A capture-hook/ledger for history, or a
per-lifecycle-phase breakdown, is **deferred** (a future 056-04) until
on-demand reading proves too slow or history is actually needed.

## Design notes

- **On-demand, not a hook (MVP).** 056-01 reads
  `~/.claude/projects/*<repo>*/*.jsonl` directly at report time — no capture
  hook or ledger to maintain. Deferred unless transcript volume makes
  on-demand reads slow.
- **Attribution.** Group by `cwd`/worktree (≈ task); infer the spec from the
  branch name + transcript content (spec-path mentions), or an explicit
  `.jig/spec-ref` (056-03). Branch names are random codenames, so
  content/marker is required.
- **Cost via ccusage.** Store token counts; for $, apply `ccusage`'s per-model
  effective rates to the attributed token totals (or shell to `ccusage
  --json` and reconcile). Never hard-code rates.
- **Subagent proxy.** Per `Agent` `toolUseResult`: `usage` is final-turn-only,
  so estimate cumulative cache_read ≈ `usage.cache_read_input_tokens` ×
  `totalToolUseCount` × a factor (~0.5–1.0). Always label it an estimate.

## Decisions (resolved at clarify, 2026-06-01)

- **Helper home — RESOLVED:** `scripts/usage.py` standalone tool now (like
  `spec_lint.py`); a `jig:cost` skill wrapper deferred until discovery /
  triggering proves worth it. → 056-01.
- **ccusage integration — RESOLVED:** jig attributes + sums tokens per spec,
  then applies `ccusage`'s per-model effective rate to those sums for $.
  Attribution stays in jig; pricing stays in ccusage (no hand-rolled rates).
  → 056-01.
- **Subagent proxy factor — RESOLVED: 0.7 central** (between linear-growth 0.5
  and early-plateau 1.0); the raw final-turn-only sum is shown alongside as a
  lower bound. → 056-02.
- **`.jig/spec-ref` stamping point — RESOLVED:** on `workflow.py transition …
  IN_PROGRESS`. → 056-03.

## Slices

- `slice-01-orchestrator-usage-report.md` — on-demand per-spec orchestrator token + ccusage $ report (MVP)
- `slice-02-subagent-accounting.md` — subagent usage via the toolUseResult proxy; orchestrator-vs-subagent split
- `slice-03-spec-ref-attribution.md` — `.jig/spec-ref` marker for exact session→spec attribution

## Clarifications

### Q1: Where should the per-spec usage-report helper live?
_(category: Scope & Boundaries)_

**scripts/usage.py now, skill later** — ship the standalone script for the MVP; add a thin `jig:cost` skill wrapper later only if discovery/triggering proves worth it.

### Q2: How should the $ estimate be computed from ccusage (pricing authority)?
_(category: Acceptance Criteria Testability)_

**Apply ccusage's per-model rate to jig's attributed token sums** — jig does the per-spec attribution + token summing; ccusage supplies the per-model $/token; multiply. Keeps attribution in jig, pricing in ccusage (the approach the cost analysis validated).

### Q3: Which factor for the subagent proxy (peak_cacheR × toolUseCount × factor)?
_(category: Non-functional Requirements)_

**0.7 central** (between linear-growth 0.5 and early-plateau 1.0). The raw final-turn-only `toolUseResult` sum is shown alongside as a lower bound.

### Q4: When should `.jig/spec-ref` be stamped?
_(category: Edge Cases & Failure Modes)_

**On `transition → IN_PROGRESS`** — the natural per-slice signal; jig already owns this transition in `workflow.py`.

### Coverage summary

| Category | Status |
|---|---|
| Scope & Boundaries | Resolved |
| Acceptance Criteria Testability | Resolved |
| Dependencies & Blockers | Clear |
| Non-functional Requirements | Partial — on-demand transcript-read performance at scale is deferred (a future 056-04 capture-ledger if reads get slow) |
| Edge Cases & Failure Modes | Resolved |
| Terminology Consistency | Clear |
