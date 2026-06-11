---
status: DONE
skill: vision-elicitation
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 068: Use cases as a first-class breadth layer

> Implements [ADR-0025](../../decisions/adr-0025-use-cases-breadth-layer.md).
> **DRAFT.** A breadth-first layer between the project vision and specs that
> enumerates intended user-facing behaviors, so behavior-dense projects have a
> shared frame to anchor specs against instead of inventing each spec's slice of
> the world ad hoc. Spans **vision-elicitation** (capture, slice 01),
> **spec-workflow** (feed-forward + trace + grow + coverage, slices 02–03). The coverage
> check is a **deterministic project-wide query** surfaced at reconcile — **no new
> reviewer subagent**, but **net-new (bounded) surface**, not free reuse: neither
> one-spec-at-a-time **`/jig:analyze`** nor the per-slice reconciliation reviewer
> ([ADR-0014](../../decisions/adr-0014-review-evidence-model.md)) has a project-wide
> view today (ADR-0025 §A4). The mid-flight triage lifecycle (slice 04) is
> **DEFERRED** by design (ADR-0025 Option C).

## Overview

jig's stack runs **vision → spec → slice**, and specs are authored *depth-first*.
Nothing between the vision and the specs enumerates the project's intended
user-facing behaviors, so on behavior-dense projects each spec's author invents
that spec's slice of the world ad hoc and they diverge. Root cause (confirmed
with a user): the scaffold never asked for use cases, so they never entered the
vision (verified — no use-case/behavior/scenario concept exists in
`product-vision.md.template`, the `vision-elicitation` wizard, or `/jig:clarify`).

This spec adds a **use-case breadth layer**, per ADR-0025:

1. **Capture at init** — a `## Use cases` section in the project vision, filled by
   a conversational capture loop (any-shape input → single normalize pass →
   human-confirm before write). Goal-level `"[actor] can [goal]"` entries only.
   This is a **seed**, not the final set (behaviors aren't all knowable at init);
   growing it is mechanism (2)'s job.
2. **Feed forward + trace + grow** — spec drafting reads the use-case section as
   framing, each spec records a machine-resolvable trace link to the use case(s) it
   serves, and — because behaviors surface *while drafting specs* — a spec reaching
   draft with an **empty/absent/unresolvable** trace field **prompts** an additive
   add to the vision (the trigger is the **deterministic empty-field state**,
   reachable in the gap case — not voluntary self-report), closing the
   knowability-at-init gap *where behaviors actually surface*.
3. **Reconcile coverage** — a bidirectional check flags use cases with no
   implementing spec (coverage gap) and specs with no parent use case (scope
   creep). It is a **deterministic cross-artifact query** surfaced at reconcile —
   **no new reviewer subagent** — but **net-new (bounded) surface**, not free
   reuse: neither the per-slice reconciliation reviewer nor one-spec-at-a-time
   `/jig:analyze` has a project-wide view today (ADR-0025 §A4).

Everything is an **overridable Tier-1 default**: on by default, per-section
skippable, droppable to Tier 2 / left empty for project classes where breadth
modeling adds nothing (libraries, single-flow CLIs). Every mechanism is
**advisory / deliberateness-signal** (ADR-0011), never a hard blocking gate.

## Goals / Non-goals

**Goals**
- Give behavior-dense projects a shared breadth frame, captured at init, that
  specs anchor against — catching divergence **early** (spec-draft framing) with
  reconcile as a **backstop**.
- Keep capture **conversational + confirm-gated**; never silently infer unstated
  use cases (surface inference as a question instead).
- Keep the use-case section **goal-level**, never spec-level — the vision must not
  bloat into a requirements doc.
- Reuse existing **capture** machinery (vision section + elicitation wizard); add
  only a **bounded, deterministic coverage query** for the audit step (no new
  reviewer subagent) — neither `/jig:analyze` nor the per-slice reconciliation
  reviewer has a project-wide view today (net-new bounded surface; ADR-0025 §A4).

**Non-goals**
- The **mid-flight blast-radius triage lifecycle** (DEFERRED — ADR-0025 Option C;
  documented as slice 04, not built).
- Any **hard blocking gate** (coverage stays advisory by default; OQ3).
- **Spec-level** use cases / a requirements catalogue.
- A **separate `behaviors.md`** artifact (ADR-0025 B1 rejected it).
- Re-deciding the **factual-claim** grounding ADR-0020 already owns — this spec
  grounds *behavior coverage*, an orthogonal target that converges with ADR-0020
  only at the human-confirm gate + the reconcile checkpoint (ADR-0025
  Relationship) — a shared checkpoint + human, not a shared reviewer mechanism.

## Assumptions

> Risk-gated (ADR-0020). The load-bearing premise is thin-evidence and is the
> spec's frame-critique trigger + kill-criterion target — slice 01 carries
> `frame_review: true` so it is adversarially attacked before the capture
> mechanism is built.

- **Load-bearing (thin evidence):** breadth-divergence on behavior-dense projects
  is real and recurs at a rate that justifies the layer — **one user, one Android
  app; not measured** (ADR-0025 §A1). The *gap* (scaffold never captured use
  cases) is verified; the *harm rate* is assumed. Mitigated by the
  overridable-default scoping + the kill criterion (ADR-0025).
- **Load-bearing (thin evidence) — knowability at init:** the behaviors worth
  capturing are **knowable and enumerable at init**, when `vision-elicitation`
  runs, well enough to seed a useful anchor. This **sharpens ADR-0025 §A2** with a
  *third, distinct* failure facet: §A2 names *too coarse* (grain) and
  *doesn't-bind* (mechanical); this one is **incompleteness** rooted in *timing*.
  The verified gap proves only that the scaffold never *asked* — not that asking
  *at init* yields a reasonably-complete set, and jig's own wizard ("No prior
  pitch. Start cold," `skills/vision-elicitation/SKILL.md`) testifies init is the
  moment of *least* concrete behavior knowledge. **Mitigation — split across the
  slices by design:** slice 01 captures only a **seed** (it does not assume init
  completeness and adds no grow mechanism of its own); slice 02 then **grows** the
  set *where behaviors actually surface* — at spec-drafting — by **prompting**
  (cite / grow / decline) whenever a spec reaches draft with an
  **empty/absent/unresolvable** trace field (068-02 AC5, reusing slice 01's
  capture loop seeded with the existing entries). The trigger is a **deterministic
  predicate over the trace field — reachable in the gap case the author actually
  produces (an empty field), not a voluntary self-report**: a trigger keyed only to
  a self-inflicted unresolvable id or a volunteered "this is new" would sit inert on
  exactly the gaps it must catch. Growth is therefore **mechanically triggered**,
  not merely reachable — so the load-bearing thin-evidence assumption is **no longer
  "does the trigger fire?"** (it fires mechanically) but a **two-part
  uptake-and-quality bet:** ***when prompted at the empty-field state, do authors
  (1) choose grow/cite often enough — vs. reflexively declining under depth-first
  context pressure — and (2) when they grow, write goal-level, non-duplicate entries
  rather than spec-shaped restatements — enough to actually reduce incompleteness
  without feeding §A2 coarseness?*** Part (2) is mitigated *at the point of growth*
  by AC5(b)'s confirm-step guard (goal-level grain + near-duplicate → route-to-cite),
  so a reachable trigger cannot silently bloat the section. This two-part bet and its
  `frame_review` now live on **slice 02**, not slice 01. **Discriminating signals**
  (so the kill criterion can attribute cause, not just symptom — note "trigger never
  fired" is now mechanically impossible for an empty field):
  *(i)* a section that **stays thin despite many specs hitting the empty-field
  prompt** (high *decline* rate on specs that do serve behavior) ⇒ §A2's
  **"doesn't-bind"** facet (authors declining mechanically under context pressure);
  *(ii)* a section that **grows, but with entries that each map 1:1 to exactly one
  spec, or sit textually near a sibling** ⇒ a **grow-quality** failure (spec-shaped /
  duplicate) feeding §A2 **coarseness** — the facet the count-up/decline-low signals
  would otherwise misread as success, now made *visible* via slice 03's coverage data
  (a use case implemented by exactly one spec) plus the section text;
  *(iii)* "100% coverage yet specs still diverge" ⇒ **coarseness** at the grain level
  (§A2). All three are observable post-ship from slice 03's coverage query + git
  history of the section (use-case count *and shape* vs. spec count), no new
  instrumentation. Surfaced by slice 01's frame-critique — see
  [reviews/slice-01-frame-critique.md](reviews/slice-01-frame-critique.md); the
  trigger-reachability and grow-quality sharpenings above were driven by slice 02's
  3-round frame-critique — see
  [reviews/slice-02-frame-critique.md](reviews/slice-02-frame-critique.md).
- **Grounded by precedent (not assumed):** trace links can be machine-resolvable
  metadata — `dependencies:` frontmatter already resolves `NNN-MM` tokens for the
  DONE gate and `parsing.py` already parses list-valued frontmatter (slice 02).
  The coverage check (slice 03) is a deterministic set-difference (no reviewer
  subagent), but **net-new bounded surface** — neither the per-slice
  reconciliation reviewer nor one-spec-at-a-time `/jig:analyze` provides a
  project-wide view (ADR-0025 §A4, caught by the ADR's frame-critique). Built in
  slice 03, not assumed away.

## Decomposition (SPIDR)

The feature stages by use-case-data lifecycle — **capture → consume → audit →
evolve** — and each stage is an independently landable vertical slice (touches
the user-facing surface, delivers observable value, not intermediate state):

- **Interface** — 068-01: the minimal capture surface — a `## Use cases` vision
  section + the conversational capture loop (any-shape input → single normalize
  pass → confirm) in `vision-elicitation`, capturing a **seed** set. The
  **prerequisite**: nothing downstream works without the section existing and being
  fillable. (No grow mechanism here by design — growth is 068-02's job, where
  behaviors surface.)
- **Rules** — 068-02: the spec-author contract gains rules — spec drafting reads
  the use-case section as framing, each spec records a machine-resolvable **trace
  link** to the use case(s) it serves, and a spec whose trace field is left
  **empty/absent/unresolvable** trips a **mechanical grow prompt** (cite / grow /
  decline) — the knowability-at-init mitigation, *triggered by the deterministic
  empty-field state* so it is reachable in the gap case, not reliant on voluntary
  self-report (so this slice now carries `frame_review` too). *Produces the link
  data slice 03 audits.*
- **Rules** — 068-03: the reconcile-phase **bidirectional coverage check**
  (use-case→no-spec = gap; spec→no-use-case = creep), advisory by default — a
  **deterministic project-wide query** (no new reviewer subagent), but **net-new
  bounded surface**: neither one-spec-at-a-time `/jig:analyze` nor the per-slice
  reconciliation reviewer provides a project-wide view today (ADR-0025 §A4).
- **Rules** — 068-04 (**DEFERRED**): the mid-flight blast-radius triage lifecycle
  (additive / conflicting / reframing; asymmetric default). Load-bearing on
  02–03's trace links being *real and populated*, and the thinnest-evidence part
  — documented with its revisit trigger, **not built** (mirrors how ADR-0020
  deferred best-of-N drafting).

No spike is needed: the mechanisms reuse proven machinery (vision section,
elicitation wizard, frontmatter trace fields, the reconciliation reviewer /
analyze), so none of P/I/D/R is blocked by an unknown.

## Slices

| Slice | Title | Status | Notes |
|---|---|---|---|
| [068-01](slice-01-capture-and-vision-section.md) | capture-and-vision-section | **DONE** | Prerequisite. `## Use cases` vision section + conversational capture loop (normalize + confirm) in vision-elicitation. Goal-level only, **seed only** (no grow mechanism — that's 068-02). `frame_review: true` — passed (4-round iteration; grow moved to 02 per team decision). |
| [068-02](slice-02-feed-forward-and-trace-links.md) | feed-forward-and-trace-links | **DRAFT** | Spec drafting reads use cases as framing; each spec cites a machine-resolvable trace link (reuses the `dependencies:`-style shape). **Also owns grow-on-discovery** — a spec with an empty/absent/unresolvable trace field trips a *mechanical* grow prompt (cite / grow / decline), reachable in the gap case (knowability-at-init mitigation moved here from 01; trigger sharpened by 02's frame-critique). `arch_review: true` + `frame_review: true`. |
| [068-03](slice-03-reconcile-coverage-grounding.md) | reconcile-coverage-grounding | **DRAFT** | Bidirectional coverage at reconcile (gap + creep). Deterministic query — no new reviewer subagent — but net-new bounded surface (§A4). Advisory default (OQ3). |
| [068-04](slice-04-mid-flight-triage.md) | mid-flight-triage | **DEFERRED** | Blast-radius triage lifecycle (ADR-0025 Option C). Documented, not built. Resolution trigger: trace links real + populated AND a genuine mid-flight conflict/reframe event observed. |

## Open questions

**All resolved with the human on 2026-06-10** (see
[ADR-0025](../../decisions/adr-0025-use-cases-breadth-layer.md) `## Open
questions`). The working defaults below are now decisions:

1. **OQ1 — ADR granularity → one ADR for now.** ADR-level; does not block this
   spec. Slice 04 stays a deferred section; it re-homes to a standalone ADR later
   only if real trace data justifies it.
2. **OQ2 — capture → asked by default, skippable.** Affects **slice 01** (builds
   the default-on path). Project-type gating is **parked**, revisited per the EDD
   signal-gating precedent only if users report the default-on prompt as friction.
3. **OQ3 — coverage check → advisory (warn) first.** Affects **slice 03** (builds
   the advisory path). A gate is a later escalation if warnings prove
   insufficient.
