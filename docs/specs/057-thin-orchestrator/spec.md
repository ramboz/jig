---
status: IN_PROGRESS
skill: spec-workflow
---

# Spec 057: Thin-orchestrator discipline (delegation-first sessions + active compaction)

## Overview

Spec 055 shipped four **soft, scaffolded** context-cost mechanisms (delegate
reads, in-session growth nudge, read-once/lean, verbose-Bash containment). This
spec is the **data-driven follow-on**: a 2026-06-03 cross-session deep-dive (25
recent sessions, 8,379 orchestrator turns; script + results in `/tmp/`, to be
promoted) measured **where cost actually is** and **which levers move it**.

Findings that frame this spec:

- **Cost ≈ orchestrator context × turns.** `cache_read` is **52–55%** of
  cost-equivalent spend and correlates almost perfectly with turn count
  (r = 0.92) and peak per-turn context (r = 0.96). This is the dominant lever.
- **`cache_creation` (22–27%) is ~99% structural/incremental growth, NOT
  cache-TTL expiry.** Only **1.2%** of creation lands on post-gap (>5 min)
  turns; caches survive multi-hour idle (a ~4 h-gap turn re-read 797K tokens at
  read price with zero creation). A longer cache TTL / hit-rate tuning would
  recover essentially nothing → **rejected as a lever** (see Non-goals).
- **Model choice is minor.** The orchestrator is ~98% Opus already and
  subagents are only **17%** of combined cost — the orchestrator's own re-read
  is the budget.
- **Plannability is partial.** Subagent phases are moderately predictable
  (reviewer ≈ 383K cost-eq, implementer ≈ 1.1M; CV ≈ 0.5–0.6), but
  **orchestrator per-session cost is highly variable (CV ≈ 0.98)** — dominated
  by *turn count*, which is not constant. So the plannable lever is to
  **structure delegation up front to minimize improvised orchestrator turns**,
  not to predict the bill.

The conclusion: the bulk of cost is the two **Family-2** knobs — **turn count**
and **peak context** — so this spec operationalizes one mechanism for each
(slices 057-01 and 057-02). Clarify (2026-06-03) added a third, distinct lever:
**output volume** (slice 057-03) — output is ~22% of cost, separate from the
`context × turns` product but a real share at 5× input price. All three are
soft/non-blocking and measurable now that spec 056 gives per-spec token
attribution (and the `.jig/spec-ref` marker gives exact go-forward numbers).

## Goals

1. **Cut orchestrator turn count** on spec-implementation sessions by making
   delegation the *default, planned-up-front* shape — the orchestrator
   dispatches and integrates rather than doing turn-heavy work itself.
2. **Cap peak orchestrator context** by escalating 055-02's warn-only growth
   nudge into an *actionable* compaction / handoff trigger at a high band.
3. **Trim emitted output** — bound the delegation prompts the orchestrator
   writes and the summaries subagents return (output is ~22% of cost, 5×-priced).
4. **Stay soft.** All three mechanisms are nudges/guidance, not enforcement —
   consistent with 055's philosophy and ADR-0011 (deliberateness, not a
   firewall). jig cannot force `/compact`; it recommends, the user/harness acts.
5. **Be measurable.** Use the 056 tracker + the `.jig/spec-ref` marker to verify
   that disciplined slices show lower orchestrator turn-count / peak-context (and
   output share) than undisciplined ones, going forward.

## Non-goals

- **Cache-TTL / cache-hit-rate tuning.** The deep-dive falsified it as a lever
  (1.2% gap-correlated creation; caches survive multi-hour idle). Parked with
  evidence; do not re-explore without new data.
- **Model-downgrade policy (Family 3).** Subagents are only ~17% of cost; the
  saving is small. Out of scope.
- **Hard enforcement / blocking gates.** These are nudges (ADR-0011).
- **Implementing compaction itself.** jig cannot run `/compact` or rewrite the
  harness's context; 057-02 *prompts* an action — the user/harness performs it.
- ~~Output-token reduction~~ — **moved into scope as slice 057-03** at clarify
  (2026-06-03). Output is ~22% of cost (5×-priced, larger than folklore) — a
  real, if smaller, lever; the user chose to address it here rather than park it.

## SPIDR analysis

Axis: a **Rules + Interface** mix — three independent mechanisms: two for the
factors of `context × turns` (turn count, peak context) and one for output
volume. Each slice is independently **vertical** (delivers a
usable mechanism end-to-end). **Spike rejected** — the substrate is known: the
deep-dive characterized the cost; 055-02's `jig-context-check.sh` hook exists to
extend; subagent delegation is already proven (dogfooded on 056-03).

| Slice | Delivers | Lever |
|---|---|---|
| 057-01 | **Delegation-first session template** — a per-spec dispatch plan (each slice → implementer + which review passes + which skills) + workflow.md "run thin" guidance, so the orchestrator dispatches-and-integrates instead of improvising work across many turns | **turn count** |
| 057-02 | **Active compaction trigger** — `jig-context-check.sh` escalates from warn-only to an actionable compaction / fresh-session-handoff prompt at a high band | **peak context** |
| 057-03 | **Output discipline** — bound the size of delegation prompts the orchestrator writes + summaries subagents return (output is 5×-priced, ~22% of cost); sibling to 055-04 | **output volume** |

## Design notes

- **057-01 (turn count).** `workflow.py session-plan <spec>` (clarify Q1/Q2:
  helper form, stdout-only) enumerates a spec's non-DEFERRED slices and
  emits the standard per-slice phase sequence — implement → compliance → craft →
  [arch iff `arch_review`] → reconcile → land — with the subagent type + skill
  for each phase. The orchestrator then executes by *dispatching against the
  plan* rather than deciding each step ad hoc. The plannability finding is the
  rationale: delegated phases are predictable; the orchestrator's turn count is
  the variable, so front-loading delegation decisions is what shrinks it. Mirrors
  055-01's doc pattern (workflow.md guidance + a Hot-Cache/template pointer).
- **057-02 (peak context).** Extend the existing 055-02 `UserPromptSubmit`
  handler in `jig-context-check.sh` (which already reads the transcript-tail
  `cache_read` and bands at `JIG_CONTEXT_GROWTH_WARN_PCT` 40/60/80). Add a higher
  **compaction band** (new knob, e.g. `JIG_CONTEXT_COMPACT_PCT`, default above
  the warn bands) that emits an *actionable* message: recommend compaction, or a
  fresh-session handoff with a one-line "carry over: spec path, current slice,
  open threads" hint. Reuse the once-per-band + re-arm-on-drop machinery; don't
  duplicate the warn messages. Fail-open, advisory only.
- **Honesty on the evidence.** n = 25, single user, jig-specific workflow;
  attribution heuristic for 24/25 sessions; cost ratios are API list-price
  proxies (read 0.1× / write 1.25× / output 5× input), not billed dollars. The
  lever *ranking* is robust (r ≈ 0.9+); the absolute splits are directional.

## Slices

- `slice-01-delegation-first-template.md` — per-spec dispatch plan + "run thin" guidance (turn-count lever)
- `slice-02-active-compaction-trigger.md` — 055-02 hook escalates to an actionable compaction nudge (peak-context lever)
- `slice-03-output-discipline.md` — bound delegation-prompt + returned-summary size (output-volume lever; added at clarify)

## Open questions

_All four resolved at clarify (2026-06-03) — see ## Clarifications below._

## Clarifications

### Q1: What form should the 057-01 delegation-first dispatch plan take?
_(category: Scope & Boundaries / Acceptance Criteria Testability)_

**workflow.py helper** — a `session-plan <spec>` subcommand emits the per-slice
dispatch plan deterministically. Script-first, mirroring the 056 precedent (a
skill can come later only if discovery/triggering proves worth it).

### Q2: Where should the dispatch plan output live?
_(category: Acceptance Criteria Testability)_

**stdout-only** — emit on demand to stdout; no persisted file (leanest;
consistent with `usage.py report`).

### Q3: How should the 057-02 compaction trigger act when context crosses the high band?
_(category: Non-functional Requirements / Edge Cases & Failure Modes)_

**Prompt-only, ~75% default** — emit an actionable text recommendation (compact
/ hand off + carry-over hint) at a default ~0.75 band (tunable via
`JIG_CONTEXT_COMPACT_PCT`); never run `/compact` itself (ADR-0011: nudge, not
enforcement).

### Q4: The ~22% output-token cost lever — where should it go?
_(category: Scope & Boundaries)_

**Add as a 057-03 slice** — an output-discipline slice in this spec (concise
delegation prompts + concise returned subagent summaries).

### Coverage summary

| Category | Status |
|---|---|
| Scope & Boundaries | Resolved |
| Acceptance Criteria Testability | Resolved |
| Dependencies & Blockers | Clear |
| Non-functional Requirements | Resolved |
| Edge Cases & Failure Modes | Partial — 057-01's empty-/non-standard-slice handling not yet pinned (deferred to implementation) |
| Terminology Consistency | Clear |
