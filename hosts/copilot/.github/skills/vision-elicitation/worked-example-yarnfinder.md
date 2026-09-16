# Worked example: vision-elicitation against the YarnFinder pitch

> **Purpose.** Demonstrates the 12-section Q&A flow run against a
> **consumer product** pitch (different shape from jig's dev-tooling
> shape — see [`worked-example-jig.md`](worked-example-jig.md)). The
> two worked examples together keep the question set honest:
> dev-tooling stresses *design-principles* and *non-goals* questions;
> consumer-product stresses *data-sourcing* and *MVP-vs-future*
> questions.
>
> **Source pitch.** The YarnFinder project description in
> `/Users/ramboz/Projects/CLAUDE.md` — a regional yarn matching
> platform for knitters and crocheters. See that file for the
> full pitch + the prescribed `docs/product-vision.md` content
> sections.
>
> **Structural acknowledgment.** Same as the jig worked example —
> the elicitation skill is **template-driven**. YarnFinder's CLAUDE.md
> prescribes bespoke vision sections (Vision statement / Target
> users / Core problem / Competitive landscape summary / prioritized
> backlog / MVP scope / Future scope / Data sourcing / Recommended
> slice order). These map to the **template's 10 H2s** (incl. the
> `## Use cases` breadth section), not the other way around. This
> worked example shows the mapping inline.

## Concept-to-template mapping (the load-bearing piece)

YarnFinder's CLAUDE.md names 9 sections it wants in product-vision.md:

| YarnFinder CLAUDE.md concept | Template slot | How it maps |
|---|---|---|
| Vision statement | `## Identity` (Q1.1 answer) | Direct — template's Identity opens with the vision statement |
| Target users | `## Target users` (Q2.1 + Q2.2) | Direct |
| The core problem | `## Core problem` (Q3.1 + Q3.2) | Drop article; template uses bare "Core problem" |
| Competitive landscape summary | `## Competitive landscape` (Q4.x) | Direct — template's table format |
| Prioritized backlog (8 items) | `## Scope` > `### Core features (prioritized)` (Q5.1) | YarnFinder's 8-item backlog renders as the H3 sub-section |
| MVP scope (features 1-4) | `## Scope` > `### MVP scope` (Q5.3) | Direct — explicit MVP sub-section in the template |
| Future scope (features 5-8) | `## Scope` > (note about deferred features) | Template's Scope bucket absorbs both MVP and future via Q5.3 |
| Data sourcing | `## How new work enters` (Q11.1 + Q11.2) | YarnFinder's "where data comes from" maps to the vision-level "how new content enters the system" question |
| Recommended slice order | `## Scope` > `### Tiers / phases` (Q5.2) | YarnFinder's phasing recommendation renders as the optional Tiers/phases H3 |

This mapping is the **answer to AC #5**: the elicitation skill does
not produce YarnFinder's bespoke H2 names — it produces the template
H2s, with YarnFinder's content distributed into the appropriate slots.
(The 10th template H2, `## Use cases`, has no YarnFinder-named concept to
map from — like `## Stack` / `## Design principles` / `## Open questions`
it is filled by its own elicitation: the **Use cases capture loop**,
demonstrated below.)

## The 12-section walk-through

### Section 1 — Identity

**Skill asks Q1.1:** *"In one sentence, what does this project do?"*

**User answers:** *"YarnFinder lets crafters (knitters/crocheters)
in non-US regions find regional yarn alternatives matched to the
yarns called for in US-based patterns."*

**Skill asks Q1.2 (optional tagline) and Q1.3 (positioning story):**
*(user skips both)*

**Skill renders into `## Identity`:**

```markdown
## Identity

<!-- elicited: 2026-05-15 / status: filled -->

- **Vision statement:** YarnFinder lets crafters (knitters/crocheters)
  in non-US regions find regional yarn alternatives matched to the
  yarns called for in US-based patterns.
```

### Section 2 — Target users

**Skill asks Q2.1, Q2.2:**

**User answers:**
- For: Crafters who follow patterns with US-sourced yarns but live outside the US (Europe, Asia, Oceania); pattern designers who want regional substitution guidance
- Not for: US-only crafters; quilters or other fiber-arts users with different substitution needs

**Skill renders into `## Target users`:**

```markdown
## Target users

<!-- elicited: 2026-05-15 / status: filled -->

**For:**
- Crafters who follow patterns with US-sourced yarns but live outside
  the US (Europe, Asia, Oceania)
- Pattern designers who want regional substitution guidance

**Not for:**
- US-only crafters (existing tools serve this market)
- Quilters or other fiber-arts users with different substitution needs
```

### Section 3 — Core problem

**Skill asks Q3.1, Q3.2:**

**User answers:**
- Problem: Most knitting/crochet patterns reference US-based yarns. Crafters in Europe, Asia, and elsewhere struggle to find exact matches.
- Paths today: Manual research on pattern forums (slow, inconsistent); YarnSub (substitution but no regional filter); Ravelry (yarn data but no regional matching)

**Skill renders into `## Core problem`:**

```markdown
## Core problem

<!-- elicited: 2026-05-15 / status: filled -->

Most knitting/crochet patterns reference US-based yarns. Crafters in
Europe, Asia, and elsewhere struggle to find exact matches — the
yarns called for simply aren't available regionally.

**Today's paths and where they fall short:**
1. Manual research on pattern forums — slow, inconsistent answers
2. YarnSub — does substitution but no regional filtering
3. Ravelry — has yarn data but no regional matching
```

### Section 4 — Competitive landscape

**Skill asks Q4.1, Q4.2, Q4.3, Q4.4:**

**User answers:**
- YarnSub: substitution algorithm; lacks regional availability filter
- Ravelry: yarn metadata + community; no automatic regional matching
- Forum threads: tailored answers; doesn't scale, doesn't index
- Where YarnFinder fits: regional-availability-first substitution engine

**Skill renders into `## Competitive landscape`:**

```markdown
## Competitive landscape

<!-- elicited: 2026-05-15 / status: filled -->

| Option | What it does | Where it falls short for this gap |
|---|---|---|
| YarnSub | Substitution algorithm | No regional availability filter |
| Ravelry | Yarn metadata + community | No automatic regional matching |
| Pattern forum threads | Tailored answers per query | Doesn't scale, doesn't index |

**Where YarnFinder fits:** a regional-availability-first substitution
engine — the only one that filters matches by where the crafter lives.
```

### Section 5 — Scope

**Skill asks Q5.1 (priority order), Q5.2 (tiers/phases), Q5.3 (MVP), Q5.4 (out-of-scope):**

**User answers** (taking the prioritized backlog from CLAUDE.md):

1. Yarn database with standardized attributes
2. Search by similarity (regional matches ranked by closeness)
3. Regional availability filtering
4. Minimal web UI (search form, results, retailer links)
5. Community contributions (users add yarns + regional availability)
6. Pattern import (paste URL or text, extract requirements)
7. User accounts (saved searches, favorites)
8. Community ratings

- Tiers/phases: yes — MVP (1-4), v2 (5-6), v3 (7-8). Slice order: 1 → 2 → 3 → 4 → 5/6 in parallel → 7 → 8.
- MVP: features 1-4 only
- Out of scope: yarn-shop e-commerce; pattern marketplace; non-yarn fiber arts (quilting, etc.)

**Skill renders into `## Scope`:**

```markdown
## Scope

<!-- elicited: 2026-05-15 / status: filled -->

### Core features (prioritized)

1. Yarn database with standardized attributes (weight, fiber, gauge,
   yardage, color, region, price)
2. Search by similarity — input a yarn, get regional matches ranked
3. Regional availability filtering — filter by country/region
4. Minimal web UI — search form, results list, retailer links
5. Community contributions — users add yarns with regional availability
6. Pattern import — paste URL or text, extract yarn requirements
7. User accounts — saved searches, favorited yarns, tracked substitutions
8. Community ratings — let users rate substitution quality

### Tiers / phases

MVP (features 1-4) → v2 (features 5-6) → v3 (features 7-8).
**Recommended slice order:** 1 → 2 → 3 → 4 → 5/6 in parallel → 7 → 8.

### MVP scope

Features 1-4 only (database + similarity + region filter + basic UI).

### Out of scope (deliberately)

- Yarn-shop e-commerce — match guidance, not retail
- Pattern marketplace — substitution, not pattern hosting
- Non-yarn fiber arts (quilting, embroidery, etc.)
```

**Note:** YarnFinder's "prioritized backlog" + "MVP scope" +
"Future scope" + "Recommended slice order" all live inside the
template's `## Scope` bucket. The Tiers/phases H3 absorbs the
recommended slice order — that's the mapping AC #5 prescribes.

### Use cases capture *(conversational loop — slice 068-01)*

> **This is the load-bearing 068-01 demonstration.** After Scope, the skill
> fills the `## Use cases` section with a **conversational capture loop**, not
> the rigid per-section Q&A. YarnFinder is behavior-dense (a consumer product),
> so it stresses the loop well. The four steps below show **any-shape capture +
> loop to exhaustion**, a **single normalize pass**, **confirm-before-write with
> an edit round-trip**, and the **no-silent-inference question**.

**Step 1 — Capture (any shape, loop to exhaustion).**

**Skill:** *"List the user-facing behaviors — what can someone actually do with
YarnFinder? Type them one at a time or paste a list; goal-level, `[actor] can
[goal]`."*

**User pastes a bulk list:**
- a crafter can search for a yarn by name
- a crafter can see regional matches ranked by closeness
- a crafter can filter matches to their own country

**Skill asks:** *"Anything else?"*

**User (incrementally):** *"a crafter can open a retailer link for a match"*

**Skill asks again:** *"Anything else?"*

**User:** *"a crafter can search for a yarn and filter by region in one step —
done."*

The skill **loops on "anything else?" until the user signals done** — accepting
both the bulk paste and the later incremental additions.

**Step 2 — Normalize (a single pass).** The skill runs **one** normalize pass:

- **Dedupe:** the last entry ("search … and filter by region in one step")
  duplicates the existing search + filter behaviors — folded out.
- **Split compound:** none remaining after the dedupe (the compound entry was
  the duplicate).
- **Rephrase to goal-level:** all already in `"[actor] can [goal]"` form.

**Step 3 — Confirm before any write (edit round-trips).** The skill presents the
normalized set — **nothing is written yet**:

> *Normalized use cases (confirm / edit / skip):*
> 1. a crafter can search for a yarn by name
> 2. a crafter can see regional matches ranked by closeness
> 3. a crafter can filter matches to their own country
> 4. a crafter can open a retailer link for a match

**User edits:** *"Make #3 'filter matches by any region', not just their own —
designers help crafters elsewhere."*

The skill applies the edit and **re-presents** the list (the edit
**round-trips** through confirm). **User confirms.** *Now* — and only now — the
skill writes the section, **assigning each entry the next free `UC-N` id** as
it renders (this is the first capture, so the ids run `UC-1`…`UC-4`). The ids
are append-only — a later grow pass (slice 068-02) keeps `UC-1`…`UC-4` stable
and assigns `UC-5` to the next behavior.

**Step 4 — No silent inference.** The skill suspects an obvious missing
behavior but does **not** auto-add it — it asks:

> *"You didn't mention contributing a yarn to the database — intentional? (y/n)"*

**User:** *"No, that's v2 — leave it out."* The skill **does not add it**. (Had
the user said yes, it would have been added — only on the explicit yes.)

**Skill renders into `## Use cases`** (on confirm):

```markdown
## Use cases

<!-- elicited: 2026-05-15 / status: filled -->

- UC-1: A crafter can search for a yarn by name
- UC-2: A crafter can see regional matches ranked by closeness
- UC-3: A crafter can filter matches by any region
- UC-4: A crafter can open a retailer link for a match
```

Each entry carries a stable `UC-N` id (append-only) so a spec can cite it in
`use_cases:` and the trace link resolves (slice 068-02). Note the section is
**goal-level** — no entry names a table, an endpoint, or a scoring weight
(those are spec-level, kept out per the section's guidance). And
it is a **seed**: community-contribution behaviors (v2) were deliberately left
out here and will be **added while drafting those specs** — that additive growth
is slice 068-02's job, not this capture session's.

### Section 6 — Repository structure *(feeds architecture.md)*

**Skill asks Q6.1:**

**User answers:** *"Monorepo with: api/, frontend/, db/, shared/,
docs/, tests/. Cloudflare Workers for the API; Cloudflare Pages for
frontend; D1 for the database."*

**Skill renders into `architecture.md ## Repository structure`:**

```markdown
## Repository structure

<!-- elicited: 2026-05-15 / status: filled -->

```
yarn-finder/
├── api/         # Cloudflare Workers — yarn search + similarity API
├── frontend/    # Cloudflare Pages — search UI + results
├── db/          # D1 schema migrations + seed data
├── shared/      # Types + similarity scoring logic shared api↔frontend
├── docs/        # Project docs (spec-driven workflow)
└── tests/       # Cross-package test suites
```
```

### Section 7 — Tech stack *(feeds architecture.md)*

**Skill asks Q7.1, Q7.2, Q7.3:**

**User answers:**
- Runtime: Node.js / TypeScript (strict mode)
- Platform: Cloudflare ecosystem (Workers + Pages + D1 + KV); npm package manager
- Locked-in: Cloudflare D1 (SQLite at edge), no ORM, raw SQL with typed helpers
- Still open: similarity scoring weights (tunable), color matching approach

**Skill renders into `architecture.md ## Tech stack`:**

```markdown
## Tech stack

<!-- elicited: 2026-05-15 / status: filled -->

- **Runtime / language:** Node.js + TypeScript (strict mode)
- **Platform commitments:** Cloudflare Workers (API), Cloudflare Pages
  (frontend), Cloudflare D1 (SQLite at edge), Cloudflare KV (caching)
- **Package manager:** npm
- **Database / state:** D1 (SQLite at edge) — locked-in. No ORM; raw
  SQL with typed query helpers.
- **Key external services:** none in MVP (Ravelry API explicitly NOT
  a dependency — see Section 11)
- **Locked-in:** Cloudflare D1, raw SQL, no ORM
- **Still open:** similarity scoring weights, color matching approach
```

### Section 8 — Module boundaries *(feeds architecture.md)*

**Skill asks Q8.1, Q8.2:**

**User answers:**
- Concerns: api (Worker), frontend (Pages), db (D1 + migrations), shared (types + scoring)
- Contracts: api ↔ shared (typed interfaces); frontend ↔ api (HTTP JSON); db ↔ api (SQL queries via typed helpers)

**Skill renders into `architecture.md ## Module boundaries`:**

```markdown
## Module boundaries

<!-- elicited: 2026-05-15 / status: filled -->

- `api/` — Cloudflare Worker; yarn search + similarity scoring endpoints
- `frontend/` — Cloudflare Pages; search UI + results display
- `db/` — D1 schema, migrations, seed data (~30 yarns for MVP)
- `shared/` — TypeScript types + similarity scoring logic (consumed
  by both api/ and frontend/)

Interface contracts: api ↔ shared via typed interfaces; frontend ↔
api via HTTP JSON; db ↔ api via SQL queries through typed query
helpers in shared/.
```

### Section 9 — Data model *(feeds architecture.md)*

**Skill asks Q9.1, Q9.2:**

**User answers:** Yarn entity (per spike-yarn-domain-research.md):
weight category, fiber content, gauge, yardage, color, region,
price, retailer links, community ratings.

**Skill renders into `architecture.md ## Data model`:**

```markdown
## Data model

<!-- elicited: 2026-05-15 / status: filled -->

Single core entity: **Yarn**. Attributes:

- `weight_category` (lace, fingering, sport, DK, worsted, bulky, …)
- `fiber_content` (wool, cotton, acrylic, blends — structured)
- `gauge` (stitches per inch / 10cm)
- `yardage_per_100g`
- `color` (RGB + name for closest-match scoring)
- `region` (country / region of availability)
- `price` (per-100g)
- `retailer_links[]`
- `community_ratings[]` (deferred to v3)

Stored in Cloudflare D1 (SQLite at edge).
```

### Section 10 — Design principles & constraints

**Skill asks Q10.1, Q10.2:**

**User answers** (taken directly from YarnFinder's CLAUDE.md
"Coding Conventions" section):
- Prefer Cloudflare-native solutions over generic alternatives
- TypeScript strict mode; explicit types; no clever generics
- Early returns + guard clauses over nested conditionals
- Fail fast with typed errors
- No ORM — raw SQL with typed helpers
- Dependency injection for testability
- High coverage on business logic; skip framework glue

**Skill renders into `## Design principles & constraints`:**

```markdown
## Design principles & constraints

<!-- elicited: 2026-05-15 / status: filled -->

1. Prefer Cloudflare-native solutions over generic alternatives.
2. TypeScript strict mode; explicit types; avoid clever generics.
3. Early returns + guard clauses over nested conditionals.
4. Fail fast with typed errors.
5. No ORM — raw SQL with typed helpers.
6. Dependency injection for testability (pass deps, don't import singletons).
7. High coverage on business logic; skip framework glue.

**Non-obvious constraints:**
- Solo dev — human reviewer reads TS fluently but doesn't write it
- D1 query complexity limits (revisit if outgrown)
```

### Section 11 — How new work enters

**Skill asks Q11.1, Q11.2:**

**User answers:**
- Initial data sourcing: manual curation from public sources (no Ravelry API dependency — explicit decision from spike)
- Growth phase: community contributions
- New features: spec-driven, slice-by-slice per Agile SDD workflow

**Skill renders into `## How new work enters`:**

```markdown
## How new work enters

<!-- elicited: 2026-05-15 / status: filled -->

**Data sourcing.** Manual curation from public sources for MVP — no
Ravelry API dependency (explicit decision from the domain-research
spike slice; see that slice's Outcome for full rationale).
Community contributions planned for v2 (feature 5).

**Feature work.** Spec-driven slice-by-slice per the Agile SDD
workflow. Each slice has DoR, AC, DoD; one slice = one implementable
unit.
```

**This is YarnFinder's "Data sourcing" content** — mapped into the
template's `## How new work enters` slot per AC #5 mapping.

### Section 12 — Open questions *(feeds refinement-todo.md)*

**Skill asks Q12.1:**

**User answers:**
- Similarity weight tuning — how do we calibrate?
- Color matching approach — RGB distance vs perceptual?
- D1 limitations for complex queries — when do we outgrow?

**Skill writes these as entries in `docs/refinement-todo.md`** (no
H2 in `docs/product-vision.md` for open questions — they live in
refinement-todo, with `docs/architecture.md ## Open questions`
serving as a pointer).

## Result: rendered docs/product-vision.md

Same 10 H2s as jig's worked example (Identity / Target users / Core
problem / Competitive landscape / Scope / Use cases / Stack / Design
principles & constraints / How new work enters / Open questions) — the
elicitation skill produces template-shaped output regardless of
project shape. The `## Use cases` section is filled by the
conversational capture loop demonstrated above (any-shape capture →
single normalize pass → confirm-before-write → no silent inference).
YarnFinder's bespoke concepts (Data sourcing,
Recommended slice order, prioritized backlog, Future scope) all
land in the appropriate template slots per the mapping table at
the top of this file.

`docs/architecture.md` has 4 of its elicitation slots filled
(Repository structure / Tech stack / Module boundaries / Data
model). The two non-marker sections (Core architecture decisions /
Open questions) remain for ADR-driven content + refinement-todo
pointers.

## Why two worked examples

Different project shapes stress-test different parts of the question
set:

- **jig** (dev tooling) stresses Section 10 (design principles —
  the load-bearing 7 principles), Section 5 (out-of-scope non-goals
  — what jig deliberately doesn't do), and Section 11 (how new
  work enters — signal-driven prioritization model).
- **YarnFinder** (consumer product) stresses Section 4 (competitive
  landscape — direct competitor analysis), Section 5 (MVP vs v2 vs
  v3 phasing — clear product-tier separation), Section 9 (data
  model — the core Yarn entity with concrete attributes), and
  Section 11 (data sourcing — where the underlying data comes
  from).

Two shapes also expose **mapping gaps**: YarnFinder's "Recommended
slice order" doesn't have a dedicated template H2 — it maps to the
Tiers/phases H3 under Scope. The two examples make the mapping
explicit so the 017-02 implementer can verify the skill handles
both shapes coherently.
