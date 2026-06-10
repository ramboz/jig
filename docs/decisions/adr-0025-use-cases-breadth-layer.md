---
dependencies: [docs/decisions/adr-0020-spec-frame-hardening.md, docs/decisions/adr-0014-review-evidence-model.md, docs/decisions/adr-0012-scaffold-tier-gated-install.md, docs/decisions/adr-0011-spec-gate-model.md]
last_verified: 2026-06-10
frame_review: true
---

# ADR-0025: Use cases as a first-class breadth layer

## Status

Accepted (2026-06-10)

## Context

jig's artifact stack runs **vision → spec → slice**. Specs are authored
*depth-first* — one at a time, each SPIDR-split into vertical slices. There is
**no breadth-first layer between the vision and the specs** that enumerates the
intended user-facing behaviors of the project as a whole.

The consequence shows up on **behavior-dense** projects (apps, multi-flow
services): with no shared frame to anchor against, each spec's author (an agent)
invents *that spec's slice of the world* ad hoc. Two specs touching the same
behavior reach different assumptions about it; a behavior nobody specs falls
through silently; scope creep (a spec serving no stated behavior) is invisible.
The depth-first workflow then executes each divergent frame *with discipline* —
the same failure shape [ADR-0020](adr-0020-spec-frame-hardening.md) names for
wrong *factual* frames: jig's rigor **masks** the divergence rather than catching
it.

**Root cause (confirmed with a user):** the scaffold never asked for use cases,
so they never entered the vision. This is verifiable in jig's own framing
machinery: [`product-vision.md.template`](../../templates/docs/product-vision.md.template)
captures Identity / Target users / Core problem / Competitive landscape / Scope /
Stack / Principles / How-new-work-enters / Open-questions — and the
`vision-elicitation` wizard fills exactly those slots. **None enumerates
behaviors.** "Target users" names *who* (personas); "Scope" names *features* in
priority order; neither is the goal-level **"[actor] can [goal]"** breadth model.
No use-case / behavior / scenario / jobs-to-be-done concept exists anywhere in
the vision template, the elicitation wizard, or `/jig:clarify`. The *gap* is
verified (see Assumptions §A1).

Two constraints shape the design (mirroring ADR-0020's framing):

1. **jig defaults lean.** Specs [055](../specs/055-context-cost-discipline/spec.md)/[057](../specs/057-thin-orchestrator/spec.md)
   spent real effort *removing* front-loaded ceremony. A breadth-capture step
   must earn its cost: on-by-default but **skippable**, and **droppable** for
   project classes where breadth modeling adds nothing (libraries, single-flow
   CLIs).
2. **The vision is a vision, not a requirements doc.** Use cases must stay
   *goal-level* ("a user can resume a draft offline"), never spec-level, or the
   vision bloats and stops being read.

**Evidence honesty (reflexive):** the evidence is thin — **one user, one Android
app**. This is the load-bearing premise (§A1) and it is *not measured*. The ADR
is therefore scoped as an **overridable default**, not a universal mandate, and
carries an explicit kill criterion (per the brief).

## Decision Options Considered

### Option A: Do nothing — depth-first specs + reconcile-time grounding only

Keep authoring specs depth-first; rely on the reconciliation pass (and the human)
to notice divergence after the fact.

- **Pros:** Zero added ceremony; preserves the 055/057 lean arc; the eventual
  reconcile backstop *does* catch some divergence.
- **Cons:** Catches divergence **late** — post-implementation, after tokens are
  already spent on a divergent frame — rather than preventing it; offers specs no
  shared frame to anchor against, so behavior-dense projects keep diverging; and
  it leaves the **root cause** (use cases are never captured) untouched.

### Option B (Recommended): A use-case breadth layer — captured at init, fed forward, coverage-checked at reconcile

Four coordinated, mostly-soft mechanisms. Each sub-decision below carries its
rejected alternative + rationale.

**B1 — Home: use cases live as a section in the project vision, not a separate
artifact.** Add a `## Use cases` H2 section to `product-vision.md` (and its
template), holding goal-level `"[actor] can [goal]"` entries, each marked with
the standard `<!-- elicited: … -->` slot marker so the elicitation wizard treats
it like any other section.
- *Rejected: a separate `behaviors.md`.* Three docs (vision / behaviors / specs)
  drift out of sync and cost tokens to keep coherent. The vision is *already* the
  breadth home — it holds Target users *and* Scope; a sibling doc would split the
  breadth frame across two files that must be cross-read to be understood. One
  doc, one breadth frame.

**B2 — Capture at init via a conversational loop, single normalize pass,
human-confirm before write.** At init (the `vision-elicitation` step), the user
enters behaviors in *any* shape — incremental or bulk paste; the wizard loops on
"anything else?"; then a **single normalize pass** (dedupe, split compound
entries, rephrase to goal-level `"[actor] can [goal]"`) is shown for
**confirm/edit before anything is written**.
- *Rejected: a single static question.* Users don't know the canonical phrasing,
  so a one-shot question yields malformed or empty input.
- *Rejected: silent inference of unstated use cases.* That is a **framing-layer
  hallucination at the root** — the most damaging place possible, because
  everything downstream grounds against this artifact. Inference is permitted
  **only as a surfaced question** ("you didn't mention X — intentional?"), never
  auto-folded into the artifact. (This refuses fabricated frame content, the same
  stance ADR-0020 takes on unverified factual claims — see Relationship.)

**B3 — Feed-forward + trace links: the spec step reads use cases as framing; each
spec cites the use case it serves.** Spec drafting reads the `## Use cases`
section as framing context, and each spec records a **trace link** to the use
case(s) it serves.
- *Rejected: grounding only at reconcile.* Reconcile runs *after* implementation,
  so it detects drift **after tokens are burned** rather than preventing it.
  Reconcile grounding stays as the **backstop** (B4), not the primary mechanism —
  the same "catch it early, where correction is cheapest" logic behind ADR-0020
  placing frame-critique at READY_FOR_REVIEW, not DONE.
- *Mechanism (deferred to the spec):* the trace link is most useful as
  **machine-resolvable metadata**, so coverage (B4) is a query, not a re-read.
  The proven shape is `dependencies:` frontmatter, which already powers the DONE
  dependency gate by resolving `NNN-MM` tokens, and `parsing.py` already supports
  list-valued frontmatter — so a `use_cases:` field is the same machinery.
  Whether the link lives in typed frontmatter or spec prose is spec 068's
  choice; either way it must be machine-resolvable for B4 (and per conventions a
  new frontmatter field updates `parsing.py` + templates together — a known,
  bounded cost).

**B4 — Coverage grounding at reconcile: flag use cases with no spec (gap) and
specs with no use case (creep).** At reconcile, a **bidirectional** coverage
check flags use cases with no implementing spec (**coverage gap**) and specs with
no parent use case (**scope creep**) — the same must-be-covered-or-flagged shape
as the grounding ADR's claim-coverage logic.
- *It is a deterministic cross-artifact query, not a reviewer pass.* Coverage is a
  **set-difference** over the vision's use-case ids and the specs' B3 trace links —
  a pure computation, so it needs **no new reviewer subagent**. But it is
  **net-new (bounded) surface, not free reuse**: a probe of the existing surfaces
  (§A4) shows neither hosts a project-wide view — the reconciliation reviewer
  ([ADR-0014](adr-0014-review-evidence-model.md)) is *per-slice +
  deviation-log-scoped and never reads the vision*, and `/jig:analyze` is
  *one-spec-at-a-time (cross-spec explicitly unsupported in its MVP)*. So B4 is a
  **new** project-wide coverage query (a `workflow.py` helper, or a cross-spec
  extension of analyze) **surfaced at** the reconcile checkpoint — distinct from
  the per-slice reviewer that also runs there. (See §A4 + Relationship.)
- *Advisory vs. gate:* flagged as **OQ3**; the family default (ADR-0011/0020) is
  **advisory/warn**, escalatable to a gate per a later spec.

- **Pros:** Catches divergence **early** (at spec-draft framing) where correction
  is cheapest, with reconcile as a backstop; gives behavior-dense projects a
  shared anchor; addresses the actual root cause (capture at init); reuses the
  existing **capture** machinery (vision section + elicitation wizard) and adds
  only a **bounded, deterministic coverage helper** for B4 — no new reviewer
  subagent (§A4); **overridable** so it never taxes project classes that don't
  need it.
- **Cons:** Adds an init capture step + a per-spec trace-link discipline + a new
  (bounded) coverage helper (§A4); rests on **thin evidence** (§A1); risks the
  use-case section drifting toward a requirements doc (mitigated by the goal-level
  constraint + normalize pass); and — the subtler risk — goal-level use cases may
  be **too coarse** to anchor the spec-level assumptions that actually diverge, so
  coverage can read "complete" while specs still diverge on a behavior's details
  (**false coverage confidence** — §A2, watched by a kill criterion that measures
  divergence-prevention, not just link existence).

### Option C (Deferred — documented, not built): mid-flight blast-radius triage lifecycle

When a use case is added **after** N specs already exist, handling is
**blast-radius triage** — *not* a fixed reframe flow, and *not* "just a new spec":

- **Additive** (no intersection): capture + confirm into the vision, spawn
  spec(s). Default, frictionless. Project size is irrelevant here.
- **Conflicting** (intersects existing specs/assumptions): flag only the
  **specific intersecting specs**, surface to the human, decide per-spec. Bounded
  to the intersection — the B3 trace links make blast radius a **query, not a
  re-read**.
- **Reframing** (contradicts the vision's framing): escalate as an **ADR-grade
  decision**; human-driven. Do **not** auto-re-review the whole project —
  re-reading N specs to "reconcile against the new framing" is
  shallow-analysis-at-scale and burns the 055/057 cost ceiling.
- **Triage default is asymmetric:** when unsure, treat as a **conflict-candidate**
  and surface to the human; never wave through as additive. Misclassifying a
  conflict *as* additive is the silent-corruption failure mode.

**Why deferred (mirrors ADR-0020 Option C — best-of-N drafting):**
- It is **load-bearing on B3's trace links being real and populated** —
  blast-radius-as-a-query only works once specs actually carry resolvable trace
  links and there is a corpus to query.
- It is the **thinnest-evidence part** (the rare reframe class — one user, *zero*
  observed mid-flight reframe events).
- Building a triage lifecycle now would be designing a classifier against
  *imagined* trace data.

**Revisit trigger:** reconsider only once **(a)** B3 trace links exist and are
populated across a real spec corpus, **AND (b)** there is real trace data of a
mid-flight use-case addition that intersects existing specs (a genuine
conflict/reframe event), so the triage classifier can be validated against an
*actual* case. Record the direction now; do not build until then.

## Recommended Decision

Adopt **Option B** — the four built mechanisms — sequenced as spec
[068](../specs/068-use-cases-breadth-layer/spec.md)'s slices 01→03 (capture +
section → feed-forward + trace → reconcile coverage). **Defer Option C** (the
mid-flight triage lifecycle) per the revisit trigger; the full triage design is
recorded here so the analysis isn't lost.

Scope discipline (mirroring ADR-0020):
- The capture step is an **overridable Tier-1 default** — on by default,
  per-section **skippable** (the wizard's existing skip mechanic), and
  **droppable** to Tier 2 / left empty for project classes where breadth modeling
  adds nothing (libraries, single-flow CLIs).
- Every mechanism is **advisory / deliberateness-signal** (ADR-0011), never a
  hard blocking gate — the coverage check's advisory-vs-gate posture is OQ3.
- Use cases stay **goal-level**, never spec-level.
- **Do not** pull Option C into implementation (spec 068's slice 04 documents it
  as deferred).

## Consequences

**Becomes easier:**
- Behavior-dense projects get a shared breadth frame to anchor specs against —
  less ad-hoc per-spec divergence.
- Divergence is caught **early** (spec-draft framing), with reconcile as a
  backstop — not only post-hoc.
- Coverage gaps (unimplemented behaviors) and scope creep (specs serving no stated
  behavior) become a **query**, not a manual audit.

**Becomes harder:**
- Init gains a capture step; behavior-dense projects pay a small up-front cost
  (bounded by skippability + tier-drop).
- Specs carry a trace-link discipline. Without it, **B4's coverage check is
  inert** — B4 is load-bearing on B3 being real, the *same* dependency that
  defers Option C.
- B4 is **net-new (bounded) surface**, not free reuse: a project-wide coverage
  query that today's per-slice reconciliation reviewer + one-spec-at-a-time
  analyze do **not** provide (§A4). Deterministic (no reviewer subagent), but real
  work to build.
- Risk of vision bloat toward a requirements doc *and* the subtler **false
  coverage confidence** risk if goal-level entries are too coarse (§A2) — both
  kill-criterion-watched.

## Scope

- **In:** a `## Use cases` vision section + template slot; conversational init
  capture (loop + single normalize + human-confirm); feed-forward into spec
  drafting + per-spec trace links; a reconcile-phase bidirectional coverage check
  (advisory default). Overridable Tier-1 default.
- **Out (this ADR):** the mid-flight blast-radius triage lifecycle (Option C —
  documented, deferred w/ trigger); any hard blocking gate; spec-level (vs.
  goal-level) use cases; a separate `behaviors.md`.

## Assumptions

> Per this ADR's own grounding standard (ADR-0020), load-bearing claims are
> listed rather than asserted as fact.

- **A1 — breadth-divergence on behavior-dense projects is real and recurs at a
  rate that justifies the layer.** *Unverified — thin evidence:* one user, one
  Android app. This is the load-bearing premise and it is **not measured**; its
  kill criterion is below. *Grounded only as:* the **root cause** ("the scaffold
  never asked, so use cases never entered the vision") is **confirmed** against
  jig's own vision template + elicitation wizard, which carry no use-case concept.
  The *gap* is verified; the *harm rate* is assumed. The overridable-default
  scoping mitigates **one** failure direction only — a project class that
  *doesn't* need the layer drops it at zero cost. It does **not** cover the other
  direction (adopting projects that pay the cost but don't actually diverge less);
  that risk is §A2.
- **A2 — capture at init reduces divergence more than it adds friction**, on the
  project classes that opt in. *Unverified.* The sharpest exposure: goal-level use
  cases (`"[actor] can [goal]"`) may be **too coarse** to anchor the spec-level
  assumptions that actually diverge — so adopting projects could get **false
  coverage confidence** (every use case maps to a spec, yet the specs still
  contradict each other on the behavior's details). Two distinct failure modes
  share this exposure: the entries are **too coarse** (grain), *or*
  **feed-forward-by-reading simply doesn't bind** — the spec-drafting agent emits
  trace links mechanically without internalizing the breadth frame, because
  ad-hoc divergence may be a property of *depth-first authoring under context
  pressure* (055/057), not merely of whether a breadth doc exists. Measurable
  post-ship, but only by the *right* signal: not uptake + link-existence, but
  whether trace-linked specs show **less contradiction/overlap on shared
  behaviors** than before. This is the kill-criterion target (corrected below) —
  it catches **both** failure modes.
- **A3 — trace links can be represented as machine-resolvable metadata at
  acceptable cost.** *Grounded by precedent:* `dependencies:` frontmatter already
  resolves `NNN-MM` tokens for the DONE gate, and `parsing.py` already parses
  list-valued frontmatter (`_parse_flow_list`), so a `use_cases:` field is the
  same proven machinery; the conventions rule (a new field updates `parsing.py` +
  templates together) bounds the cost. To be confirmed in spec 068's interface
  slice, not assumed.
- **A4 — RESOLVED by probe (corrected from the original draft): B4 is net-new
  (bounded) surface, not free reuse — but needs no reviewer subagent.** The
  original draft assumed B4 could *ride* the reconciliation reviewer / analyze. A
  probe falsifies the *reuse* half: `review.py`'s reconciliation prompt is
  **per-slice + deviation-log-scoped and never reads the vision** (no whole-project
  view), and `/jig:analyze` is **one-spec-at-a-time — cross-spec input is
  explicitly unsupported in its MVP**. A project-wide, bidirectional vision↔spec
  coverage check is therefore a **new** capability (a `workflow.py` helper, or a
  cross-spec extension of analyze), not a line added to an existing prompt. It
  does need **no new reviewer subagent**, though: coverage is a deterministic
  set-difference over use-case ids ↔ trace links, not a judgment call. Net: B's
  cost is *higher* than a naive "low net-new surface" reading (a real helper to
  build) but lower than "a new reviewer pass." *(This correction was caught by
  this ADR's own frame-critique — see
  [adr-0025-frame-critique.md](reviews/adr-0025-frame-critique.md).)*

## Kill criteria

- **Required (per the brief) — kills the default:** behavior-dense projects need
  this; **if** the overridable default sees **low uptake** (scaffolded projects
  routinely skip or empty the use-case section) **OR** the capture loop is felt as
  **friction without payoff**, **drop it** — demote to Tier 2 / remove the default.
- **Kills the value claim even at high uptake (the false-coverage trap, §A2):** if
  trace-linked specs show **no less contradiction/overlap on shared behaviors**
  than before — coverage reads "complete" but divergence persists because
  goal-level entries are too coarse — the layer is *measuring the wrong thing*;
  **drop it** (or push capture to a finer grain). This signal is **distinct from
  uptake/link-existence and must be watched separately**: a project can have 100%
  coverage and still diverge.
- **Kills feed-forward + trace specifically:** if specs routinely carry **no
  resolvable trace link** in practice (authors skip it), B4's coverage check is
  inert and B3 is ceremony — drop the trace requirement, keep the section as
  documentation-only.
- **Kills Option C's revisit:** if, after trace links are real and populated, **no
  genuine mid-flight conflict/reframe event ever materializes**, the triage
  lifecycle stays deferred indefinitely — its premise (conflicts occur and need
  bounded handling) was never observed.

## Relationship to other decisions

- **[ADR-0020](adr-0020-spec-frame-hardening.md) — frame-hardening (grounding +
  frame-critique).** Three relationships:
  1. **Orthogonal grounding targets that converge — not a shared mechanism.**
     ADR-0020 grounds **factual claims** about runnable surfaces (*is this
     library capability real?*) — truth-of-claim. This ADR grounds **behavior
     coverage** (*is every intended behavior served by a spec, and every spec by a
     behavior?*) — coverage-of-frame. Different targets, but they **converge on
     two shared chokepoints**: **(a) the human-confirm gate** — ADR-0020's human
     reads the frame-critique verdict; this ADR's human confirms the normalized
     use-case set before write (B2); **(b) the reconcile checkpoint** — B4's
     coverage finding is *surfaced at* reconcile, the same checkpoint where
     ADR-0014's reconciliation reviewer runs and the same human reads it. But B4
     is a **deterministic query, not a reviewer pass** (§A4) — it does **not**
     share, ride, or extend the reconciliation reviewer's prompt (which is
     per-slice and never reads the vision). Stated explicitly so the two **do not
     duplicate or silently overlap** reviewer machinery: this ADR adds **no new
     reviewer subagent** — the convergence is a shared *checkpoint + human*, not a
     shared mechanism.
  2. **Deferral pattern reused.** Option C here mirrors ADR-0020's Option C
     (Tier-2 best-of-N drafting): a fully-documented design, deferred behind an
     explicit revisit trigger, captured so the analysis isn't lost.
  3. **Anti-fabrication stance shared.** ADR-0020 forbids asserting unverified
     factual claims as fact; this ADR forbids silently inferring unstated use
     cases (B2). Both refuse fabricated frame content and surface the gap as a
     *question* instead.
- **[ADR-0014](adr-0014-review-evidence-model.md) — review-evidence model.** B4 is
  a deterministic coverage helper **surfaced at** the reconcile checkpoint — **not**
  a new gated review pass and **not** an extension of the reconciliation reviewer
  (§A4); whether it *blocks* (gate) or *warns* (advisory) is OQ3.
- **[ADR-0012](adr-0012-scaffold-tier-gated-install.md) — tier-gated install.**
  The capture step is the **overridable Tier-1 default**; tier-drop is the
  override mechanism for project classes that don't need breadth modeling.
- **[ADR-0011](adr-0011-spec-gate-model.md) — soft-gate posture.** Every mechanism
  here is advisory / deliberateness-signal; real enforcement stays out-of-band.

## Open questions

> Resolved with the human on 2026-06-10 (at acceptance). The decision leads each
> item; the original trade-off analysis is preserved below it.

1. **OQ1 — ADR granularity → RESOLVED: one ADR for now.** The mid-flight lifecycle
   (Option C) stays a deferred section here rather than its own ADR. *Interwoven
   rationale (the deciding factor):* the triage taxonomy is load-bearing on B3's
   trace links and shares B4's coverage logic — separating them fragments a single
   decision. *Revisit:* split into a standalone ADR (with its own frame-critique)
   later **if** real trace data makes the triage lifecycle a substantial decision
   in its own right.
2. **OQ2 — capture default vs. project-type gating → RESOLVED: asked by default,
   skippable.** The capture question fires for all project classes (insistence
   over ceremony); a user who doesn't want it skips the section. **Type-gating is
   parked, not chosen** — revisit per the EDD (eval-driven development)
   signal-gating precedent (LLM/agent detection for EDD; the team-signal detection
   in [spec 050](../specs/050-solo-team-redetection/spec.md); the derived
   `frame_review` trigger in [064-04](../specs/064-spec-frame-hardening/slice-04-derived-trigger.md))
   **if users report the default-on prompt as friction.** Slice 01 keeps the
   gating hook cheap to add later.
3. **OQ3 — coverage check advisory or gate → RESOLVED: advisory (warn) as the
   first step.** On a coverage gap / scope creep the check **warns**, it does not
   block — the family default ([ADR-0011](adr-0011-spec-gate-model.md) /
   [ADR-0020](adr-0020-spec-frame-hardening.md)). A gate is the **later
   escalation** if warnings prove insufficient (gaps go unaddressed when only
   warned). Slice 03 builds the advisory path.
