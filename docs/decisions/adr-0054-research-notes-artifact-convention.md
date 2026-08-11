---
status: Accepted
dependencies: []
last_verified: 2026-08-11
frame_review: true
---

# ADR-0054: Research notes as a lightweight standalone-investigation artifact

## Status

Accepted (2026-08-11)

## Context

jig has homes for parked thoughts (`docs/inbox.md`), deferred *decisions*
keyed on resolution triggers (`docs/refinement-todo.md`), committed decisions
(ADRs), and committed work (specs + slices). It has no home for the **open
investigation phase** — the stretch *before* a decision is even named, when you
are gathering sources, weighing pros/cons, and holding open questions on a
generic idea that is not attached to any committed build.

The load-bearing distinction this ADR rests on is a **phase / altitude** one,
not a "thickness" one:

- A `refinement-todo` entry is a **named deferred decision + a resolution
  trigger**. Its charter (the file's own header) is *"Decisions the initial
  setup explicitly deferred. Each item has a resolution trigger. Resolve items
  by writing an ADR."* It presupposes you already know *what the decision is*
  and are choosing not to make it yet.
- A research note is the home for the step *before* that: an **open
  investigation with no decision named yet**, whose *output* might be a
  `refinement-todo` entry, an ADR, a spec, or nothing at all.

These are **sequential, not competing**: investigate (research note) →
crystallize into a named deferred decision (`refinement-todo`) or a decision
(ADR) or committed work (spec) → or drop it. A research note is not "a thick
`refinement-todo` entry"; it is the phase that *feeds* one.

Spike-type slices do not fill the gap either: a spike assumes the work is
already shaped and in-flight — it lives inside a spec that has already been
reserved and (usually) ADR-framed. Research that precedes any shaping has
nowhere to go.

### Demand — recounted honestly

An earlier draft of this ADR claimed "n ≫ 3 internal instances" by pointing at
four thick `docs/inbox.md` entries. A frame-critique correctly showed that
count was **inflated**: three of those four — the `[2026-06-10]` positioning
map (`inbox`:37, "promote … on a 2nd real ask; count: 1"), the `[2026-06-10]`
"jobs" entry (`inbox`:38), and the `[2026-06-11]` design-conformance ladder
(`inbox`:40) — each already carry a resolution trigger and a promotion target,
which by jig's own taxonomy makes them **`refinement-todo`-shaped**, not
homeless. And `refinement-todo.md` *already* holds thick, multi-paragraph,
options-bearing entries (e.g. the Claude-scaffold-template entry
`refinement-todo`:67-72; the cross-spec sequencing entry
`refinement-todo`:114-123), so "too thick for its home" does **not** on its own
justify a new type. That critique is accepted, and the count is corrected here
rather than defended.

What genuinely survives scrutiny as evidence is two data points plus one
hypothesis — and the "act now" decision rests only on the two data points:

1. **An existing, un-homed artifact class (evidence, n=1).** `docs/research/`
   already holds jig's **founding** research corpus — `00-starter-prompt.md`
   plus `01-research-skills-and-triggering.md` … `09-addition-memory-layer.md`
   (verified this session: 10 frozen prose files, no status frontmatter, no
   index). jig literally bootstrapped itself from research notes, then never
   made the practice *living*. This is a real class that exists today with no
   convention around it — not speculation. (Honest caveat: it is a *one-time
   genesis* event, not proof of a recurring steady-state phase.)
2. **An independent external ask (evidence, n=1, unverifiable here).**
   [Issue #196](https://github.com/ramboz/jig/issues/196) names a 230-line
   dashboard-brainstorm investigation floating undocumented in a `docs/design/`
   file, with no status, index, or hand-off path. jig historically weights an
   outside ask above internal dogfood.
3. **A hypothesis — NOT counted as evidence.** It is *plausible* that the three
   thick inbox entries (`inbox`:37, 38, 40) bloated the inbox because they began
   as open investigations and accreted their trigger only at the end — i.e. they
   needed an open-phase home the inbox was standing in for. But this is an
   **unfalsifiable narrative**: on disk those entries carry a decision + trigger
   *now*, and there is no historical artifact showing they ever existed without
   one. So it is stated as a hypothesis the convention will *test* (see Kill
   criteria), not leaned on as proof. Subtracting it, the demonstrated
   *recurring internal* open-phase signal is ≈ n=0–1, not more.

Honest tally: recurring *internal* demand for an open phase that *stays* open is
essentially unproven (≈ n=0–1); a strict rule-of-three reading says **defer**.
The decision to act *now* is a deliberate, eyes-open bet resting on exactly
three things — the **existing** un-homed seed corpus (data point 1), the
**external** ask (data point 2), and the fact that the response is a
**near-zero-cost, reversible convention** rather than machinery, guarded by a
tripwire (Kill criteria). It explicitly does **not** rest on demonstrated
recurring internal open-phase demand; if this ADR proceeds, the deviation log
should record that framing so the bet stays honest.

The remaining design question is *how heavy* the home should be. Issue #196
proposes a first-class type with a creation helper, indexed discovery,
documented hand-offs, and **bidirectional cross-linking** — a full spec with
machinery. jig's cost model (context × turns; every artifact type is standing
surface every adopter and every session inherits) argues for the lightest thing
that removes the pain.

## Decision Options Considered

### Option A: Do nothing — keep using the inbox + incidental files
- **Pros:** Zero new surface. No new template, glossary term, scaffold output,
  or adopter-facing concept.
- **Cons:** Leaves the demonstrated pain in place. The inbox keeps drifting
  from "thin capture" to "unsearchable deep-research dump"; investigations keep
  landing in undocumented `docs/design/` / `docs/research/` files with no
  status or hand-off. Ignores an external ask (#196) and an already-existing
  in-repo corpus that proves the practice.

### Option A′: Route thick investigations into `refinement-todo` (no new type)
The nearest existing artifact — the fix the frame-critique proposed. Instead of
a new type, add discipline: thick, evolving investigations go into
`refinement-todo.md`, which already holds multi-paragraph entries.
- **Pros:** Zero new artifact type. Reuses a home that already tolerates depth.
  Cheapest possible response.
- **Cons:** Charter mismatch. `refinement-todo`'s contract is *"each item has a
  resolution trigger; resolve by writing an ADR"* — it presupposes a **named
  deferred decision**. An open investigation with no decision named yet, and
  possibly no trigger, does not fit that schema: filing it there forces you to
  either (a) mislabel exploration as a settled-but-deferred *decision*, or (b)
  invent a fake trigger to satisfy the convention — both of which corrupt the
  trigger-audit discipline that makes `refinement-todo` scannable ("resolve
  items keyed on their trigger"). It also conflates two altitudes in one file:
  the register of *what we've decided to defer* becomes polluted with *what
  we're still figuring out*. The right relationship is **sequential** — the
  investigation lands in a research note and *promotes into* a `refinement-todo`
  entry the moment it crystallizes a named deferred decision (this is the
  chosen hand-off, below), not that the two share one file.

### Option B: First-class type with machinery (issue #196 as written)
A `research.py` creation helper, a regenerated index, a `transition`-style
status state machine, enforced bidirectional cross-linking, and (implicitly)
reservation-on-origin/main numbering to match specs/ADRs.
- **Pros:** Uniform with the spec/ADR artifact families; discovery and
  hand-off are tool-enforced rather than convention-enforced.
- **Cons:** Buys machinery ahead of evidence that the *convention* is
  insufficient. Reservation numbering is actively wrong here: a research note
  that promotes *into* a spec/ADR needs no globally-coordinated number — a
  collision (two `R-007`s) is a harmless nuisance, not board corruption, so
  dragging in the origin/main reservation apparatus (and its concurrent-session
  failure modes) buys nothing. A `transition` gate and a bidirectional-link
  linter repeat the trace-link-spine over-reach (spec 068) before there is a
  single real catalogue to justify them. Highest standing cost of the three;
  most to explain to adopters.

### Option C: Ship a convention, defer the machinery (recommended)
A directory + naming convention + a template + a hand-maintained index + a
short documented hand-off. No helper, no hooks, no state machine, no
link-enforcement. Every piece of machinery from Option B becomes a
trigger-gated `refinement-todo` entry.
- **Pros:** Removes the demonstrated pain immediately at minimal standing cost.
  Matches the existing precedent exactly — jig's own founding research corpus,
  and `inbox.md` / `refinement-todo.md` themselves, are all hand-maintained
  prose with no helper. Adopter-optional and ignorable. Keeps `R-NNN`
  numbering the user wanted for cross-referencing without importing reservation
  semantics it does not need. Because the response is a convention rather than a
  machine, the downside of acting on the modest-but-real signal is small and
  reversible. Leaves a clean, evidence-gated path to Option B's pieces if and
  when they are actually warranted.
- **Cons:** Discovery and hand-off are convention-enforced, so they can be
  skipped or done inconsistently until a human or reviewer notices. The
  hand-maintained index can drift (the same class of risk the spec board's
  Notes column carries). Numbering is manual, so a concurrent-session
  double-`R-NNN` is possible — accepted as a harmless nuisance here.

## Recommended Decision

Adopt **Option C**: research notes are a **lightweight, convention-level
artifact**, not a machine.

**Shape:**

- **Location & naming.** Living notes are `docs/research/R-NNN-<slug>.md`,
  numbered from `R-001`. The existing `00`–`09` files are formally declared
  **seed research** (jig's frozen founding corpus) — kept in place, unrenamed
  (ADR-0010 ethos: don't rewrite history for its own sake), and labeled as such
  at the top of the index. The `R-` prefix *is* the clean boundary between the
  frozen seed corpus and the living series, and reads naturally in
  cross-references (`see R-004`).
- **Frontmatter (light):** `status` (`OPEN` | `CONCLUDED` | `PARKED` |
  `ABANDONED`), `topic`, `created`, `related:` (links to specs/ADRs/issues).
  Status is a prose word, not a gated state machine.
- **Body:** free-form and evolving — question → sources/findings → pros/cons →
  open questions → conclusion.
- **Index:** a **hand-maintained** `docs/research/README.md` — a seed-research
  note at the top plus a small table of living notes (status + topic). No
  regen helper initially.
- **Hand-offs (two conventions, no enforcement):**
  1. *Inbox → note.* A thick investigation is captured as a one-line inbox
     pointer (`[date] exploring X → R-004`) instead of swallowing the whole
     thing inline; the depth lives in the note. This returns the inbox to the
     "thin" role its own header claims.
  2. *Note → decision/work.* When the investigation crystallizes, it **promotes
     into the right existing artifact**: a `refinement-todo` entry (if it lands
     on a *named deferred decision + trigger*), an ADR (a decision), or a spec
     (committed work). The downstream artifact **cites `R-NNN` in its Context**;
     the note flips to `CONCLUDED` and gains a `Promoted to: …` line. This is
     the sequential relationship that keeps research notes and `refinement-todo`
     distinct rather than overlapping: the note is the open phase, the
     `refinement-todo` entry is the crystallized-but-deferred decision it feeds.
     Two one-liners, not a linter.

**Explicitly deferred to `refinement-todo` (each trigger-gated):** a
`research.py` creation helper; index regeneration; a link-resolution linter;
any numbering-collision handling; wiring research notes into `scaffold-init`
output for adopters. None ships until a concrete trigger fires.

This is placed as an ADR rather than an inbox bullet because it is a
load-bearing *convention* decision with genuine rejected alternatives (heavy
vs. light; reserved vs. local numbering; new type vs. incidental files) — which
is itself a small dogfood of the very artifact-discipline this ADR governs.

## Consequences

**Becomes easier:**
- Standalone investigations get a durable, searchable, status-bearing home that
  is neither a decision nor committed work.
- The inbox returns to thin one-liners; deep research stops drifting inside
  unsearchable bullets.
- Promotion to an ADR/spec carries a traceable back-reference to the
  investigation that seeded it.
- jig's dead founding-research corpus is reframed as the labeled seed of a
  living practice.

**Becomes harder:**
- One more artifact type to explain (glossary term + a `docs/conventions.md`
  entry, the latter gated on human approval) and, eventually, to teach adopters.
- Discovery/hand-off correctness rests on convention until a trigger promotes a
  helper — a wrong or skipped hand-off won't be mechanically caught.
- The hand-maintained index and manual numbering can drift; accepted as the
  Option-C trade until drift is observed.

## Assumptions

<!-- Spec 064-02 / ADR-0020 §1–§2 — grounding-by-probe (risk-gated). -->

- **Verified:** `docs/research/` currently contains exactly `00-starter-prompt.md`
  and `01`–`09` research files, all prose with no status frontmatter (directory
  listed this session). The named thick entries exist in `docs/inbox.md` and the
  drift language is quoted from `docs/refinement-todo.md`'s sequencing entry
  (both read this session). Issue #196's content (230-line example, proposed
  helper/index/hand-off/bidirectional-linking) is quoted from the issue.
- **Assumption (not probed):** that no *other* in-repo directory already serves
  as a living research home that this would duplicate. Searched `docs/research/`
  and `docs/design/` only; a broader sweep was not run.
- **Judgment, not fact:** that an external ask (#196) + an existing un-homed
  artifact class (the seed corpus) + near-zero convention cost together justify
  acting *now* despite an internal genuinely-triggerless signal of only ~n=1–2.
  This is an eyes-open bet against a strict rule-of-three reading, explicitly
  hedged by the Kill criteria — not a claim that the signal already clears the
  bar on internal instances alone.

## Kill criteria

- **The distinctness test (guards against the self-concealing count the
  frame-critique flagged).** A raw "were any `R-NNN` notes created?" tally is
  self-fulfilling — the convention will capture entries that would otherwise
  have gone to `refinement-todo`, manufacturing its own usage. The honest test
  is whether notes represent a *persistent* open phase, on **two** conditions,
  not just birth-state: (a) *born open* — the note carried no named decision +
  trigger at creation; **and** (b) *stayed open* — it lived as an active
  investigation across more than a trivial window (e.g. multiple sessions /
  days) before crystallizing, rather than acquiring a decision + trigger almost
  immediately. Sample the `R-NNN` notes over a meaningful window: if most fail
  (a) they were mis-filed `refinement-todo` entries; if most pass (a) but fail
  (b) they crystallized so fast that filing straight to `refinement-todo` at
  crystallization would have served as well — either way the type is capturing
  no distinct *persistent* phase → the convention is deadweight (Option A′ was
  right); retire it and route that content to `refinement-todo`. (Both
  conditions are self-judged by a party invested in the convention, so this
  tripwire is a mitigation, not a proof — weigh it honestly.)
- If essentially **no** note is created at all over that window (open research
  keeps landing in inbox bullets or incidental files regardless), the
  convention failed to change behavior — retire it rather than prop it up with a
  helper.
- If the *first* thing every note needs is machinery (numbering collisions bite
  immediately, or hand-offs are never done without enforcement), then Option C
  was the wrong altitude and this should be superseded by the Option-B spec —
  but that reversal must be evidence-driven, not anticipated.

## Open questions

- **Numbering policy.** Keep `R-NNN` strictly local-and-cheap (collisions
  tolerated, reconciled by hand at promotion), or add a minimal fetch-and-check
  at creation time if concurrent double-numbering is observed? Leaning
  local-and-cheap until it bites.
- **Adopter default.** Should `scaffold-init` seed an empty
  `docs/research/README.md` for new projects, or is research-notes a
  jig-internal convention until an adopter asks? Leaning jig-internal first
  (dogfood before shipping surface).
- **Conventions doc.** The `docs/conventions.md` entry codifying this needs
  explicit human approval (`JIG_CONVENTIONS_APPROVED=1`) — track as a follow-up
  rather than blocking the ADR.
