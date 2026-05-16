# Question set — `/jig:vision-elicitation`

> Canonical 13-section Q&A flow. Sections 1–12 mirror Appendix A of
> [spec 017](../../docs/specs/017-vision-elicitation/spec.md); Section
> 13 (Contract surfaces) was added by
> [spec 022-02](../../docs/specs/022-contracts/slice-02-integration-touchpoints.md)
> to feed the `/jig:contracts` skill. The skill asks each section in
> order; each section is independently skippable; the skill stops when
> all 13 have been visited.

## Rules

- **Per-section flow** (Path SPIDR decision). Sections are independently
  skippable and re-runnable. Questions within a section are not their
  own skip-units.
- **Write the user's words.** No paraphrasing, no expansion, no
  "improving." Two narrow exceptions: markdown structure (bullets,
  tables, sub-bullets per template shape) and preserving the user's
  declared section ordering.
- **Stop conditions.** All 13 sections have a marker (`filled` or
  `skipped`). No looping; no upselling.
- **Marker convention** (per [docs/conventions.md](../../docs/conventions.md)
  "Elicitation slots" rule):
  - Answered → `<!-- elicited: YYYY-MM-DD / status: filled -->`
  - Skipped → `<!-- elicited: YYYY-MM-DD / status: skipped -->`
  - The `hash` field is added in slice 017-03 once re-run mechanics ship.

## Section-to-slot map

| Section | Produces | File |
|---|---|---|
| 1 — Identity | `## Identity` | product-vision.md |
| 2 — Target users | `## Target users` | product-vision.md |
| 3 — Core problem | `## Core problem` | product-vision.md |
| 4 — Competitive landscape | `## Competitive landscape` | product-vision.md |
| 5 — Scope | `## Scope` (with H3 sub-sections) | product-vision.md |
| 6 — Repository structure | `## Repository structure` | architecture.md |
| 7 — Tech stack | `## Tech stack` | architecture.md |
| 8 — Module boundaries | `## Module boundaries` | architecture.md |
| 9 — Data model | `## Data model` | architecture.md |
| 10 — Design principles & constraints | `## Design principles & constraints` | product-vision.md |
| 11 — How new work enters | `## How new work enters` | product-vision.md |
| 12 — Open questions | refinement-todo.md entries (architecture.md Open questions footer points there) | refinement-todo.md |
| 13 — Contract surfaces | `## Contract surfaces` | architecture.md |

> The vision template's `## Stack` H2 has no Q&A producer in this
> 13-section design. That's the intentional gap recorded in slice
> 017-01's deviation log §7 — Stack content varies between vision
> (platform framing) and arch (concrete runtime/db), and the skill
> writes only the latter. Future work may dual-write or remove the
> vision-side Stack section.

> Section 13 (Contract surfaces) was added by spec 022-02 to feed the
> `/jig:contracts` skill's nudge-toward-standard-artifacts workflow.
> See [skills/contracts/SKILL.md](../contracts/SKILL.md) for the
> per-surface recommendation table referenced by the section's
> question.

---

## Section 1 — Identity *(always asked)*

Produces: vision template's `## Identity` section (vision statement +
optional tagline subhead + optional positioning story).

- **Q1.1:** "In one sentence, what does this project do?"
- **Q1.2** *(optional)*: "If you were defining the project's name as
  a noun ('<name> (noun): __'), what's its essence?"
- **Q1.3** *(optional)*: "Is there a positioning story worth
  recording? (e.g. 'we pivoted from X to Y after we realized Z',
  or 'an audit at month N flagged that we'd drifted from the
  original framing')."

## Section 2 — Target users *(always asked)*

Produces: `## Target users` (including a "not for" sub-bullet).

- **Q2.1:** "List 2–4 specific user types this project serves. Be
  concrete — 'first-time Claude Code users' or 'devs migrating
  legacy specs' is better than 'developers'."
- **Q2.2:** "Who is this *not* for? List 1–3 personas you're
  explicitly choosing not to serve. (Often clearer to define a
  product by exclusion than inclusion.)"

## Section 3 — Core problem *(always asked)*

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

## Section 4 — Competitive landscape *(always asked)*

Produces: `## Competitive landscape` (table format).

- **Q4.1:** "List 3–5 alternatives a user might consider —
  generic or specific."
- **Q4.2** *(per alternative)*: "What does it do well?"
- **Q4.3** *(per alternative)*: "Where does it fall short for *this
  particular* gap?"
- **Q4.4:** "In one sentence, where does this project fit between
  those alternatives?"

## Section 5 — Scope *(always asked)*

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

## Section 6 — Repository structure *(always asked; feeds architecture.md)*

Produces: architecture.md's `## Repository structure` slot.

- **Q6.1:** "What's the top-level directory layout? Even a one-line
  description per directory beats nothing — it's the easiest place
  for new contributors to start. If you don't have it yet, sketch
  what you expect: 3–6 top-level directories with a one-line purpose
  each."

## Section 7 — Tech stack *(always asked; feeds architecture.md)*

Produces: architecture.md's `## Tech stack` slot.

- **Q7.1:** "Runtime / language?"
- **Q7.2:** "Platform commitments? (cloud target, deployment shape,
  package manager, database, key external services.)"
- **Q7.3:** "For each of these — locked-in decision, or still open?"
- **Q7.4** *(optional, per locked-in decision)*: "Want to seed a
  draft ADR for this? (Slice 017-04 lands the auto-scaffold; for
  now this is captured as a tagged sub-bullet so `adr-workflow`
  can pick it up later.)"

## Section 8 — Module boundaries *(always asked; feeds architecture.md)*

Produces: architecture.md's `## Module boundaries` slot.

- **Q8.1:** "What are the top-level *concerns* of this codebase?
  Name them even if their interfaces aren't formal yet."
- **Q8.2:** "Are interface contracts between those concerns defined
  today, or is the coupling read-only / one-directional / deferred?
  'Today's coupling is read-only' is a valid and honest answer."

## Section 9 — Data model *(always asked; feeds architecture.md)*

Produces: architecture.md's `## Data model` slot.

- **Q9.1:** "What state does this project own? List the state
  elements (config files, databases, append-only logs, in-memory
  caches, etc.) with one-line descriptions."
- **Q9.2:** "If the project is stateless or near-stateless, name
  that explicitly. 'Stateless — config files only' is a valid and
  honest answer; leaving the section blank is not."

## Section 10 — Design principles & constraints *(always asked)*

Produces: vision template's `## Design principles & constraints`
section.

- **Q10.1:** "Are there principles every spec should be judged
  against? Constraints you don't want to violate? List 3–7."
- **Q10.2:** "Any non-obvious constraints? (perf budgets,
  regulatory, team size, cost, context-window economics,
  backward-compat policy.)"

## Section 11 — How new work enters *(always asked)*

Produces: vision's `## How new work enters` (the equivalent of
"data sourcing" in the YarnFinder shape).

- **Q11.1:** "How will new features get prioritized? Signal-driven,
  roadmap-driven, stakeholder-driven, or some mix?"
- **Q11.2:** "Any specific triggers documented for what justifies
  a new spec? (e.g. 'pain hit twice', 'cross-project comparison
  revealed a pattern', 'compliance requirement landed'.)"

## Section 12 — Open questions *(always asked)*

Produces: entries in `docs/refinement-todo.md` (the
architecture.md `## Open questions` section is just a pointer
to that file).

- **Q12.1:** "What's still uncertain? List architectural questions
  that don't have answers yet. (Bullets here become refinement-todo
  rows automatically.)"

## Section 13 — Contract surfaces *(always asked; feeds architecture.md; per spec 022-02)*

Produces: architecture.md's `## Contract surfaces` slot. The dev's
declared surfaces and chosen artifacts (or "no artifact yet"
acknowledgments) get written here so the `/jig:contracts` skill's
reviewer-prompt integration (spec 022-02 AC #2) can read them at
slice-review time. Skipping this section is an acceptable opt-out —
the reviewer-prompt check is conditional on the section existing
with at least one declared surface (per spec 022-02's nudge-don't-mandate
convention).

- **Q13.1:** "What **external surfaces** does this project commit to
  as caller-facing interfaces? List the categories that apply: HTTP
  API, event bus / async messaging, RPC, GraphQL, internal data
  shapes (cross-service envelopes), CLI output, config / env vars.
  For each, in one line, name the recommended artifact (see
  [skills/contracts/SKILL.md](../contracts/SKILL.md) for the
  per-surface recommendation table) or write 'no artifact yet' if
  the surface exists but no schema is committed. 'No external
  surfaces' is a valid and honest answer — this project may be a
  library, a script, or a single-consumer internal tool."
- **Q13.2** *(per declared surface)*: "Where does the artifact live
  on disk? (e.g. `openapi.yaml`, `src/events/*.schema.json`,
  `proto/*.proto`, `schema.graphql`.) 'Not yet committed' is a
  valid answer; it surfaces the gap to the next reviewer."
- **Q13.3** *(optional)*: "Any stack-coupled alternative chosen
  instead of the canonical artifact? (e.g. Zod / TypeBox / Pydantic
  for internal data shapes instead of JSON Schema.) If yes, consider
  capturing the rationale via `/jig:adr-workflow` per ADR-0005's
  opt-out convention."
