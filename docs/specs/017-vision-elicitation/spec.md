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

## Slice 017-01 — vision-template-and-architecture-slots

**STATUS: DONE**

**Scope:** pure template surgery. No skill yet. Lands the named-but-
empty *slots* into the templates so `scaffold-init` already produces
a project with a recognizable vision/architecture shape that a dev
can hand-fill even before 017-02 ships.

**SPIDR axis:** Data — splits the work by what artifact changes.

**Deliverables:**
- New `templates/docs/product-vision.md.template` with the 9 named
  sections (per Appendix A). Each section starts with the
  marker `<!-- elicited: PENDING / status: unfilled -->`. Section
  bodies are placeholder prose (one or two lines) plus named
  sub-bullets that make the expected shape legible to a dev who
  reads them without running the skill.
- **Reshaped** `templates/docs/architecture.md.template` to mirror
  the proven structure of jig's own
  [docs/architecture.md](../../architecture.md) — the slimmed-down
  version produced in this same session. Four elicitation slots
  (Repository structure / Tech stack / Module boundaries / Data
  model), each carrying `<!-- elicited: PENDING / status: unfilled -->`
  above placeholder prose. Two un-markered sections (Core
  architecture decisions for ADR-driven content; Open questions
  as a footer pointing to `refinement-todo.md`). A top-of-doc pointer
  to `product-vision.md` replaces the old "What this project does"
  stanza entirely — vision.md owns that question. *Why a reshape and
  not just adding markers to the old 3 stanzas: the old template was
  asking the wrong questions. "What this project does" duplicated
  vision.md; "Module boundaries" being fully deferred was the wrong
  default (every project has top-level concerns on day 1); the
  template lacked Repository structure and Data model entirely.
  Filling in jig's own arch.md proved the better shape.*
- Updated `templates/CLAUDE.md.template`: line 8 ("What this project
  does → Deferred") rewritten to reference `docs/product-vision.md`
  rather than carrying its own stub.
- New short section in `docs/conventions.md` documenting the
  elicitation marker convention (3 states: `unfilled` / `filled` /
  `skipped`; date format; hash field deferred to 017-03).

**Acceptance criteria:**
1. `templates/docs/product-vision.md.template` exists and parses as
   valid Markdown.
2. The template contains exactly 9 H2 sections in this order:
   `Identity` / `Target users` / `Core problem` /
   `Competitive landscape` / `Scope` / `Stack` /
   `Design principles & constraints` / `How new work enters` /
   `Open questions`.
3. Each H2 section's first line is the unfilled marker comment.
4. `templates/docs/architecture.md.template` is **reshaped** to four
   elicitation slots — `Repository structure` / `Tech stack` /
   `Module boundaries` / `Data model` — each carrying
   `<!-- elicited: PENDING / status: unfilled -->` immediately after
   the H2 heading. Two un-markered sections survive: `Core
   architecture decisions` (one H3 per decision, populated by ADRs
   over time) and `Open questions` (footer pointing to
   `refinement-todo.md`). The previous "What this project does"
   stanza is removed entirely; a top-of-doc preamble points to
   `product-vision.md` instead. `Tech stack` and `Module
   boundaries` retain the `> **Deferred — …**` fallback prose;
   `Repository structure` and `Data model` get positive
   placeholder prose (their "no signal" answer is rarely honest —
   every project has a layout and some state on day 1).
5. `templates/CLAUDE.md.template` line 8 references
   `docs/product-vision.md` and no longer carries a `Deferred — no
   signal` stub for project description.
6. `docs/conventions.md` documents the marker convention with the
   three states and the date format. The `hash` field is named as
   "added in 017-03" so 017-01 doesn't promise machinery it doesn't
   ship.
7. Running `scripts/scaffold.py` (or equivalent dogfood path)
   against a temp dir produces a project where
   `docs/product-vision.md` exists with the 9 unfilled-marker
   sections (per AC #2) and `docs/architecture.md` exists with the
   four unfilled slots (per AC #4 — Repository structure / Tech
   stack / Module boundaries / Data model).
8. New tests pin the section structure of both templates: parse,
   assert exact H2 list, assert marker presence on each section.

**Definition of Done:**
- [x] All ACs green.
- [x] New tests added; existing 593 still pass. (640 → 643 total green after reviewer-driven tightening.)
- [x] No regression in existing `scaffold-init` tests.
- [x] Implementation review passed. _(auto-ticks on IN_PROGRESS → REVIEWED)_
- [x] Deviation log written.
- [x] Reconciliation review passed. _(auto-ticks on REVIEWED → RECONCILED)_
- [x] Spec status board updated.

### Close-out (post-DONE)
- [x] CLAUDE.md hot-cache row for 017-01 updated.

### Deviation log (017-01)

**1. Implementer was the main agent, not the real `jig:implementer` subagent.**
Mirrors slice 013-01 §1 — work was done in the main session under
the implementer convention (TDD: red → green) but without the fresh-
context guarantee that spawning the real subagent would provide.
Implementation review (§2 below) WAS spawned as a real subagent, so
the independent-evaluation half of the spec lifecycle held.

**2. Implementation review used `general-purpose` subagent, not real `jig:reviewer`.**
This worktree is not installed as a jig plugin (`subagent-type
implementation` returned `general-purpose`). Per slice 011-02's
fallback design, this is the documented degraded mode. Review returned
`VERDICT: pass` with 5 specific issues + 4 reconciliation notes, all
addressed below.

**3. AC #4 underwent mid-implementation reshape (3 stanzas → 4 slots + 2 non-marker sections).**
After the initial template surgery landed (markers added to the old
three Deferred stanzas: "What this project does" / "Tech stack" /
"Module boundaries"), a user-led step-back surfaced that the
template itself was structurally wrong — its three placeholders
asked the wrong questions. Specifically: "What this project does"
duplicated `product-vision.md`'s job; the "Module boundaries"
Deferred default was the wrong abstraction (every project has
top-level concerns on day 1); the template lacked "Repository
structure" and "Data model" entirely. Filling in jig's own
[docs/architecture.md](../../architecture.md) earlier in the same
session proved the better shape. **The reshape replaced AC #4
wholesale**: removed the old "What this project does" stanza
(a top-of-doc pointer to vision.md does the job), kept Tech stack +
Module boundaries as elicitation slots with Deferred fallback,
added Repository structure + Data model as new elicitation slots
with positive placeholders (because "no signal" is rarely an honest
answer for those), and added a `## Core architecture decisions`
no-marker section for ADR-driven content. Spec text + tests + the
template were all updated together to keep them consistent.

**4. AC #6 (conventions.md) required the documented `JIG_CONVENTIONS_APPROVED=1` escape.**
The `jig-spec-gate` hook + Claude Code's auto-mode classifier both
refused the convention-file edit until the user gave explicit
in-the-moment approval. This is the gate working as designed — slice-
level approval ("yes, implement 017-01") does not cascade to
convention-level approval. The edit landed once the user authorized
the documented bypass. No deviation in the *outcome*; recording the
*path* in case the gate pattern recurs.

**5. Reviewer-driven test tightening (4 specific findings addressed).**
The implementation reviewer flagged (a) AC #7 spec text was stale
("three unfilled slots" — pre-reshape phrasing); (b) the
conventions.md test was substring-only and didn't pin the rule body;
(c) the scaffold-dogfood test only covered the vision side, missing
architecture.md; (d) no test pinned exact-marker-count, so a
duplicated marker or marker on a wrong section would pass. All four
addressed before requesting reconciliation: spec text corrected in
AC #7, `test_conventions_md_documents_marker_convention` rewritten
to anchor on the rule heading + assert the three states + marker
prefix + 017-03 hash reference appear *inside* the rule block,
`test_scaffold_produces_product_vision_md` extended to also verify
the scaffolded architecture.md has all 4 markers + all 4 named
slots present, and new `test_architecture_template_has_exactly_four_markers`
pins the count. Test count: 640 → 643.

**6. Appendix A heading-name drift fixed.**
Reviewer also flagged that Appendix A's "Produces:" lines named
section headings that didn't match the vision template's actual
H2s ("## Vision statement" vs template's `## Identity`; "## The
core problem" vs template's `## Core problem`; "## Core features
(prioritized), ### MVP scope, ..." vs template's `## Scope` with
4 H3 sub-sections; "## Design principles" vs template's
`## Design principles & constraints`). Out of slice 017-01's
strict scope but fixed inline — leaving the drift would have
trapped the 017-02 implementer. Vision template wasn't touched
(scope was arch template only).

**7. Vision template's Stack section is currently un-mapped to any Q&A section.**
Side-effect of the AC #4 reshape: Q&A Section 7 (Tech stack) now
produces *only* arch.md's Tech stack slot. The vision template's
`## Stack` H2 (unchanged from the original 9-section design)
has no elicitation producer. **Intentional, not a defect** — Stack
content varies between vision (high-level platform framing) and
arch (concrete runtime/db). Future work in 017-02 may either
(a) have Section 7 dual-write to both slots, or (b) reshape vision
template to drop the Stack section. Not blocking this slice; logged
here so the 017-02 designer sees the choice point.

**8. Reconciliation reviewer caught stale stanza list in conventions.md.**
The first reconciliation review returned `VERDICT: needs-changes`
flagging that the "Elicitation slots" rule's "How to apply:" line in
`docs/conventions.md:81` still named the **pre-reshape** stanza list
("The three Deferred stanzas in `templates/docs/architecture.md.template`
(What this project does / Tech stack / Module boundaries)"). The rule
that 017-01 *introduces* was inconsistent with the deliverable that
017-01 *ships* — the very kind of self-contradiction the slice's own
reshape was supposed to eliminate. Same flavor of staleness the
implementation reviewer caught at AC #7 (§5(a)) on the spec-doc side,
but on the conventions-doc side. **Fixed inline** before requesting a
second reconciliation review: the line now reads "The four elicitation
slots in `templates/docs/architecture.md.template` (Repository
structure / Tech stack / Module boundaries / Data model) each carry
the same marker; two sibling sections (Core architecture decisions,
Open questions) deliberately carry no marker — they're populated by
ADRs over time and by `refinement-todo.md` references, respectively."
The tightened `test_conventions_md_documents_marker_convention` (§5)
continues to pass — it anchors on rule heading + 3 lifecycle states
+ marker prefix + 017-03 hash reference, none of which the stanza-
list rewrite affects.

## Slice 017-02 — vision-elicitation-skill-core

**STATUS: DONE**

**Scope:** the elicitation skill itself, first-run only. Asks the
12 sections per Appendix A in order, writes captured answers into
the template slots created by 017-01. No re-run smarts yet — that's
017-03.

**SPIDR axis:** Interface — splits the work by adding the user-facing
trigger surface on top of 017-01's data scaffolding.

**Deliverables:**
- New `skills/vision-elicitation/SKILL.md` with frontmatter
  (`name: vision-elicitation`, judgment-only, no `.py` helper).
  Description includes a category-based deferral hint matching the
  pattern from `pr-review` (012-01) and `arch-review` (014-01).
- New `skills/vision-elicitation/questions.md` shipping the 12-section
  question set verbatim from Appendix A. Loaded on-trigger via
  progressive disclosure.
- New `skills/vision-elicitation/worked-example-jig.md` —
  annotated transcript that traces each section of the hand-seeded
  [docs/product-vision.md](../../product-vision.md) back to the
  elicitation questions that would have produced it.
- New `skills/vision-elicitation/worked-example-yarnfinder.md` —
  same for the YarnFinder pitch in `/Users/ramboz/Projects/CLAUDE.md`.
  Two project shapes (dev-tooling vs. consumer-product) keep the
  question set honest.
- SKILL.md body documents the per-section flow (per the Path SPIDR
  decision: each section is independently answerable, skippable,
  and re-runnable).
- On first run: writes answers into the unfilled-slot template
  produced by 017-01, transitioning each filled section's marker
  from `status: unfilled` to `status: filled`. Skipped sections
  transition to `status: skipped`.
- Also updates `docs/architecture.md` slots using the answers from
  Sections 6 (Repository structure) / 7 (Tech stack) / 8 (Module
  boundaries) / 9 (Data model) / 12 (Open questions). Each
  architecture slot maps 1:1 to its elicitation section, so a user
  can skip any individual slot without losing the others. The
  "What this project does" stanza no longer exists in the template
  (slice 017-01 reshape) — vision.md owns it.

**Acceptance criteria:**
1. `skills/vision-elicitation/SKILL.md` ships with the required
   frontmatter and a description that includes:
   (a) trigger phrases ("set up project vision", "elicit
   architecture", "define what we're building"),
   (b) explicit reference to the templates from slice 017-01 as the
   output shape,
   (c) category-based deferral hint (any user-installed skill whose
   description identifies it as handling vision elicitation,
   product discovery, or project framing wins).
2. `skills/vision-elicitation/questions.md` exists and contains the
   12 sections from Appendix A, with question text matching verbatim.
3. Both worked-example transcripts exist and walk through their
   respective pitches section by section, showing question →
   answer → rendered section heading + body.
4. **Structural-match dogfood (worked example #1):** the worked
   example transcript for the jig pitch produces an output document
   whose H2 section structure matches the **vision template**
   (`templates/docs/product-vision.md.template`) — i.e. the 9 H2s
   `Identity / Target users / Core problem / Competitive landscape /
   Scope / Stack / Design principles & constraints / How new work
   enters / Open questions`. The worked example MUST acknowledge
   the divergence from the hand-seeded `docs/product-vision.md`
   (which predates the template and uses bespoke H2 names like
   "Vision statement" / "Future scope" / "References") — annotating
   the content-to-slot mapping makes the divergence explicit.
5. **Structural-match dogfood (worked example #2):** the worked
   example transcript for the YarnFinder pitch produces an output
   document whose H2 section structure also matches the vision
   template's 9 H2s (same as AC #4 — the elicitation skill is
   template-driven, so all outputs have the same H2 shape regardless
   of project). The worked example MUST acknowledge how YarnFinder's
   bespoke concepts from `/Users/ramboz/Projects/CLAUDE.md` (Data
   sourcing, Recommended slice order, prioritized backlog, etc.)
   map to the template's slots — Data sourcing → How new work
   enters; prioritized backlog → Scope > Core features; Recommended
   slice order → Scope > (Tiers / phases or Out of scope as
   appropriate).
6. After a first run, the resulting `docs/product-vision.md` has
   every section marker transitioned away from `status: unfilled`
   (each is either `status: filled` or `status: skipped`).
7. The `docs/architecture.md` four elicitation slots (Repository
   structure / Tech stack / Module boundaries / Data model) are
   each filled from their corresponding Q&A section (6 / 7 / 8 / 9
   in the new 12-section question set). For each slot: if the user
   answered, the slot transitions from `status: unfilled` to
   `status: filled` and the body is rendered from the user's words;
   if the user skipped, the slot transitions to `status: skipped`
   and the existing placeholder/Deferred prose is retained
   verbatim.
8. Surface tests pin: frontmatter fields, description category-
   deferral phrasing, questions.md section structure, SKILL.md
   per-section flow markers. Anti-greediness `DescriptionBoundsTests`
   class (same shape as pr-review) pins the description against
   over-claim phrases like "best vision elicitation" or
   "comprehensive product discovery".
9. **Routing dogfood:** in a fresh session, an "elicit project
   vision" or "let's define what we're building" prompt triggers
   `/jig:vision-elicitation` (or defers to a user-installed
   category-equivalent if one is present). Like pr-review and
   arch-review, this dogfood lands as a post-merge close-out item;
   AC #9 fallback (`disable-model-invocation: true`) is held in
   reserve.

**Definition of Done:**
- [x] All ACs 1–8 green pre-merge; AC #9 deferred to post-merge close-out.
- [x] New surface tests green; no regression in existing suite. (659 → 695 total green; +36 from `VisionElicitationSkillSurfaceTests`.)
- [x] Implementation review passed. _(auto-ticks on IN_PROGRESS → REVIEWED)_
- [x] Deviation log written.
- [x] Reconciliation review passed. _(auto-ticks on REVIEWED → RECONCILED)_
- [x] Spec status board updated.

### Close-out (post-DONE)
- [ ] Routing-dogfood verification (AC #9) in a fresh session — does an "elicit project vision" prompt trigger `/jig:vision-elicitation`?
- [x] CLAUDE.md hot-cache row for the new skill.

### Deviation log (017-02)

**1. AC #4 and AC #5 reworded mid-implementation (template-shape ground truth).**
The original ACs claimed the worked examples would match the
hand-seeded `docs/product-vision.md` byte-for-byte in H2 structure.
While drafting the jig worked example, the implementer discovered
the hand-seeded file uses bespoke H2 names ("Vision statement",
"The core problem", "Future scope", "References") that diverge
from the vision **template**'s H2 names ("Identity", "Core problem",
"Stack", "Open questions" — slice 017-01 deliverable). Because the
elicitation skill is template-driven (it reads the template's H2s
and writes between them), its output can only match the template,
not the hand-seeded file. **The original AC was unachievable as
written.** Reworded both ACs to require template-shape output +
explicit acknowledgment of the divergence + (for YarnFinder) a
concept-to-slot mapping table. The reworded ACs improved the slice
— the worked-example-yarnfinder.md concept-to-template mapping
table is more useful guidance for the 017-03 implementer than a
byte-for-byte structural-match check would have been.

**2. Implementation reviewer caught a stale "byte-for-byte" claim
in SKILL.md that contradicted the AC #4 reword.**
Third instance (after 017-01 §5(a) and 017-01 §8) of the
"reshape/reword didn't propagate to all consuming sentences"
pattern. SKILL.md:177 claimed the jig worked example "Produces
output matching the hand-seeded `docs/product-vision.md`
byte-for-byte in H2 section structure" — that's the pre-reword
text. The actual worked-example-jig.md correctly produces
template-shaped output and annotates the divergence. **Fixed
inline**: SKILL.md rewritten to describe template-shaped output
with explicit hand-seeded divergence acknowledgment. **New
regression test landed**:
`test_worked_examples_section_acknowledges_template_shape` pins
the worked-examples section against the recurrence — must mention
"template", must NOT contain "byte-for-byte". Test count: 35 → 36
in the vision-elicitation surface suite; 694 → 695 overall.

**3. Test file renamed: `test_skill_surface.py` → `test_vision_elicitation_skill_surface.py`.**
Mirrors arch-review's precedent (`test_arch_review_skill_surface.py`).
The unprefixed name collided with pr-review's same-named test file
at unittest-discover time (pytest discovery would also fail).
Asymmetry: pr-review still uses the unprefixed `test_skill_surface.py`
— a follow-up consistency rename is a plausible refinement-todo
entry but is correctly out of scope for this slice. Reviewer noted
the rename was principled.

**4. Implementer was the main agent, not the real `jig:implementer` subagent.**
Mirrors slice 017-01 §1 and the broader pattern across 013-01,
007-01, etc. Work was done in the main session under the
implementer convention (TDD: red → green) but without the fresh-
context guarantee that spawning the real subagent would provide.
Implementation review (§5 below) WAS spawned as a real subagent,
so the independent-evaluation half of the spec lifecycle held.

**5. Implementation review used `general-purpose` subagent, not real `jig:reviewer`.**
This worktree is not installed as a jig plugin (`review.py
subagent-type implementation` returns `general-purpose`). Per
slice 011-02's fallback design, this is the documented degraded
mode. Review returned `VERDICT: needs-changes` with one specific
issue (the SKILL.md stale claim — §2) and three reconciliation
notes (template-shape principle worth recording — addressed via
§1; rename principled — §3; pr-review consistency rename worth a
refinement-todo entry — see §6 below). All findings addressed
before requesting reconciliation review.

**6. Refinement-todo candidate: pr-review test file rename for consistency.**
Reviewer surfaced (in reconciliation notes) that pr-review still
uses the unprefixed `test_skill_surface.py` while arch-review and
now vision-elicitation use the `test_<skill_name>_skill_surface.py`
shape. A follow-up consistency rename of pr-review's file is
plausible but out of scope for this slice. **Not recording in
refinement-todo.md inside this slice's deliverable surface** (would
expand the diff beyond slice scope and require gate approval since
`docs/conventions.md`-adjacent files share the gate); the entry
should land in a follow-up commit if and when a real friction
appears (e.g. a third same-named test file is added).

## Slice 017-03 — re-runnable-with-edit-detection

**STATUS: READY_FOR_REVIEW**

**Scope:** re-run mechanics. The skill must detect manual edits
between runs and warn before overwriting them. Adds the `hash` field
to the marker convention; teaches the skill to read existing markers,
recompute body hashes, and surface divergence to the user.

**SPIDR axis:** Rules — splits the work by adding behavior over the
same surface from 017-02.

**Deliverables:**
- SKILL.md body extended with a "Re-run protocol" section: read
  existing marker → compute current body hash → compare against
  marker's `hash` field → if divergent, surface
  `manual edits detected in section <N> — refresh anyway? [y/N/diff]`.
- Marker convention extended in `docs/conventions.md`: `hash` field
  now required for `status: filled` sections; format is
  `sha256:<first-12-hex>` of the section body (trimmed; bytes
  between the marker line and the next H2 heading).
- Per-section refresh supported: `/jig:vision-elicit --section
  "Core problem"` (or its skill-form equivalent — exact CLI shape
  is implementer's call).
- New worked-example transcript:
  `skills/vision-elicitation/worked-example-rerun.md` showing a
  re-run against jig's own vision doc with one section manually
  edited; skill warns; user confirms; section refreshed; hash
  updated.

**Acceptance criteria:**
1. SKILL.md body contains a "Re-run protocol" section documenting
   the four-step flow (read marker → compute hash → compare →
   surface decision).
2. `docs/conventions.md` marker convention now specifies the `hash`
   field format for `filled` sections.
3. Re-run on a vision doc with no manual edits is silent: no
   warning, only the actual re-elicited-section diffs are surfaced.
4. Re-run on a vision doc with one manually-edited section warns
   before that section is touched. The warning quotes the section
   heading and offers three choices: refresh / skip / diff.
5. Per-section refresh is documented in SKILL.md.
6. Worked-example transcript demonstrates a divergence detection
   end-to-end.
7. Surface tests pin the re-run flow markers in SKILL.md and the
   hash format string in conventions.md.

**Definition of Done:**
- All ACs green.
- New surface tests green; no regression.
- Implementation review passes.
- Reconciliation review passes.
- Spec status board updated.
- Close-out (post-DONE): CLAUDE.md hot-cache row for 017-03 updated.

## Slice 017-04 — seed-ADR-pass

**STATUS: DEFERRED** _(deferred — optional optimization, gated on real usage signal)_

**Resolution trigger:** First 5 real `/jig:vision-elicit` runs after 017-02 lands. If >25% of those runs name an explicit locked-in decision during Section 6 (Stack) elicitation that the user would have wanted auto-scaffolded as an ADR, promote 017-04 to DRAFT. If <25%, deferral becomes permanent — the elicitation output already names decisions inline and ADR seeding can stay manual.

**Goal:** when the user names a decision during Section 6 (Stack)
elicitation, the skill scaffolds a draft ADR via
`/jig:adr-workflow new` rather than just writing a sub-bullet.

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
