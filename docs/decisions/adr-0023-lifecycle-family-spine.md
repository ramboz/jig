---
dependencies: [docs/decisions/adr-0014-review-evidence-model.md, docs/decisions/adr-0016-bug-fix-lifecycle.md, docs/decisions/adr-0019-refactor-workflow.md, docs/decisions/adr-0022-pluggable-oracle-boundary.md]
last_verified: 2026-06-09
frame_review: true
---

# ADR-0023: The lifecycle-family spine — shared contract and convergence rule for gated-evidence workflows

## Status

Proposed (2026-06-09)

## Context

jig has organically grown a **family of work-shaped lifecycles**, each
recorded in its own ADR, each independently re-deriving the same
architecture:

| Member | Backbone (distinctive middle) | ADR |
|---|---|---|
| `spec-workflow` | specify intent → vertical slices | (lifecycle in `docs/workflow.md`; gate in [ADR-0014](./adr-0014-review-evidence-model.md)) |
| `jig:bug-fix` | root-cause → prove → prevent regression | [ADR-0016](./adr-0016-bug-fix-lifecycle.md) |
| `jig:refactor` | capture baseline → restructure → prove equivalence | [ADR-0019](./adr-0019-refactor-workflow.md) |

Read side by side, ADR-0016 and ADR-0019 say *the same structural thing in
different words*: "a parallel, proportional, teeth-gated lifecycle that
**mirrors `workflow.py transition`'s gate architecture** (ADR-0014),
**reuses `_common/`** rather than forking, inherits **ADR-0011**'s
deliberateness/trust-boundary posture and **ADR-0015 / spec-049**'s
reservation+claim machinery, **de-escalates trivial work**, and offers a
**first-class escape seam** to another member (bug→spec escalate;
refactor→spec carve-out)." [ADR-0022](./adr-0022-pluggable-oracle-boundary.md)
then added a shared **pluggable oracle** to the same set and, in its Scope,
**explicitly flagged this gap**: "extract a shared `_common/lifecycle.py`
transition-gate engine … deferred to implementation; rule-of-three."

So the pattern is real but **implicit and re-asserted per ADR**. There is no
single decision that (a) *names* the family, (b) states the **contract**
every member must uphold, and (c) decides **how and when** the three
hand-mirrored implementations converge onto shared code. Leaving it implicit
has two costs:

- **Drift.** Each lifecycle is free to invent slightly different gate
  semantics, status vocabularies, record shapes, or bypass conventions —
  divergence that is cheap to prevent now and expensive to reconcile later.
- **Re-litigation.** Every future work-shape (go-live, data-migration,
  dependency-upgrade, incident) reopens the same design questions from
  scratch, because there is no recorded template for "what makes something a
  jig lifecycle."

This ADR records the organizing pattern as a first-class decision. It is a
*governance / architecture* decision — once multiple helpers depend on the
contract it is costly to reverse — which is why it is an ADR and not a
`docs/workflow.md` paragraph.

Two constraints bound it:

- **Do not mandate premature extraction.** ADR-0022 already deferred the
  shared `_common/lifecycle.py` module to implementation time, and ADR-0003's
  own lesson is *extract on the rule of three, from real duplication* — not
  from one example plus two designs. The spine is a **contract first**; the
  shared **module** comes on the third concrete implementation.
- **Do not distort the backbones.** The spine is the shared *substrate*
  (gates, evidence, reservation/claim, oracle, proportionality, escape seam)
  — NOT the per-lifecycle backbone (specify-slices vs root-cause vs
  preserve-behaviour). Each member keeps its distinctive states and gates.

## Decision Options Considered

### Option A: Leave it implicit (status quo)

Each new lifecycle ADR re-derives the pattern from its predecessors.

- **Pros:** Zero upfront work; maximum per-lifecycle freedom.
- **Cons:** Drift in gate/status/record semantics goes unmanaged; every new
  work-shape re-litigates settled questions; there is no single place that
  answers "to add a lifecycle, satisfy *this*." The duplication ADR-0022
  flagged stays unowned.

### Option B: Extract `_common/lifecycle.py` now

Build the shared engine immediately and refactor the shipped `spec-workflow`
onto it, ahead of `bug.py` / `refactor.py`.

- **Pros:** DRY at once; one engine to maintain.
- **Cons:** Premature. Only `spec-workflow` is implemented; `bug.py` /
  `refactor.py` are paper. Abstracting from one concrete example (plus two
  designs) risks the *wrong* abstraction (ADR-0003), and churns a stable,
  shipped workflow for speculative reuse. Contradicts ADR-0022's deferral.

### Option C: Record the spine as a contract + convergence rule, not code yet (recommended)

Name the family; define the invariants every member must satisfy; adopt an
explicit rule-of-three convergence so the shared **module** is extracted when
— and only when — the third concrete `transition` implementation makes the
duplication real.

- **Pros:** Captures the pattern, prevents drift, stops re-litigation, *and*
  avoids the premature/wrong-abstraction trap. Consistent with ADR-0002 /
  ADR-0003 and ADR-0022. Cheap — a document, no code churn.
- **Cons:** The contract is prose-enforced until extraction (a member could
  violate it before `_common/lifecycle.py` exists); mitigated by the
  convergence rule and reviewer awareness. A two-step (contract now, module
  later) is marginally more process.

## Recommended Decision

**Option C.** Record the spine as a contract plus a convergence rule.

### 1. The family

A **work-lifecycle** is a gated-evidence state machine that carries a unit of
work from intake to DONE, where each load-bearing transition is gated on a
durable, presence/shape-checked evidence artifact. Current members:
`spec-workflow`, `jig:bug-fix` (ADR-0016), `jig:refactor` (ADR-0019). The
*spine* is what they share; the *backbone* (the distinctive middle states) is
what differs and stays per-member.

### 2. The spine contract — every member MUST uphold

- **C1 — Gated transitions on durable evidence.** Load-bearing transitions
  refuse unless a durable artifact exists and is shape-valid. Gates check
  presence / shape / declared-verdict, **never quality** — quality is the
  reviewer's job ([ADR-0014](./adr-0014-review-evidence-model.md)).
- **C2 — Deliberateness, not sign-off.** Gates sit inside the agent's trust
  boundary, are **env-bypassable** as a deliberate act, and **fail closed**
  on a tooling error (exit 2). Real enforcement is out-of-band
  ([ADR-0011](./adr-0011-spec-gate-model.md)).
- **C3 — Durable, claimable, reviewable record.** One numbered record per
  work item (frontmatter machine-fields + human body) on its own board;
  numbering + `claimed_by` reuse [ADR-0015](./adr-0015-worktree-aware-reservation.md)
  / [spec-049](../specs/049-slice-claim-on-in-progress/spec.md) (local by
  default; `--push` reserves on `origin/main`; `--release` force-clears).
- **C4 — Proportionality / downward de-escalation.** A triage step that
  **refuses ceremony for trivial work** (bow out → just commit). Ceremony is
  earned, not default (ADR-0016 §3 / ADR-0019 §4).
- **C5 — Verification via the pluggable oracle.** The terminal verification
  gate is backed by the [ADR-0022](./adr-0022-pluggable-oracle-boundary.md)
  pluggable oracle (deterministic via `tdd.py`, machine-witnessed; eval /
  composite via servo, attest-only; soft-degrade when servo is absent). jig
  attests; it does not run evals.
- **C6 — Reuse `_common/`, don't fork.** Members borrow
  `review_evidence.py`, `parsing.py`, the reviewer machinery, and `tdd.py` —
  never re-implement them.
- **C7 — A first-class escape seam.** Each member names the off-ramp to a
  *different* member when the work turns out mis-shaped (bug→spec escalate;
  refactor→spec carve-out). Mis-shaped work is re-routed, not force-fit.

### 3. The convergence rule (rule-of-three)

Members **inline-mirror** the transition/gate logic until the **third
concrete `transition` implementation** exists in code. That third
implementation **triggers extraction to `_common/lifecycle.py`** (the states
table, the gate predicate, evidence wiring, reservation/claim, oracle
dispatch), after which members are reduced to **descriptors** — their states,
gates, oracle bindings, and tier policy — over the shared engine. This is
[ADR-0002](./adr-0002-contracts-stays-deferred.md) /
[ADR-0003](./adr-0003-extract-find-slice-section.md) applied at the
lifecycle-engine level.

**State today:** `spec-workflow` is implemented (1 concrete); `bug.py` and
`refactor.py` are designs (0 concrete). **Extraction is therefore not yet
triggered** — exactly the posture ADR-0022 deferred to. The contract (§2) is
the coordination mechanism until then; the module enforces it after.

### 4. What is NOT a family member (scope boundary)

- A **gate *over* a lifecycle** — e.g. the deferred go-live /
  production-readiness checklist — is **not** a lifecycle. It is a
  milestone-level Definition of Done that *consumes* the same evidence/oracle
  substrate (it may reuse spine primitives) but does **not** get its own
  state machine, because it has no distinct backbone — it is a checklist of
  evidence, not a path from intake to DONE.
- **Spikes** (`kind: spike`) are a spec sub-shape, not a separate lifecycle.
- **Trivial one-off work** bows out under C4 — it never gets a record.

### 5. Adding a future member

To add a work-lifecycle (data-migration, incident, dependency-upgrade, …) an
ADR must show **(a)** a distinct backbone not already served by an existing
member, and **(b)** conformance to C1–C7. If that addition is the *third*
concrete implementation, it also triggers the §3 extraction.

## Consequences

**Becomes easier:**

- One recorded contract to conform to; no per-ADR re-derivation; drift across
  members is prevented at the source.
- Future work-shapes get a decision template ("distinct backbone + satisfy
  C1–C7"), so the recurring "should this be a spec, a bug, or its own thing?"
  question has a structured answer.
- The extraction trigger is unambiguous — no debate about *when* to DRY.

**Becomes harder:**

- Until `_common/lifecycle.py` exists, the contract is prose-enforced; a
  member could violate C1–C7 (mitigated by the convergence rule + reviewers
  who now have a checklist).
- Adding a member costs a short "distinct backbone" argument — deliberate
  friction against lifecycle sprawl.

**Neutral:** no code changes now. This ADR is governance; it ratifies a
pattern three ADRs already follow and sets the rule for the next one.

## Assumptions

<!-- Spec 064-02 / ADR-0020 §1–§2 — grounding-by-probe (risk-gated). -->

- **The three lifecycles share a genuine spine, not a superficial
  resemblance.** Grounded: ADR-0016 and ADR-0019 *explicitly* state they
  mirror `workflow.py`'s gate architecture, reuse `_common/`, and adopt
  ADR-0011/0014/0015; ADR-0019 calls itself "same architecture, different
  backbone" relative to ADR-0016. (Verified by reading both ADRs in full.)
- **`bug.py` / `refactor.py` are not yet implemented,** so the rule-of-three
  extraction is not yet triggered. Grounded: both ADRs are Proposed; no
  `docs/bugs/` or `docs/refactors/` helper exists on disk.
- **The rule-of-three is jig's accepted convergence heuristic.** Grounded:
  ADR-0002 / ADR-0003.

## Kill criteria

- If the three backbones turn out to require *materially different* gate or
  evidence semantics (C1/C2 do not actually generalize), the spine is a false
  abstraction → demote this to "documented similarity" and drop the
  convergence rule.
- If a fourth-plus work-shape repeatedly cannot fit C1–C7, the contract is
  too narrow → revisit the invariants rather than forcing conformance.
- If, at extraction time, `_common/lifecycle.py` requires heavy per-member
  special-casing (members fight the engine), the seam is wrong → keep
  inline-mirroring (ADR-0003's "extract only when it pays").

## Scope

**In scope:** naming the family; the C1–C7 contract; the rule-of-three
convergence rule; the non-member boundary (§4); the add-a-member bar (§5).

**Deferred (named, no slice reserved):**

- **The actual `_common/lifecycle.py` extraction** — triggered by the third
  concrete `transition` implementation (already named in ADR-0022's Scope).
- **Go-live / production-readiness** as a milestone-level DoD *over* the
  spine (not a member).
- **A machine-checkable conformance lint** for C1–C7 (vs prose + reviewer
  judgment) — see Open questions.

**Out of scope:** implementing `bug.py` / `refactor.py` (their own ADRs);
changing `spec-workflow`'s shipped behaviour; CI enforcement of the contract.

## Relationship to other decisions

- **[ADR-0014](./adr-0014-review-evidence-model.md)** — supplies C1 (the
  durable-evidence gate pattern the whole family mirrors).
- **[ADR-0011](./adr-0011-spec-gate-model.md)** — supplies C2 (deliberateness
  inside the trust boundary, not human sign-off).
- **[ADR-0015](./adr-0015-worktree-aware-reservation.md) / spec-049** —
  supply C3 (reservation + claim/release).
- **[ADR-0016](./adr-0016-bug-fix-lifecycle.md) /
  [ADR-0019](./adr-0019-refactor-workflow.md)** — the two members that, with
  `spec-workflow`, constitute the family; this ADR generalizes what each
  asserts separately.
- **[ADR-0022](./adr-0022-pluggable-oracle-boundary.md)** — supplies C5 (the
  pluggable oracle); this ADR records the spine that ADR-0022's Scope said
  was deferred.
- **[ADR-0002](./adr-0002-contracts-stays-deferred.md) /
  [ADR-0003](./adr-0003-extract-find-slice-section.md)** — supply the
  convergence rule (rule-of-three; extract to `_common/` from real
  duplication).

## Open questions

- **Does `spec-workflow` itself get refactored onto `_common/lifecycle.py`
  at extraction time, or only the new members?** Lean: eventually yes (it is
  the proven reference), but only *after* the engine is validated by the two
  new members — do not churn the stable workflow first.
- **Should C1–C7 be machine-checkable (a conformance lint) or stay prose +
  reviewer judgment?** Lean: prose now; add a lint only if drift actually
  appears (mirrors ADR-0014's "the gate is the check, not a hook").
- **Is go-live truly a gate-over-lifecycle and not a member?** Lean:
  gate-over (no distinct backbone — it is a checklist of evidence), but
  confirm when it is specced.
