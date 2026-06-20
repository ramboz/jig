---
status: DRAFT
skill: spec-workflow
use_cases: []
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 076: Lean the always-loaded primer

> Source: [eng-tips self-audit brief-01](../../external-review/eng-tips-2026-06/brief-01-lean-primer.md)
> (EngTip #23 "Your Codebase Is Your AI's Context", #26 "Token Saving").
> Reserved 2026-06-19 via `workflow.py new`. Pure dogfooding —
> jig applying its own context-cost discipline to itself.

## Overview

jig's project `CLAUDE.md` is loaded into context **every session, every
turn**. Its **Hot Cache** inlines long, dense ADR-prose entries
(Lifecycle-family spine, Closed-spec drift policy, Spec-gate model,
Security floor, Review-evidence gate, Worktree-aware reservation,
Context-cost discipline, Thin-orchestrator, …) — each a multi-sentence
paragraph with embedded links. It contradicts jig's own thesis:

- **spec 055** (context-cost discipline) measured cost ≈ orchestrator
  context-size × turns and shipped mechanisms to keep in-session context
  lean.
- **spec 057** (thin-orchestrator) confirmed peak context (r=0.96) as a
  top cost knob.
- **EngTip #23** is explicit: context that re-describes what the agent
  would read anyway "adds tokens without removing turns." Much of the Hot
  Cache is *definitional reference prose* the agent needs only when it
  touches that subsystem — which is exactly what `/jig:explain` + the
  lexicon (spec 065) already serve on demand.

The tell: the repo's `AGENTS.md` (Codex variant) is already the lean
shape — a short glossary that *points to* `docs/memory/glossary.md`
instead of inlining ADR prose. jig already authored the tip-#23-correct
primer; `CLAUDE.md` is the one out of policy.

**End state:** `CLAUDE.md`'s Hot Cache is a compressed index — always-on
facts kept as one-line claims + links; definitional bodies relocated to
`docs/memory/glossary.md` / `_common/lexicon.json` (reachable via
`/jig:explain`). A measurable budget guard keeps it from regrowing.

## Assumptions

None load-bearing — this builds entirely on shipped surfaces (spec 055,
057, 065 are all DONE; the lexicon loader and `/jig:explain` exist). The
classification of "always-on vs. on-demand" is judgment, executed in
slice 01, not an unverified runnable-surface claim.

## Clarifications

- **Depth (resolved 2026-06-19):** drive to DRAFT spec.md + SPIDR slice
  files; implementation in a later session.
- **Always-on budget (open — for slice 01):** set a concrete line/token
  cap on `CLAUDE.md` so the guard is testable, not aesthetic. Tie it to
  the spec-055 "dumb zone" framing. Candidate: parity with `AGENTS.md`.
- **`CLAUDE.md` ⇄ `AGENTS.md` relationship (open — for slice 02):** two
  hand-edited files, one generated from the other, or kept in lockstep by
  `memory-sync`? They drift today. Slice 02 decides.
- **Keep-inline candidates (guidance):** active-work routing (v2 branch),
  the PARKED-don't-re-propose guards, and the do-not-modify-`conventions.md`
  constraint are plausibly every-turn. Everything *definitional* is
  on-demand.

## Decomposition

SPIDR — primarily a **Data** split: the change re-partitions *where each
fact lives* (always-on primer vs. on-demand glossary), driven by a
classification rule. Not a Spike (no unknown to reduce); the lean target
shape already exists in `AGENTS.md`.

- **076-01 (relocate + compress):** classify every Hot Cache entry, move
  definitional bodies to `glossary.md` / `lexicon.json`, compress
  `CLAUDE.md` to the index shape, add a budget-guard test. Delivers the
  whole user-facing win — a lean always-loaded primer — on its own.
- **076-02 (template + sync):** apply the lean shape to
  `templates/CLAUDE.md.template` so scaffolded projects inherit the
  discipline, and resolve the `CLAUDE.md` ⇄ `AGENTS.md` relationship.

## Slices

- [076-01 — relocate + compress the Hot Cache](slice-01-lean-claude-md.md)
- [076-02 — lean template + primer sync](slice-02-template-and-sync.md)
