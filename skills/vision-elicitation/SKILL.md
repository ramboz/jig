---
name: vision-elicitation
description: >
  Lightweight baseline elicitation pass that fills in `docs/product-vision.md`
  and the four `docs/architecture.md` elicitation slots after `scaffold-init`.
  Auto-triggers when you say set up project vision, elicit architecture,
  define what we're building, run the vision wizard, refresh the project
  pitch, or capture product scope. Defers to any other installed skill whose
  description identifies it as handling vision elicitation, product
  discovery, project framing, or product scope capture — if such a skill is
  present, prefer it over this one (jig's version is a slim baseline). Does
  not defer to the generic built-in `init` skill. Do not use for: ad-hoc
  brainstorming with no `docs/product-vision.md` slot to write into;
  rewriting vision content the user has already hand-edited (use the 017-03
  re-run path with edit detection once that ships); spec authoring (use
  `/jig:spec-workflow`); seeding ADRs for already-named decisions (use
  `/jig:adr-workflow new`).
user-invocable: true
---

> Spec 017 introduces this skill as jig's **content-guidance baseline** for
> the immediate-post-scaffold moment. It is the third non-stub active jig
> skill that ships without a `.py` helper — vision-elicitation is
> fundamentally a judgment skill, and the determinism it needs (find the
> elicitation slots, transition markers, render Q&A into template bodies)
> Claude can run inline via Read/Edit. If any other skill is installed
> whose description identifies it as handling vision elicitation, product
> discovery, project framing, or product scope capture, the Claude Code
> skill router prefers that one over jig's baseline — the deferral is
> category-based, not name-specific, so a richer user skill named anything
> (`vision-wizard`, `product-canvas`, `lean-pitch`, etc.) wins. Jig's slim
> version remains the auto-trigger when no such skill is installed.

## What this skill does

Runs a structured 12-section Q&A immediately after `scaffold-init`, then
writes the captured answers into the elicitation slots that slice 017-01
introduced:

- `docs/product-vision.md` — 9 H2 sections (Identity, Target users, Core
  problem, Competitive landscape, Scope, Stack, Design principles &
  constraints, How new work enters, Open questions). Each section's
  `<!-- elicited: PENDING / status: unfilled -->` marker transitions
  to `status: filled` (with today's ISO date) or `status: skipped`.
- `docs/architecture.md` — 4 elicitation slots (Repository structure,
  Tech stack, Module boundaries, Data model). Same marker transition.
  Two sibling sections (Core architecture decisions, Open questions)
  carry no markers and are populated by ADRs / refinement-todo entries
  over time, not by elicitation.

The 12 Q&A sections map 1:1 to vision + arch slots (5 sections feed
vision-only slots, 4 sections feed arch-only slots, 1 section feeds
the refinement-todo entries that the arch Open questions footer points
to, and 2 sections feed vision-only slots that don't have a single-slot
mirror — see [`questions.md`](questions.md) for the canonical mapping).

The skill is **breadth over depth**: catch the essentials of what the
user wants to build, leave deeper product-discovery facilitation
(lean-canvas workshops, multi-persona scoping, prioritization frameworks)
to a richer user-installed skill at the discovery surface.

## When to use vs. when to defer

There are four things people often confuse with this skill. Pick the right
one:

- **Any other user-installed vision-elicitation / product-discovery /
  project-framing skill.** Common locations include
  `~/.claude/skills/vision-elicitation/`, `~/.claude/skills/product-canvas/`,
  `~/.claude/skills/lean-pitch/`, etc. — but the deferral is
  **category-based, not name-based**, so a skill named anything whose
  description claims vision elicitation, product discovery, project
  framing, or product scope capture will be preferred. If one is present,
  **defer to it.** The one exception jig's description carves out is the
  bundled `init` skill — jig:vision-elicitation does **not** defer to that
  one (it's the generic CLAUDE.md-bootstrap helper, a different surface).
- **`/jig:spec-workflow`** — sibling jig skill for **spec authoring**
  (drafting a slice, SPIDR-splitting features, transitioning state
  markers). That's about *what we'll build next*. This skill is about
  *what the project is fundamentally* — the substrate spec-workflow runs
  on top of. Reach for `/jig:spec-workflow` when you have a feature in
  mind and need to author a slice. Reach for this skill when the project's
  identity, target users, core problem, or architectural shape isn't yet
  captured in `docs/product-vision.md` / `docs/architecture.md`.
- **`/jig:adr-workflow new`** — for seeding ADRs from decisions the user
  has already named. If the user comes in saying "we've decided on
  SQLite, let's write that down," that's an ADR job, not vision
  elicitation. Slice 017-04 (deferred) will add an optional seed-ADR
  pass at the end of this skill's Section 7 (Tech stack); until then,
  ADRs are seeded by hand via `/jig:adr-workflow new`.
- **`/jig:scaffold-init`** — the install-time wizard that produces the
  empty slots this skill fills. `scaffold-init` runs once; this skill
  runs after, can be re-run, and produces the substantive content.

Rule of thumb: **empty slot → this skill. Named decision → adr-workflow.
Feature scope → spec-workflow. Empty repo → scaffold-init.**

## How the elicitation works

The skill is **judgment-only** — no `.py` helper. Claude reads the
question set, conducts the Q&A inline with the user, and writes the
rendered answers via the Edit tool. The per-section flow is:

1. **Load the question set** from [`questions.md`](questions.md). 12
   sections; each lists 1–4 questions plus optional follow-ups.
2. **Detect existing markers.** Open the project's
   `docs/product-vision.md` and `docs/architecture.md`. Find each
   section's `<!-- elicited: ... -->` marker. Today (017-02): only
   sections with `status: unfilled` are candidates for elicitation;
   `status: filled` or `status: skipped` sections are passed over.
   (Slice 017-03 adds re-run mechanics with hash-based edit detection.)
3. **For each candidate section, ask the questions in order.** Let the
   user answer, skip, or come back later. A user can answer "skip" to
   transition the section to `status: skipped` without filling it.
4. **Render the answer into the template slot.** Replace the
   placeholder prose between the marker and the next H2 with the
   user's words. Update the marker:
   - Answered → `<!-- elicited: YYYY-MM-DD / status: filled -->`
   - Skipped → `<!-- elicited: YYYY-MM-DD / status: skipped -->`
5. **Move to the next section.** No looping; no upselling; stop when
   all 12 sections have been visited.

### Per-section flow, not per-question flow

The Path SPIDR decision (spec 017's SPIDR table) is per-section.
Each *section* is independently skippable and re-runnable; *individual
questions within a section* are not their own skip-units. If a user
wants to answer Q7.1 but skip Q7.2, the skill should still write the
Q7.1 answer into the Tech stack slot, then move to Section 8 — not
treat that as a half-filled section.

## Inputs

Three input modes, ordered by richness:

1. **Full session context (preferred).** You're inside a Claude Code
   session at the project root, with `docs/product-vision.md` and
   `docs/architecture.md` on disk from `scaffold-init`. The user can
   answer questions interactively; you write to disk as each section
   completes.
2. **Pitch-document context.** The user pasted or pointed at a project
   pitch (e.g. `/Users/ramboz/Projects/CLAUDE.md` for YarnFinder; a
   README; a one-pager). Use the pitch to ground the questions but
   still ask the user — the skill does not auto-fill from a pitch
   alone (the user's voice in the final doc matters).
3. **No prior pitch.** Start cold. The first Section (Identity) is
   load-bearing in this case — the rest of the elicitation flows from
   the one-sentence answer to Q1.1.

## Rendering rule: the skill writes the user's words

**The skill does not paraphrase, expand, or "improve" the user's
answers.** If Q3.1 is "describe the problem in 2–3 sentences" and the
user answers "crafters can't find regional yarn alternatives," the slot
reads "crafters can't find regional yarn alternatives." Not "Crafters in
non-US regions face difficulty locating equivalent yarn substitutes for
US-sourced patterns." The skill's job is to ask, not to interpret.

This is a hard rule. It's enforced inline by the worked-example
transcripts ([worked-example-jig.md](worked-example-jig.md) and
[worked-example-yarnfinder.md](worked-example-yarnfinder.md)) — both
demonstrate the user's literal words rendered into the slot.

Two narrow exceptions:
- **Markdown structure.** The skill formats answers as bullet lists,
  tables, or sub-bullets where the template prescribes that shape
  (e.g. the Competitive landscape table). The user's *content* is
  unchanged; only the markdown around it is added.
- **Section ordering.** If a user's answer to Q5.1 (core features)
  enumerates 5 items in priority order, the skill writes them in that
  order. The skill never reprioritizes.

## Worked examples

Two annotated transcripts ship with this skill:

- [`worked-example-jig.md`](worked-example-jig.md) — runs the
  elicitation against jig's own pitch (the README's "what it does"
  + the audit-stage positioning recovery story). Produces
  **template-shaped output** with the 9 H2s defined by
  `templates/docs/product-vision.md.template` (Identity / Target
  users / Core problem / Competitive landscape / Scope / Stack /
  Design principles & constraints / How new work enters / Open
  questions). The worked example explicitly acknowledges the H2-name
  divergence from the hand-seeded `docs/product-vision.md` (which
  predates the template and uses bespoke H2 names like "Vision
  statement" / "Future scope" / "References"). **The template is
  the structural ground truth for elicitation output shape** — if
  the skill produces H2s that don't match the template, something
  is wrong.
- [`worked-example-yarnfinder.md`](worked-example-yarnfinder.md) —
  runs the elicitation against the YarnFinder pitch described in
  `/Users/ramboz/Projects/CLAUDE.md`. Demonstrates a different
  project shape (consumer product vs. dev tooling) and shows how
  YarnFinder's bespoke concepts (Data sourcing, Recommended slice
  order, prioritized backlog) map to the template's slots. Two
  shapes keep the question set honest.

## Gotchas

- **The deferral hint is the routing mechanism, not a code path.**
  Same as pr-review and arch-review: jig's description tells the
  Claude Code router "prefer any other installed skill whose
  description identifies it as handling vision elicitation, product
  discovery, project framing, or product scope capture." There is no
  filesystem probe, no plugin-precedence lookup. The deferral is
  category-based: a user skill named anything that claims the
  discovery / framing surface will win.
- **Lightweight is a feature.** This baseline does not run multi-
  persona facilitation, does not impose a lean-canvas template, does
  not produce a JTBD framework artifact. If you find yourself wishing
  the baseline did more, you are in the target audience for installing
  a richer skill at the user scope.
- **No state machine.** This skill does not transition spec slice
  state markers (that's `spec-workflow`), does not write ADRs (that's
  `adr-workflow new`), and does not enforce the conventions gate
  (that's `jig-spec-gate`). It only writes content into the slots that
  slice 017-01 introduced.
- **Re-runs are 017-03's job.** Today (017-02) the skill is first-run
  only. Sections already marked `status: filled` or `status: skipped`
  are passed over; the skill does not detect or warn on manual edits
  between runs. Once slice 017-03 ships, hash-based edit detection
  lets the skill detect divergence and offer refresh / skip / diff
  per-section.
- **Fallback mode** (if the routing-dogfood in spec 017-02's AC #9
  ever fails): the SKILL.md frontmatter gets `disable-model-invocation:
  true` and this skill becomes explicit-invocation-only
  (`/jig:vision-elicitation`). In that mode, no auto-trigger fires —
  the user has to type the slash command. If you see
  `disable-model-invocation: true` in this skill's frontmatter,
  that's why.

## Relationship to other skills

- **`/jig:scaffold-init`** — produces the empty slots this skill
  fills. The two skills compose: scaffold-init creates the templates,
  vision-elicitation populates them.
- **`/jig:spec-workflow`** — sibling. Spec-workflow drives the
  what-we-build-next surface; this skill defines the what-the-project-
  is surface that spec-workflow operates within.
- **`/jig:adr-workflow new`** — produces ADRs from named decisions.
  Slice 017-04 (deferred) will add an optional seed-ADR pass at the
  end of Section 7 (Tech stack) that calls `adr-workflow new` for any
  locked-in decision the user names. Until 017-04, ADR seeding stays
  manual.
- **`/jig:memory-sync`** — orthogonal. Memory-sync captures
  cross-session learnings (hot cache, glossary, learnings); this
  skill captures project-level positioning. Different surfaces.
