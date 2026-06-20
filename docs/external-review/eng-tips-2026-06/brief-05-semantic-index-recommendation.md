# Brief: Recommend a semantic index in the context-cost skill (orchestrate, install nothing)

> EngTip #26 ("Token Saving", introducing Tokensave) and #23 ("Your
> Codebase Is Your AI's Context") name the exact lever jig's own spec 055
> / 057 analysis identified — replace `grep`/`glob`/`Read` scanning with
> a deterministic semantic index to cut turns and tokens — yet jig
> recommends it nowhere. It is the natural next mechanism for the
> context-cost discipline.

## Problem

jig's context-cost work (spec 055/057) established that cost ≈
orchestrator context × turns, and that **turn count** is a top knob. Its
mechanisms attack the symptom — delegate file-heavy reading to a
subagent (055-01), nudge on growth (055-02) — but never address the
*root* lever EngTip #26 calls out: a **semantic/code index** that lets
the agent ask "where is `foo` declared?" in one query instead of
grepping every match (declarations + calls + docs + incidental string
hits) across many turns.

EngTip #26 ships Tokensave for this; EngTip #23 frames readability/index
as a direct, recurring token saving. This very repo's environment exposes
**Scout** (a semantic-code-search MCP) — so the capability is real and
present, but jig's skills and `docs/workflow.md` say nothing about when
or whether to use one. A scaffolded project gets jig's *advice* to keep
context lean with no pointer to the single highest-leverage deterministic
tool for doing so.

This is a clean fit for jig's established "orchestrate installed tools,
install nothing, defer to richer" pattern — exactly how `contracts`
(recommends OpenAPI, validates via spectral) and `code-health` (drives
ruff/eslint on PATH) already work.

## Scope

1. **Add a semantic-index recommendation** to the context-cost surface —
   either a short section in `docs/workflow.md`'s "Context-cost
   discipline" standing guidance, or a small judgment-only skill
   (sibling of `contracts`): "for repos past a size/turn threshold, a
   semantic index (Scout / Tokensave / IDE indexer / Glean / Kythe) cuts
   orientation turns; here's how to tell, and which to reach for."
2. **Detect-and-defer, install nothing** — if a semantic-index MCP/tool
   is already available (Scout on the session, Tokensave installed),
   point at it; if not, recommend the standard options without bundling
   or auto-installing any (prefer-the-standard, EngTip #5; mirror
   code-health's PATH-resolve-or-degrade).
3. *(Optional)* a **scaffold-time nudge** — at `scaffold-init`, if the
   target is large enough to benefit, surface a one-line "consider a
   semantic index" hint (opt-out `.jig/no-index-hint`, mirroring the
   072-01 servo-hint pattern). Low priority; gate on whether the
   standing-guidance version proves insufficient.

## Non-goals

- **Install nothing, bundle nothing.** jig must not vendor or auto-install
  Tokensave/Scout/any indexer. It recommends and, if present,
  orchestrates — consistent with `contracts` / `code-health` / the
  security-floor scanners.
- **No endorsement of one tool.** Name the standard options (Scout,
  Tokensave, IDE indexers, Glean, Kythe) and the *criteria*; don't hard-
  wire jig to a single vendor (EngTip #5 — and Tokensave/Scout are
  Adobe-internal, so a generic recommendation travels better).
- **No replacement of the 055 mechanisms.** This complements
  delegate-reading and the growth nudge; it doesn't supersede them.
- **No new always-loaded context.** The recommendation lives off the hot
  path (on-demand skill / `docs/workflow.md`), per brief-01's discipline.

## Suggested SPIDR axis

**I (Interface)** primary if it's a skill (a new judgment surface);
**R (Rules)** if it's standing guidance (the rule "when a semantic index
pays for itself"). Clarify will likely settle this.

## Sketch of slices

1. **index-recommendation** — the standing-guidance section in
   `docs/workflow.md` *or* the slim judgment skill (clarify decides
   which), with the "when does it pay off" criteria and the
   detect-installed-else-recommend behavior. If a skill: defers to a
   richer installed code-navigation/indexing skill, like the other Tier-1
   baselines. Tests per the chosen shape (skill-surface test, or a
   workflow-doc presence/anchor test).
2. *(optional)* **scaffold-index-hint** — the `scaffold-init` one-line
   nudge + `.jig/no-index-hint` opt-out, mirroring 072-01. Skip unless
   slice 1 shows the passive guidance isn't reaching people.

## Dependencies

- **None blocking.** Conceptually downstream of spec 055/057 (DONE) —
  this is the "next mechanism" those specs gestured at.
- Pattern-aligned with `contracts`, `code-health`, and the 072-01
  servo-hint (all DONE) — reuse their detect-and-defer / opt-out shape.

## Notes for clarify / SPIDR

- **Primary clarify question: skill vs. standing-guidance?** A full skill
  is more discoverable but adds surface area (and always-loaded
  description tokens — mind brief-01). Standing guidance in
  `docs/workflow.md` is lighter and on-path-only-when-read. Lean toward
  guidance unless there's a routing reason for a skill.
- Likely clarify question: "Adobe-internal vs. public tools?" Scout /
  Tokensave / Polyget are Adobe-internal; jig ships publicly. The
  recommendation should center *the category* and public options (IDE
  indexers, tree-sitter-based local indexers, Glean/Kythe as references)
  and mention the internal ones only as "if available."
- Evidence angle: spec 056 (`usage.py`) can A/B a representative task
  with vs. without the index (Scout is togglable via `/mcp`), giving the
  spec a measured turn/token delta for its deviation log — the same
  before/after rigor 055 used.
- Honesty: this is a *recommendation*, not a guarantee of savings —
  EngTip #23's caution ("context isn't free; it helps only when it
  removes a step") applies to indexes too. Frame accordingly.
