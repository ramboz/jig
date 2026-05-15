---
status: DRAFT
skill: vision-elicitation
tier: 0
---

# Spec 017: vision-elicitation

## Overview

Today `scaffold-init`'s Q&A flow asks five surface-level installation
questions (runtime, solo/team, has CI, has tests, plans AI). Those map
to **tier selection** — *which* jig skills get auto-installed — not to
*project substance*. The audit at the head of [spec 016](../016-scaffold-mode/spec.md)
confirmed that `templates/docs/architecture.md.template` contains three
literal `Deferred — no signal from initial pitch` stanzas; the wizard
never asks anything that produces a single byte of substantive content
for `architecture.md`, and no `product-vision.md.template` exists at all.

This is the gap the user originally imagined: a wizard that **guides
the dev into refining project scope and architecture** during `init`.
The YarnFinder example in the global CLAUDE.md is the worked example
of what scaffold-init *should* produce after a good elicitation pass
— a project-vision.md with target users, the core problem, competitive
landscape, MVP scope, and a recommended slice order; an architecture.md
with a tentative stack, data model sketch, and explicit open questions.
Today's scaffold-init produces none of that.

Spec 017 introduces a new skill `vision-elicitation` (judgment-only,
no `.py` helper required — similar shape to slice 012-01's `pr-review`)
that conducts an interactive elicitation, then writes
`docs/product-vision.md` and updates `docs/architecture.md` with the
captured answers. Designed to be re-runnable as the project evolves.

## Why now (and why deferred to a separate spec)

- **The audit named two related-but-distinct gaps**: (a) plugin-vs-
  scaffold positioning [spec 016], and (b) missing vision/architecture
  elicitation [this spec]. Conflating them into one spec would mix a
  mostly-mechanical refactor (016) with a mostly-judgment-and-prompt-
  design effort (017). Keeping them separate lets 016 land fast as a
  positioning recovery, and gives 017 the room to design the
  elicitation flow properly.
- **It is the original positioning's load-bearing piece.** Without
  elicitation, a "scaffolding library" is just a directory-copier.
  The user's framing in the audit conversation was explicit: "I'm
  not sure we built much around helping create the project vision,
  architecture, etc." Closing this gap completes the scaffold-and-
  extend positioning.
- **Not blocking 016.** 016 ships a useful dual-mode product even
  without 017. 017 then adds the elicitation layer to whichever
  install shape the user picked.

## Goals (high level — to be SPIDR-split before promotion)

1. **A new skill `vision-elicitation`** that runs after `scaffold-init`,
   conducts a structured Q&A about the project's substance (problem,
   users, scope, stack, constraints, known decisions), and writes the
   captured answers into `docs/product-vision.md` (new template) and
   the relevant stanzas of `docs/architecture.md` (existing template,
   gains content slots).
2. **A `templates/docs/product-vision.md.template`** with named
   sections (Problem / Target users / Competitive landscape / MVP
   scope / Future scope / Constraints) — slots, not Deferred markers.
3. **An enriched `templates/docs/architecture.md.template`** that
   keeps Deferred stanzas as fallback but adds content slots that
   the elicitation skill fills (Stack choices, key data shapes,
   first ADR candidates).
4. **Optional seed-ADR pass.** For any decision the user names during
   elicitation (e.g. "we're going with SQLite, not Postgres"),
   scaffold a draft ADR under `docs/decisions/` via
   `/jig:adr-workflow`'s `new` subcommand.
5. **Re-runnable.** `/jig:vision-elicit` can be invoked at any time
   to refresh vision/architecture as the project's understanding
   matures. Re-runs preserve manually-edited sections via a stable
   marker convention (similar to how 016-02 plans to handle existing
   `.claude/settings.json`).

## Non-goals (high level)

- **Doing the user's thinking for them.** The elicitation asks
  questions; the user answers. The skill writes their words into the
  template, not its own interpretation.
- **Project-management surface.** No backlog, no estimates, no
  roadmap rendering. Those are spec-workflow's territory.
- **Auto-coding from the elicited spec.** The elicitation produces
  *docs* (vision, architecture, draft ADRs). Slice-authoring still
  lives in `/jig:spec-workflow`.
- **Replacing `scaffold-init`'s install-profile Q&A.** That stays as
  it is for tier selection; this skill is a separate, later step.

## SPIDR analysis (high level — full split happens at promotion to READY_FOR_REVIEW)

A first-pass split outline. Detailed slice ACs land when this spec is
promoted from DRAFT.

| Technique | Question | Outline |
|---|---|---|
| **S** — Spike | Do we need a spike on "how do we elicit architecture without LLMing past the user's actual answers"? | **No**; the pattern is well-trodden in product discovery (lean canvas, RFC templates). |
| **P** — Path | Single mega-Q&A or per-section flow? | Per-section, almost certainly — each section (Problem / Users / Scope / Stack / Constraints / Decisions) is independently skippable and re-runnable. |
| **I** — Interface | Skill-only (no helper) vs. skill + `.py` helper for template surgery? | TBD; lean toward skill-only initially (judgment + Read/Write), matching pr-review's shape. |
| **D** — Data | What templates change? | New `product-vision.md.template`; updated `architecture.md.template`; possibly new `decisions/adr-NNNN-<elicited>.md` drafts. |
| **R** — Rules | What marks a section "elicited" vs. "user-edited"? | Marker comment at section head (e.g. `<!-- elicited: 2026-05-15 -->`) lets re-runs detect manual edits and warn before overwriting. |

## Status

**DRAFT** — high-level scope only. Promotion to `READY_FOR_REVIEW`
requires:
- Slice-level SPIDR with concrete ACs and DoDs.
- A concrete proposal for the question set (which questions, in what
  order, with what skip/branch rules).
- A worked example: run the elicitation against the YarnFinder pitch
  in the global CLAUDE.md and verify the resulting
  `docs/product-vision.md` matches the hand-written example closely
  enough to be a credible artifact.

## Slice 017-01 — TBD

**STATUS: DRAFT**

(Placeholder — slice-level definition is part of the promotion-to-
`READY_FOR_REVIEW` step. Tracked here so the status board renders a
row.)

---

## References

- **Originating audit:** the same conversation that authored
  [spec 016](../016-scaffold-mode/spec.md).
- **Worked example of the target output:** the YarnFinder vision +
  architecture documents described in `/Users/ramboz/Projects/CLAUDE.md`.
- **Skill-only-no-helper precedent:** [spec 012-pr-review](../012-pr-review/spec.md)
  slice 012-01.
- **Related but distinct concern:** [spec 016-scaffold-mode](../016-scaffold-mode/spec.md)
  (positioning / packaging; this spec is about content guidance).
