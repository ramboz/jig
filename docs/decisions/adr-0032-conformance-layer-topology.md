---
status: Proposed
dependencies: []
last_verified: 2026-06-27
frame_review: true
---

# ADR-0032: Conformance layer — jig owns the canonical↔implementation graph topology

## Status

Proposed (2026-06-27)

> **This is the jig half of a paired decision.** The servo half —
> fidelity *scores* and the convergence *trend ledger* that decorate the graph
> — is **servo ADR-0017** (Proposed, same date). Each ADR is the single source
> for its half; neither restates the other. Both are **recorded ahead of a
> committed consumer** (the ADR-0022 / servo ADR-0005 "integrate on signal"
> pattern) and stay **Proposed** until the demand trigger below fires.

## Context

A recurring, hard problem when an LLM builds a UI incrementally from a canonical
design (e.g. Claude Design `.dc.html` exports + a prose `design-system.md` token
contract): **each slice must be locally scoped but globally convergent.** You
hold complete final mocks, but specs/slices implement portions — and you need
the app to *converge* toward the final design rather than become a pile of
individually-correct but collectively-inconsistent screens.

Two observations reframe this away from "build a UI checker":

1. **It is one instance of a general problem — *contract conformance*:** keep a
   generated implementation coherent with an *evolving canonical contract*
   across many independently-scoped increments. jig already has **instance #0**
   — external API contracts (`jig-boundary-change-warn.sh` + the `contracts`
   skill watch OpenAPI/proto/GraphQL and flag drift). A design system is the
   same problem with a **visual** contract — **instance #1**.
2. **The per-slice (local) loop is already shipped.** servo `/servo:design-eval`
   (servo ADR-0009: render the reference, screenshot the app at a seeded state,
   vision-judge fidelity, freeze) + jig's attest-only `design_review` pass
   ([spec 071](../specs/071-design-review-pass/spec.md)) already answer "does
   *this slice's* UI match *this increment's* mock." What has **no home** is the
   **global convergence** half — *is the whole app moving toward the final
   design, and which canonical pieces are unbuilt or have drifted?*

## Decision (direction — Proposed, not a commitment to build)

Introduce a **conformance layer** built on a single durable, versioned,
queryable **conformance graph**. Nodes = `(canonical element @ version) ↔ (code
unit) ↔ (verdict slot)`; edges = component-reuse dependencies. The graph makes
"is the app converging?" a **query**, not a recomputation.

**The boundary (this generalizes ADR-0022's attest-only seam):**

- **jig writes the graph's TOPOLOGY (this ADR)** — deterministic structure:
  which code unit implements which canonical element, per-slice **scope**,
  **debt** (as a typed expiring waiver), **staleness** (`design_ref` pinning),
  **sanctioned-divergence** (a node state), the deterministic conformance rungs
  (token/component lint + semantic-principle assertions), and the convergence
  query itself.
- **servo writes the graph's SCORES** — non-deterministic fidelity verdicts +
  the convergence trend ledger. **Single-sourced in servo ADR-0017**; jig never
  re-derives a score (attest-only).

This preserves the jig = deterministic-structure / servo = non-deterministic-eval
philosophy and keeps the coupling loosest-possible (the graph is the contract;
two writers, neither re-derives the other's half).

## Consequences

**Positive.** "Global convergence" gets a concrete home (the graph) and a
mechanical definition (below). The design-fidelity case stops being a one-off:
the same graph + staleness + blast-radius machinery is reusable for the
API-contract instance #0 jig already half-has. The local loop (design-eval +
design_review) is reused unchanged as the per-node score source.

**Negative / cost.** A new durable artifact to maintain and version. Two
*Proposed* paired ADRs (this + servo ADR-0017) can drift while both are unbuilt
— mitigated by each owning exactly one half and citing the other as the single
source. The graph is only as good as the canonical being committed + diffable
(see Assumptions A1).

## Assumptions

These are load-bearing requirements distilled from a live adversarial
pressure-test (2026-06-27); they are not optional polish.

- **A1 — Convergence needs no frozen "final"; it is a *staleness* problem.**
  Claude Design re-exports the design system *wholesale*, so there is no fixed
  target. Pin a `design_ref: design_vN` per node; a re-export is a **staleness
  event** (reuse `workflow.py stale`'s dep-changed model; re-opening DONE
  screens is [ADR-0010](adr-0010-amendment-scope-records-vs-live-prose.md)
  closed-spec-drift territory). Convergence = *no unsanctioned drift from the
  pinned version* + *a shrinking unbuilt/stale set as versions advance.*
- **A2 — Convergence-checking must be OFF until "design-stable".** The design
  system is itself emergent early (the first screens *discover* the component
  boundaries); arming the graph from slice 1 punishes the discovery that
  *produces* the canonical. Mirror the scaffold-stable threshold
  ([ADR-0001](adr-0001-scaffold-stable.md)).
- **A3 — Shared-component visual blast-radius is a NEW primitive** neither tool
  has. Editing a component node must re-eval the dependent screens (jig
  `impact`/blast-radius, for visuals). This is the most likely way
  "individually-correct screens" go collectively wrong, and probably the
  highest-value missing piece.
- **A4 — "Sanctioned-divergent" is a first-class node state.** Real apps ship
  intentional inconsistency (onboarding that breaks the chrome, an experimental
  screen). Without this state the convergence report cries wolf on deliberate
  choices.
- **A5 — Debt must be a typed, expiring waiver** keyed to a paydown slice, or it
  rots into a TODO that lies. (Same lesson as `refinement-todo` triggers,
  mechanized.)
- **A6 — Lead with the cheap deterministic rungs; the VLM is last.** Rung-0
  token/component lint + rung-1 semantic-principle assertions catch egregious
  drift cheaply and own most of the anti-drift value; servo's VLM fidelity rung
  is the heaviest *and* least load-bearing. Rung-0 is a smoke alarm, not a proof
  (false-positive tail; cannot verify semantic token correctness; is gated on
  someone first authoring the token→theme map).

## Kill criteria / demand trigger

**Promote Proposed → build only when a real consumer commits to an automated
design gate** (SymPill's v1.2.3 Today screen is candidate #1; food-log is the
existing design-eval consumer). Until then this is recorded-ahead-of-consumer.
**Kill it** if, after the first real consumer, the deterministic rungs (0/1) +
the existing per-slice design_review prove sufficient and no "individually-fine,
collectively-drifting" incident materializes — i.e. the *global* graph never
earns its keep over per-slice attestation + a hand-maintained checklist.

## Roadmap if promoted (dependency-sequenced; NO spec numbers reserved)

P0 canonical as a versioned, diffable contract → P1 the graph itself (even
hand-maintained; jig topology) → P2 deterministic rung-0/1 decorate nodes → P3
staleness + re-pin events → P4 shared-component blast-radius → P5 servo VLM
fidelity + score-trend ledger decorate the graph (servo ADR-0017) → P6
convergence as a lifecycle query (armed post-design-stable, honoring
sanctioned-divergent). Lay P1 early so everything else is a query against it;
sequence the VLM (P5) last.

## Open questions

- **Where does the graph physically live?** A `docs/` artifact, a `.jig/` state
  file, or a generated board (sibling of the status board)? Leaning: a
  committed, diffable artifact so re-pin diffs are reviewable.
- **Is instance #0 (API contracts) retrofitted onto the same graph,** or does
  the graph stay design-specific until a second instance demands generalization
  (rule-of-three)?
- **Build-vs-use:** the first real use should run on a real app with today's
  primitives + the cheap rung-0, and let that pull P1+ — not a speculative
  build.

## Relationships to other decisions

- [ADR-0022](adr-0022-pluggable-oracle-boundary.md) — the pluggable-oracle
  boundary / attest-only seam this **generalizes** (per-slice attest → a durable
  multi-element graph).
- [ADR-0014](adr-0014-review-evidence-model.md) — the review-evidence rails the
  per-node verdicts ride.
- [ADR-0025](adr-0025-use-cases-breadth-layer.md) / [spec 068](../specs/068-use-cases-breadth-layer/spec.md)
  — the use-cases breadth layer + `workflow.py coverage` bidirectional check is
  the **structural-coverage pattern to copy** for the convergence query.
- **servo ADR-0017** — the paired scores/ledger half (single source for fidelity
  scores + the convergence trend).
- servo ADR-0005 (eval-oracle component / ledger) + servo ADR-0009
  (`/servo:design-eval`) — the shipped per-slice loop this builds on.
- jig inbox `design-conformance / visual-oracle` entries (2026-06-10,
  2026-06-11) — the per-slice precursors this generalizes.
