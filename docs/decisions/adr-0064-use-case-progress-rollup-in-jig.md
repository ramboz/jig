---
status: Accepted
dependencies: [adr-0025]
last_verified: 2026-10-03
frame_review: true
---

# ADR-0064: Use-case progress rollup lives in jig as a bounded exception

## Status

Accepted (2026-10-03)

## Context

An owner of a project with many specs cannot tell whether the work is still
advancing the product's goals. The originating report (owner, 2026-10-03):
agents go down rabbit holes in directions the owner does not fully know, and it
is hard to confirm the project is still moving toward its goals.

jig already holds all three levels of the needed hierarchy:

- **Use cases** — the vision's `## Use cases` section, with stable `UC-N` ids
  ([ADR-0025](adr-0025-use-cases-breadth-layer.md), spec 068).
- **Specs** — each cites the use cases it serves through `use_cases:`
  frontmatter, read by `workflow.py coverage` (slice 068-03).
- **Slices** — each carries a lifecycle state, rolled up per spec by
  `compute_spec_status` in `skills/spec-workflow/workflow.py`.

What is missing is the join: per use case, how much of the known work is done,
and which specs cite no use case at all. Spec 116 proposes it as a read-only
`workflow.py progress` command. It answers part of the owner's question — how
far along each goal's known work is, and where to audit which spec claims which
goal — not whether the work is on-goal (bound 5 below).

The force against it is jig's own vision. `docs/product-vision.md` § "Out of
scope (deliberately)" lists a **project management surface**: "No backlog
rendering, no estimation, no roadmap visualization. Specs are the only project
state." A future agent reading that line would reasonably refuse the report, or
remove it. On 2026-10-03 the owner ruled the report in scope as a bounded
exception, and this record exists so that ruling is not undone by citing the
line it qualifies ([ADR-0031](adr-0031-load-bearing-decision-adr-trigger.md)
trigger, routed per [ADR-0042](adr-0042-decision-routing-gate.md)).

## Decision Options Considered

### Option A: A derived, read-only rollup in jig
`workflow.py progress` joins the trace links with slice state and prints use
case → specs → done/known slice counts, plus the specs that cite no use case. It
stores nothing and is recomputed from the vision and spec records on every run.
- **Pros:** every input is already a jig artifact, read by jig code. No new
  state, so "specs are the only project state" stays true. Small: one
  subcommand plus one orient section.
- **Cons:** it qualifies an out-of-scope line, which opens a door that later
  requests could push wider.

### Option B: Put it in shaper
shaper is the sibling project for release shaping, and reads jig's specs and
status board already.
- **Pros:** keeps jig's out-of-scope line untouched.
- **Cons:** shaper is release-scoped, while this report is project-wide. Its
  own vision rules the report out: it is "not a task board, sprint planner,
  estimation engine, backlog groomer" and keeps "non-duplicating overlays: do
  not create a second status board" (shaper `docs/product-vision.md`, read
  2026-10-03 at commit `c0d7a33`).

### Option C: Start a dedicated project-management project now
A new repository, the way shaper was split out of jig.
- **Pros:** jig's scope stays strictly as written.
- **Cons:** a whole project for one read-only query. A separate project is
  worth it once deeper features are wanted (estimation, velocity, roadmaps),
  and none are wanted today.

### Option D: Status quo — `coverage` only
- **Pros:** zero cost.
- **Cons:** `coverage` answers yes/no per use case (is it cited at all) and
  says nothing about how far along it is, so even the progress half of the
  owner's question stays unanswered.

## Recommended Decision

**Option A**, as the owner ruled on 2026-10-03. The report is a bounded
exception to the "project management surface" out-of-scope line, and the
bounds are the decision:

1. **Derived, not stored.** No new file, board, or state. A persisted progress
   board would need its own drift check, and is out.
2. **Read-only and advisory** ([ADR-0011](adr-0011-spec-gate-model.md)): it
   never gates a transition and never writes.
3. **Counts, not forecasts.** Done/known slice counts only — no percentages,
   weighting, estimation, velocity, burndown, or dates.
4. **Spec-level links only** — the trace links stay where slice 068-02 put
   them.
5. **A progress view, not a drift detector.** The report shows where the known
   work sits and how far along it is. It does not certify that the work is
   on-goal: the links it reads are assigned by the agents whose direction is in
   question (see Assumptions).

**The re-open trigger is a new project, not jig growth.** A request that
crosses these bounds — estimation, velocity, roadmaps, a persisted board — is
the signal to start Option C, not to widen this command.

Slice 116-01 amends the vision's out-of-scope bullet to name this exception
and point here, with wording the owner approved on 2026-10-03 (that slice's
AC9).

## Consequences

**Becomes easier:**
- The owner sees, per use case, how much known work is done and which specs
  are still open (each spec is listed with its status under the use case it
  cites), plus the specs that cite no use case.
- A mis-mapped `use_cases:` link can be spotted by an owner reading a use
  case's spec list. Spotting it still takes a reader who knows the spec.

**Becomes harder:**
- Adding project-management features to jig: each one now has to clear this
  record's bounds or go to a separate project.

## Assumptions

- **Load-bearing (thin evidence):** a done/known count per use case is a useful
  progress view. It rests on one owner request (2026-10-03), not on measured
  use. A count can read "all done" while the behavior is still not delivered
  end to end (the ADR-0025 §A2 caution), and nothing here mitigates that:
  showing counts rather than percentages only keeps partial progress from
  looking more precise than it is — `31/31` still reads as complete.
- **Known limit (false anchoring):** the `use_cases:` links are written by the
  same agents whose direction is in question, against goal-level use cases
  broad enough to fit almost any work, and spec-workflow step 2a prompts every
  new spec to cite or add a use case. On adoption day 110 of 112 specs were
  anchored. So the Unanchored bucket mostly holds deliberate declines, and an
  off-goal spec usually reads as ordinary progress under a plausible use case.
  That is why bound 5 claims a progress view, not drift detection. Signals the
  drafting agent does not author (owner-confirmed versus agent-assigned links;
  use cases added since the owner last confirmed the vision) are parked in
  `docs/refinement-todo.md`.

## Kill criteria

- The owner stops consulting the report or its `/jig:orient` section — then
  retire the command rather than grow it.
- Escalation trigger (not a retirement test — the false-anchoring limit
  predicts it): a spec the owner later judges off-goal turns out to have been
  listed as ordinary progress under a use case. Then build a parked
  agent-independent signal (`docs/refinement-todo.md`); retirement stays with
  the criterion above.
- A request for any feature outside the bounds above — handled by starting a
  separate project (Option C), not by amending this record.

## Open questions

None.
