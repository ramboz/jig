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
| **R** — Rules | What marks a section "elicited" vs. "user-edited"? | Marker comment at section head: `<!-- elicited: <date> / status: filled / hash: <sha256-of-body> -->`. Re-runs read the marker, recompute the body hash, and warn if it diverges from the last-elicited hash (= manual edit). Full design in slice 017-03. |

## Status

**DRAFT** — slice-level definitions and question set landed
2026-05-15; ready for promotion to `READY_FOR_REVIEW` pending a
spec-level review pass.

Promotion checklist:
- [x] Slice-level SPIDR with concrete ACs and DoDs — see slices
  017-01 / 017-02 / 017-03 below; 017-04 deferred with an
  empirical resolution trigger.
- [x] Concrete proposal for the question set — see Appendix A
  (12 sections after slice 017-01 reshape — 1 per vision slot + 1
  per arch slot; skip / re-run / stop mechanics defined).
- [x] Worked-example *artifact* on disk — [docs/product-vision.md](../../product-vision.md)
  serves as ground-truth output shape and is referenced by slice
  017-02 AC #4 / #5 (structural-match dogfood) and by the
  worked-example transcripts that 017-02 ships.
- [ ] Worked-example *run* — folded into slice 017-02 AC #4 and
  #5 (structural-match dogfood against the jig + YarnFinder
  pitches) and AC #9 (routing dogfood). Cannot run before the
  elicitation skill is implemented; this is no longer a spec-
  level gate, it's the DoD of slice 017-02.

### Worked-example artifact (seeded 2026-05-15)

[docs/product-vision.md](../../product-vision.md) is now seeded by
hand as jig's own dogfood vision document. It serves two roles for
this spec:

1. **Ground-truth output shape.** The elicitation skill's resulting
   `docs/product-vision.md` should match this artifact's section
   structure (Vision statement / Target users / Core problem /
   Competitive landscape / Core features (tier-stratified) / Design
   principles / How new work enters / Future scope) and tone (concise,
   linked, deferred-items explicit).
2. **Promotion gate input.** The "run the elicitation against the
   YarnFinder pitch" worked-example check (above) should compare the
   skill's output against both (a) the YarnFinder vision described
   in `/Users/ramboz/Projects/CLAUDE.md` and (b) this jig vision
   document. Two different project shapes (consumer-product vs.
   dev-tooling-on-dev-tooling) sharpen the question set — the
   YarnFinder shape stress-tests *data-sourcing* and *MVP-vs-future*
   questions; jig's shape stress-tests *design-principles* and
   *non-goals* questions.

The artifact also closes a standalone dogfood gap noted during the
spec 017 framing: jig itself had no vision document, even though the
template (will) prescribe one once 017 lands. Seeding it now lets
jig pass its own positioning audit while the elicitation skill is
being designed.

## Slices

- [017-01 — vision-template-and-architecture-slots](slice-01-vision-template-and-architecture-slots.md)
- [017-02 — vision-elicitation-skill-core](slice-02-vision-elicitation-skill-core.md)
- [017-03 — re-runnable-with-edit-detection](slice-03-re-runnable-with-edit-detection.md)
- [017-04 — seed-ADR-pass](slice-04-seed-adr-pass.md)


## References

- **Originating audit:** the same conversation that authored
  [spec 016](../016-scaffold-mode/spec.md).
- **Worked example of the target output:** the YarnFinder vision +
  architecture documents described in `/Users/ramboz/Projects/CLAUDE.md`.
- **Skill-only-no-helper precedent:** [spec 012-pr-review](../012-pr-review/spec.md)
  slice 012-01.
- **Related but distinct concern:** [spec 016-scaffold-mode](../016-scaffold-mode/spec.md)
  (positioning / packaging; this spec is about content guidance).

---

## Appendix A: Question set (proposed)

The elicitation skill asks **12 sections** in order (1 per
product-vision.md slot + 1 per architecture.md elicitation slot;
slice 017-01 reshape grew this from 9 to 12 when architecture.md
gained Repository structure / Module boundaries / Data model as
distinct slots alongside Tech stack). Each section is independently
skippable; any answered section gets its template slot filled and
its marker transitioned to `status: filled`; skipped sections
transition to `status: skipped`. Stop condition: all 12 sections
answered or explicitly skipped. The skill does not loop indefinitely.

> **Note:** *"always asked"* below means the skill prompts for the
> section by default; the user can still answer "skip" at the prompt.
> *"optional"* means the skill flags the question as low-priority and
> a one-key skip is offered upfront.

### Section 1 — Identity *(always asked)*

Produces: vision template's `## Identity` section (vision statement +
optional tagline subhead + optional positioning story).

- **Q1.1:** "In one sentence, what does this project do?"
- **Q1.2** *(optional)*: "If you were defining the project's name as
  a noun ('<name> (noun): __'), what's its essence?"
- **Q1.3** *(optional)*: "Is there a positioning story worth
  recording? (e.g. 'we pivoted from X to Y after we realized Z',
  or 'an audit at month N flagged that we'd drifted from the
  original framing')."

### Section 2 — Target users *(always asked)*

Produces: `## Target users` (including a "not for" sub-bullet).

- **Q2.1:** "List 2–4 specific user types this project serves. Be
  concrete — 'first-time Claude Code users' or 'devs migrating
  legacy specs' is better than 'developers'."
- **Q2.2:** "Who is this *not* for? List 1–3 personas you're
  explicitly choosing not to serve. (Often clearer to define a
  product by exclusion than inclusion.)"

### Section 3 — Core problem *(always asked)*

Produces: vision template's `## Core problem` section (problem
description + paths-today-and-shortfalls + optional originating-
incident sub-bullet).

- **Q3.1:** "Describe the problem in 2–3 sentences. What's broken
  about how users try to do this today?"
- **Q3.2:** "Enumerate the 2–3 paths users take today and where
  each falls short."
- **Q3.3** *(optional)*: "Any specific incident, audit, or
  comparison that motivated this project? If yes, sketch it in
  2–3 sentences."

### Section 4 — Competitive landscape *(always asked)*

Produces: `## Competitive landscape` (table format).

- **Q4.1:** "List 3–5 alternatives a user might consider —
  generic or specific."
- **Q4.2** *(per alternative)*: "What does it do well?"
- **Q4.3** *(per alternative)*: "Where does it fall short for *this
  particular* gap?"
- **Q4.4:** "In one sentence, where does this project fit between
  those alternatives?"

### Section 5 — Scope *(always asked)*

Produces: vision template's `## Scope` section, including its four
H3 sub-sections (`### Core features (prioritized)` /
`### Tiers / phases` *(optional)* / `### MVP scope` /
`### Out of scope (deliberately)`).

- **Q5.1:** "List the core features, in priority order."
- **Q5.2:** "Do these features cluster into tiers or phases?
  (e.g. always-install / default-on / opt-in; or MVP / v2 / v3.)
  If yes, name the tiers."
- **Q5.3:** "Which features are MVP? Which are deferred?"
- **Q5.4:** "What's explicitly out of scope? List 3–5 non-goals —
  things users might expect that you're choosing not to do."

### Section 6 — Repository structure *(always asked; feeds architecture.md)*

Produces: architecture.md's `## Repository structure` slot.

- **Q6.1:** "What's the top-level directory layout? Even a one-line
  description per directory beats nothing — it's the easiest place
  for new contributors to start. If you don't have it yet, sketch
  what you expect: 3–6 top-level directories with a one-line purpose
  each."

### Section 7 — Tech stack *(always asked; feeds architecture.md)*

Produces: architecture.md's `## Tech stack` slot.

- **Q7.1:** "Runtime / language?"
- **Q7.2:** "Platform commitments? (cloud target, deployment shape,
  package manager, database, key external services.)"
- **Q7.3:** "For each of these — locked-in decision, or still open?"
- **Q7.4** *(optional, per locked-in decision)*: "Want to seed a
  draft ADR for this? (Slice 017-04 lands the auto-scaffold; for
  now this is captured as a tagged sub-bullet so `adr-workflow`
  can pick it up later.)"

### Section 8 — Module boundaries *(always asked; feeds architecture.md)*

Produces: architecture.md's `## Module boundaries` slot.

- **Q8.1:** "What are the top-level *concerns* of this codebase?
  Name them even if their interfaces aren't formal yet."
- **Q8.2:** "Are interface contracts between those concerns defined
  today, or is the coupling read-only / one-directional / deferred?
  'Today's coupling is read-only' is a valid and honest answer."

### Section 9 — Data model *(always asked; feeds architecture.md)*

Produces: architecture.md's `## Data model` slot.

- **Q9.1:** "What state does this project own? List the state
  elements (config files, databases, append-only logs, in-memory
  caches, etc.) with one-line descriptions."
- **Q9.2:** "If the project is stateless or near-stateless, name
  that explicitly. 'Stateless — config files only' is a valid and
  honest answer; leaving the section blank is not."

### Section 10 — Design principles & constraints *(always asked)*

Produces: vision template's `## Design principles & constraints`
section.

- **Q10.1:** "Are there principles every spec should be judged
  against? Constraints you don't want to violate? List 3–7."
- **Q10.2:** "Any non-obvious constraints? (perf budgets,
  regulatory, team size, cost, context-window economics,
  backward-compat policy.)"

### Section 11 — How new work enters *(always asked)*

Produces: vision's `## How new work enters` (the equivalent of
"data sourcing" in the YarnFinder shape).

- **Q11.1:** "How will new features get prioritized? Signal-driven,
  roadmap-driven, stakeholder-driven, or some mix?"
- **Q11.2:** "Any specific triggers documented for what justifies
  a new spec? (e.g. 'pain hit twice', 'cross-project comparison
  revealed a pattern', 'compliance requirement landed'.)"

### Section 12 — Open questions *(always asked)*

Produces: entries in `docs/refinement-todo.md` (the
architecture.md `## Open questions` section is just a pointer
to that file).

- **Q12.1:** "What's still uncertain? List architectural questions
  that don't have answers yet. (Bullets here become refinement-todo
  rows automatically.)"

### Skip / re-run / stop mechanics

- **Skip:** any section can be skipped at the prompt. The skill
  writes `<!-- elicited: <date> / status: skipped -->` and moves
  on. The user can return later with `/jig:vision-elicit --section
  "<name>"`.
- **Stop conditions:** all 12 sections have a marker (filled or
  skipped). No looping; no upselling.
- **Re-run:** see slice 017-03. Re-run reads existing markers,
  recomputes body hashes, and surfaces divergence per section.

### Question-set vs. user-words boundary

The skill **does not interpret** the user's answers beyond formatting
them into the template slots. If the user answers Q3.1 with "users
can't find regional yarn alternatives," the slot reads "users can't
find regional yarn alternatives." The skill does not paraphrase,
expand, or "improve" the answer. This is a hard rule enforced by the
SKILL.md body (and by the worked-example transcripts in 017-02).
