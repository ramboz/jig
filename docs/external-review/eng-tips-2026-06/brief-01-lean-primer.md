# Brief: Lean the always-loaded primer (apply jig's own context-cost discipline to jig)

> Pure dogfooding. EngTip #23 ("Your Codebase Is Your AI's Context") and
> #26 ("Token Saving") say context that the agent re-reads every turn is
> only worth its token cost when it *eliminates an otherwise-necessary
> step*. jig's own `CLAUDE.md` is the heaviest always-loaded artifact in
> the repo and largely fails that test. The lean shape already exists.

## Problem

jig's project `CLAUDE.md` is loaded into context every session, every
turn. Its **Hot Cache** section inlines long, dense ADR-prose entries
(Lifecycle-family spine, Closed-spec drift policy, Spec-gate model,
Security floor, Review-evidence gate, Worktree-aware reservation,
Context-cost discipline, Thin-orchestrator, …) — each a multi-sentence
paragraph with embedded ADR/spec links. It is 109 lines but very token-
heavy (several entries are 200–400 words).

This contradicts jig's own thesis:

- **spec 055 (context-cost discipline)** measured that cost ≈
  orchestrator context-size × turns and shipped four mechanisms to keep
  in-session context lean.
- **spec 057 (thin-orchestrator)** confirmed peak context (r=0.96) as a
  top cost knob.
- **EngTip #23** is explicit: "context that describes the layout of a
  directory the agent is going to enumerate anyway … adds tokens without
  removing turns." Much of the Hot Cache is reference prose the agent
  does **not** need on every turn — it needs it *when it touches that
  subsystem*, which is exactly what `/jig:explain` + the lexicon (spec
  065) already deliver on demand.

The tell: the repo's untracked **`AGENTS.md`** (the Codex-targeted
variant) is the lean version — ~88 lines, a short glossary that *points
to* `docs/memory/glossary.md` instead of inlining ADR prose. jig already
authored the tip-#23-correct primer; the `CLAUDE.md` is the one out of
policy.

## Scope

1. **Classify every Hot Cache entry** as either:
   - **Always-on** — load-bearing on *every* turn regardless of
     subsystem (e.g. "the PARKED oracle boundary: do not re-propose
     without a real trigger"; "build on v2 not main"). Keep, but
     compress to a one-line claim + link.
   - **On-demand** — reference prose only needed when touching that
     subsystem. Move the body to `docs/memory/glossary.md` (and/or
     `_common/lexicon.json`) so `/jig:explain <term>` surfaces it, and
     leave a one-line pointer in `CLAUDE.md`.
2. **Rewrite `CLAUDE.md`** to the lean shape — Hot Cache becomes a
   compressed index, not an inlined encyclopedia. Target parity with the
   `AGENTS.md` density.
3. **Decide the `CLAUDE.md` ⇄ `AGENTS.md` relationship** — are they
   maintained as two hand-edited files, generated from one source, or
   does `memory-sync` keep them in lockstep? Pick one; today they drift.
4. **Apply the same lean shape to `templates/CLAUDE.md.template`** so
   scaffolded projects inherit the discipline jig preaches (separate,
   smaller change — the template's Hot Cache is already lighter, but
   confirm it doesn't model the heavy pattern).

## Non-goals

- **No information loss.** Every moved entry lands in `glossary.md` /
  `lexicon.json` and stays reachable via `/jig:explain`. This is
  relocation + compression, not deletion.
- **No new always-loaded file.** The point is *less* always-on context,
  not a second heavy primer.
- **No change to `/jig:explain` or the lexicon loader** (spec 065 is
  DONE) beyond possibly adding entries — those are the on-demand home,
  already built.
- **Don't touch the `docs/conventions.md` gate** — unrelated.

## Suggested SPIDR axis

**D (Data)** primary — the change is a re-partition of *where each fact
lives* (always-on primer vs. on-demand glossary), driven by a
classification rule.

## Sketch of slices

1. **lean-claude-md** — classify + relocate Hot Cache entries, compress
   `CLAUDE.md` to the index shape, land the moved bodies in
   `glossary.md` / `lexicon.json`. Add a test asserting `CLAUDE.md` stays
   under a token/line budget (a measurable 055-style guardrail) and that
   every relocated term resolves via the lexicon loader.
2. *(optional)* **template-and-sync** — apply the lean shape to
   `templates/CLAUDE.md.template` and decide/implement the
   `CLAUDE.md`⇄`AGENTS.md` lockstep (memory-sync step, or a generation
   source). Skip if slice 1's classification shows the template is
   already lean and the two files are intentionally hand-maintained.

## Dependencies

- **None blocking.** Builds on spec 055/057 (DONE) and spec 065
  (`/jig:explain` + lexicon, DONE) — those are the prerequisites and
  they already shipped.
- Coordinate lightly with `memory-sync` if slice 2 makes it the
  enforcement point for the lean shape.

## Notes for clarify / SPIDR

- Likely clarify question: "What is the always-on budget?" A concrete
  line/token cap makes this measurable (and testable) rather than
  aesthetic. Tie it to the 055 "dumb zone" framing.
- Likely clarify question: "Which Hot Cache entries are genuinely
  every-turn?" Candidates to *keep* inline: active-work routing (v2
  branch), the PARKED-don't-re-propose guards, and the
  do-not-modify-conventions constraint. Everything that is *definitional*
  ("what is the Review-evidence gate") is on-demand.
- Measurement hook: spec 056 (`usage.py`) can quantify the before/after
  orchestrator-token delta on a representative session — worth citing in
  the deviation log as evidence the change paid off.
- Honesty note for the spec: frame this explicitly as "jig applying
  EngTip #23 to itself," so the dogfooding intent is on the record.
