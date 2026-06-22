---
status: DONE
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

The relocation targets already exist and are real: `docs/memory/glossary.md`
(the project glossary overlay) and `_common/lexicon.json` (the shipped
lexicon), both reachable on demand via `/jig:explain` (spec 065, DONE).
The Hot Cache re-describes much of what those surfaces already hold —
plus a `## Skills in this repo` table that re-states the per-skill
descriptions the host already injects into context every session. That is
exactly the EngTip #23 anti-pattern.

> **Frame correction (2026-06-19).** The DRAFT spec claimed "the repo's
> `AGENTS.md` (Codex variant) is already the lean shape" and treated it as
> the budget anchor. That was false: there is **no `AGENTS.md` in this
> repo** — the canonical `AGENTS.md` primer is [spec 033-02], still DRAFT
> (v2 / multi-host work). The `AGENTS.md` ⇄ `CLAUDE.md` sync (slice 02) is
> therefore handled on the **`v2` branch** when that lands; on this branch
> 076 leans `CLAUDE.md` against an absolute budget (see slice-01 AC #4),
> not against a non-existent file.

[spec 033-02]: ../033-host-adapter-portability/slice-02-agents-md-canonical-primer.md

**End state:** `CLAUDE.md`'s Hot Cache is a compressed index — always-on
facts kept as one-line claims + links; definitional bodies relocated to
`docs/memory/glossary.md` / `_common/lexicon.json` (reachable via
`/jig:explain`). A measurable budget guard keeps it from regrowing.

## Assumptions

The shipped-surface premises are grounded, not assumed: spec 055/057/065
are DONE and the lexicon loader + `/jig:explain` were probed live.

The **one load-bearing assumption** (named after frame-critique flagged the
original "None load-bearing" as the classification's own blind spot): that
the always-on-vs-on-demand split correctly identifies *every* behavioral
guard. A behavioral guard is push (the agent obeys it unprompted); the
glossary is pull (`/jig:explain` only helps a reader who already suspects a
term). **If a load-bearing guard is mis-binned as on-demand, it silently
stops guarding** — the exact regression class CLAUDE.md exists to prevent
(e.g. re-proposing parked work, rebasing v2 instead of merging).
*Mitigation (two layers, honestly scoped — neither is a completeness
proof):* (1) **primary** — slice 01's AC #1 classification rule makes the
guard-vs-definition test explicit, applied when authoring / `memory-sync`-ing
the primer and enforced by review; (2) **backstop** — AC #5's test pins each
*known* guard inline as its **full directive** (not a weak word), so a future
edit that relocates a known directive fails CI. The backstop is a whitelist:
it cannot prove an *unlisted* guard wasn't relocated — that residual risk is
carried by layer (1) + review, not by the test.

## Clarifications

- **Depth (resolved 2026-06-19):** drive to DRAFT spec.md + SPIDR slice
  files; implementation in a later session.
- **Always-on budget (resolved 2026-06-19):** **≤ 70 lines / ≤ 14KB** for
  `CLAUDE.md` — roughly half the DRAFT-time 109 lines / 27.8KB, tied to
  spec-055's "dumb zone" framing (keep the always-loaded primer small).
  The `AGENTS.md`-parity candidate was dropped because `AGENTS.md` does
  not exist on this branch (see the frame correction above).
- **`CLAUDE.md` ⇄ `AGENTS.md` relationship (deferred to slice 02 on
  `v2`):** `AGENTS.md` ships with spec 033-02 on the `v2` branch; the
  sync-model decision and its drift guard belong there, not on this
  branch. Slice 02 is parked until v2 carries `AGENTS.md`.
- **Keep-inline candidates (guidance):** active-work routing (v2 branch),
  the PARKED-don't-re-propose guards, and the do-not-modify-`conventions.md`
  constraint are plausibly every-turn. Everything *definitional* is
  on-demand.

## Decomposition

SPIDR — primarily a **Data** split: the change re-partitions *where each
fact lives* (always-on primer vs. on-demand glossary), driven by a
classification rule. Not a Spike (no unknown to reduce); the lean target
shape is an absolute budget (≤70 lines / ≤14KB), not a calibration against
another file (`AGENTS.md` does not exist on this branch — see the frame
correction in the Overview).

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
