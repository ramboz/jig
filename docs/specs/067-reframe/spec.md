---
status: DONE
skill: reframe
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 067: Reframe — re-baseline the corpus when a load-bearing reference moves

## Overview

jig keeps work **consistent with prior decisions**: every spec and Architecture
Decision Record (**ADR**) is a durable record, and new work reads the accepted
corpus as authoritative. That is jig's core strength — and its blind spot when a
**load-bearing premise changes from outside the system.**

The motivating failure: a team scaffolded an Android app with jig and let the
agent choose the UI. They disliked the result, generated a proper design with a
separate tool, and dropped that design artifact into the repo intending to
retrofit the project onto it. jig and the agent kept building on the **old**
design and only patched at the edges — several specs, ADRs, and future-work
drafts had already encoded the old design as settled truth, so the new artifact
entered as an **inert file with no authority** and the consistency machinery
faithfully carried the dead premise forward.

The pattern generalizes. A **load-bearing reference** is any authoritative
external input the corpus is premised on: a design system, a test-infrastructure
choice, a vendor / API contract, a compliance regime, a target platform, **a
product-positioning / strategic-vision shift** (the n=2 servo case — Design
notes). When one moves, **two distinct things fail:**

- **Correction** — once someone *recognizes* the shift, there is no operation
  that *re-baselines* the corpus. `adr.py supersede` is 1:1 and decision-scoped;
  `migrate` brings a project *into* jig; `jig:refactor` preserves behaviour. With
  no re-baseline primitive, the agent does the locally-rational thing — patch at
  the edges. **This spec closes this gap.**
- **Noticing** — silent drift, a reference moving without anyone flagging it,
  goes unsurfaced. A user who can *invoke* a command has already noticed; the
  motivating case did not hit this. This spec ships a **best-effort nudge** for
  it and **parks** systematic detection.

[ADR-0024](../../decisions/adr-0024-reference-reframe.md) decides the shape:
reframe is a **lightweight correction capability over the lifecycle spine**
([ADR-0023](../../decisions/adr-0023-lifecycle-family-spine.md) §4), **not** a
new gated lifecycle member. A judgment-only **`/jig:reframe`** skill reads the
corpus against the moved reference and drafts a **keystone reframe-ADR** (which
elevates the new reference to authoritative) plus **retrofit spec drafts**, every
affected artifact assigned a deliberate **disposition**; a competent session then
executes through the existing ADR and spec lifecycles. Systematic blast-radius
detection is **parked** behind explicit triggers (Design notes).

One shortcut is rejected on principle: detecting the shift by scanning each
artifact's `## Assumptions` ledger. That ledger is **risk-gated**
([ADR-0020](../../decisions/adr-0020-spec-frame-hardening.md)) — it logs only
*contested* assumptions, never *settled* premises. The dead design was settled
truth, so it would never appear there. Settled premises are invisible to the
ledger **for the same reason they silently steer the model: they are
unquestioned ground.** Real detection is a genuine project-scope corpus read —
which is exactly why it is parked, not faked (ADR-0024).

## Goals

1. **Close the correction gap** — one named operation re-baselines the corpus
   instead of edge-patching.
2. **Elevate the new reference to authoritative** — the keystone reframe-ADR
   turns an inert dropped-in file into an accepted decision the corpus must
   honour.
3. **Disposition discipline** — every affected artifact gets a deliberate fate
   (no silent omission), each routing to an operation that already exists.
4. **Surface coverage, don't fake it** — the keystone manifest carries an
   explicit **two-level coverage floor** (L1: every deterministically-listable
   top-level artifact class marked `scanned`/`excused`; L2: an artifact-level
   read of the classes the reference *touches*), plus method + residual
   uncertainty, human-confirmed at the ADR's frame-critique `accept` gate — so an
   omission (whole-class **or** intra-class) must be *written down* and "did we
   catch everything?" becomes a checked decision rather than a silent assumption
   ([ADR-0024](../../decisions/adr-0024-reference-reframe.md) §2–§4).
5. **Best-effort noticing** — a soft standing practice ("reframe before building
   on a new reference"), explicitly not a detector.
6. **Least machinery** — a judgment skill riding existing lifecycles; **no new
   `.py`**, no detection engine, no `references:` tagging.
7. **Stay soft** — jig drafts and recommends; the human decides and the session
   executes ([ADR-0011](../../decisions/adr-0011-spec-gate-model.md)
   deliberateness).

## Non-goals

- **Systematic blast-radius detection** — a project-scope agentic corpus read.
  **Parked** behind triggers T1/T2/T3 (Design notes); the manual corpus read +
  coverage statement is the n=1 path.
- **`references:` frontmatter tagging** and the **spec 024-02 corpus-walking
  helper** — parked with detection; built only when demand-pulled.
- **A `reframe.py` / a new gated lifecycle member** (ADR-0024 Option B) —
  rejected at n=1: a reframe has no distinct intake→DONE backbone, so a state
  machine fights ADR-0023 §4 and a third concrete `transition` would mis-trigger
  the `_common/lifecycle.py` extraction.
- **Detection via the `## Assumptions` ledger** — rejected on principle
  (risk-gated; structurally blind to settled premises — Overview).
- **Heavy auto-execution** of the reframe — execution is session-driven by
  design (ADR-0024 §6).
- **A noticing hook / automated trigger** — parked with detection; the nudge is
  doc-only and soft (defense-in-depth — ADR-0011 /
  [ADR-0013](../../decisions/adr-0013-security-floor-policy.md)).
- **Changes to `/jig:analyze`** — untouched; reuse of analyze is *conceptual*
  (its six-category model), not code (analyze is judgment-only, no reusable
  `.py`).

## Assumptions

_None unverified._ The load-bearing runnable-surface claims are grounded:
`adr.py new` reserves a keystone ADR that inherits the frame-critique `accept`
gate and is stamped `frame_review: true` by default (*probed* in
[ADR-0024](../../decisions/adr-0024-reference-reframe.md) — `adr.py`'s
`_gate_frame_critique()` refuses the Proposed→Accepted flip without a passing
verdict); `workflow.py new` reserves + scaffolds a review-gated spec (exercised
when this spec was reserved). The design's binding *risk* — enumeration
completeness over *settled* premises — is **not** a runnable-surface assumption;
it is owned in ADR-0024 (§Assumptions §4) and pressure-tested by `frame_review`
on slice 067-01 (Design notes).

## Decomposition

SPIDR axis: an **Interface + Rules** mix. The **`/jig:reframe`** skill is the
**Interface** onto the corpus; the disposition vocabulary and the keystone-ADR /
manifest shape are **Rules**; the noticing practice is a **Rule**. Each slice is
independently **vertical** (delivers usable value end-to-end). **Spike
rejected** — the substrate is known: `adr.py new` / `workflow.py new` already
reserve + scaffold lifecycle-gated artifacts, the judgment-skill pattern is
proven (`/jig:clarify`,
[`/jig:explain`](../065-lower-vocabulary-barrier/spec.md) — SKILL.md, no `.py`),
and ADR-0024 resolved the design.

| Slice | Delivers | Role |
|---|---|---|
| 067-01 | **The `/jig:reframe` skill** — reads the corpus against a moved reference; drafts the keystone reframe-ADR via `adr.py new` (re-baselining manifest + per-artifact dispositions + coverage statement; old premise superseded). The load-bearing slice. | Interface |
| 067-02 | **Retrofit spec drafts** — for each `retrofit` disposition, the skill also mints a retrofit spec draft via `workflow.py new`, goaled on and `## Assumptions`-anchored to the new reference. | Interface |
| 067-03 | **The noticing nudge** — a soft standing practice (`docs/workflow.md` + scaffold template + lifecycle-skill cross-refs) to reframe before building on a new reference; best-effort, no detector. | Rule |

## Design notes

- **Capability over the spine, not a member** (ADR-0023 §4 / ADR-0024 §5). A
  reframe's arc (recognize → decide dispositions → execute) *orchestrates*
  existing lifecycles; every gate it relies on belongs to the ADR or spec it
  spawns. It adds **no concrete `transition`**, no state machine, and does
  **not** advance the rule-of-three extraction count. Shipping as its own skill
  is a user-facing-surface choice, not a lifecycle one.
- **Judgment-only, no `.py`** (like `/jig:explain`, `/jig:clarify`). The skill
  orchestrates `adr.py new` + `workflow.py new` + model judgment over the
  existing scaffolding. Its testable surface is **structural** (SKILL.md present
  + registered; the keystone-ADR / manifest / coverage shape it *specifies*; the
  deferral language); the *quality* of the corpus read is judgment, exercised by
  the skill prompt + the frame-critique gate — not a unit test (the accepted
  judgment-skill gap, same as
  [spec 065](../065-lower-vocabulary-barrier/spec.md)).
- **The keystone ADR rides the real ADR lifecycle** → it is **frame-critique-
  gated at `accept`** (probed: `adr.py`'s `_gate_frame_critique()` refuses the
  Proposed→Accepted flip without a passing verdict). This is load-bearing: the
  coverage statement is **human-confirmed at that gate**.
- **Enumeration completeness is the binding risk** (ADR-0024 §Assumptions §4 /
  Kill criteria / trigger T1). Finding every artifact that encodes a *settled*
  premise is the hard part — and settled premises are invisible (Overview). The
  minimal skill does **not** pretend to solve enumeration; it **reduces and
  surfaces** it via the **two-level coverage floor** (ADR-0024 §2–§3): **L1** a
  per-class `scanned`/`excused` walk of the deterministically-listable top-level
  classes (catches a whole class dropped — the n=2 servo `skills/` miss), and
  **L2** an artifact-level read within the classes the reference *touches*
  (catches an **intra-class** miss — the motivating Android-design shape, where a
  dead-premise file lives inside a class a class-level floor would mark
  `scanned`). A faithful-but-partial re-baseline is thus caught at the `accept`
  gate rather than reproducing the motivating failure under a keystone ADR; the
  irreducible residual (untouched-class misscoping; within-class miss;
  rubber-stamped `excused`) is backstopped by **T1's two-pronged evidence**
  (accept-time floor **or** post-reframe discovery of a surviving dead-premise
  artifact — ADR-0024 §7). This is why **067-01 carries `frame_review: true`** —
  the pre-implementation pass pressure-tests whether the SKILL.md actually makes a
  weak coverage statement *visible* rather than rubber-stampable.
- **Disposition vocabulary** (ADR-0024 §3), each routing to an existing
  operation:

  | Disposition | Meaning | Routes to |
  |---|---|---|
  | `reaffirm` | premise survives the new reference | refresh `last_verified` + note the reframe |
  | `amend` | closed record, still valid, needs a pointer | `## Amendments` ([ADR-0010](../../decisions/adr-0010-amendment-scope-records-vs-live-prose.md)) |
  | `supersede` | decision now wrong | `adr.py supersede` / superseding spec |
  | `retire-draft` | future-work on the dead premise | DEFERRED or discard — **do first; drafts mint dead-premise work** |
  | `retrofit` | shipped code must change | a slice in the retrofit spec (067-02) |
  | `rewrite` | **live, non-record prose** whose framing must change (not a closed record → not `amend`; not a decision → not `supersede`; not code → not `retrofit`) | rewrite in place, citing the keystone ADR. Per [ADR-0024](../../decisions/adr-0024-reference-reframe.md) §3 (added 2026-06-27, n=2); lands with 067-01 when ADR-0024 is accepted. |

- **n=2 evidence (servo EDD reframe, 2026-06-27 — `docs/inbox.md`).** A second
  real reframe (servo repositioned "autonomous loop" → "Evaluation-Driven
  Development engine"; the new reference was a dropped-in vision brief) was
  executed **ad hoc, without this workflow**, and reproduced the exact failure
  067 guards against: the corpus read covered only `docs/` + `README` and **missed
  the flagship skill's description** (still "closed-loop, unattended agent-operations
  infrastructure"). This **corroborates the binding-risk control** — the **L1
  coverage floor** (067-01 AC5), which lists `skills/` as a top-level class to mark
  `scanned`/`excused`, would have forced "did we scan `skills/`?" (a *free-text*
  coverage note would not) — and is T1-adjacent evidence that an undisciplined
  single-pass read under-catches (not a clean T1 trip, since the workflow wasn't
  used). It also surfaced **two
  shape refinements**, both folded in above / below: (1) the **`rewrite`
  disposition** for live non-record prose — a documentation-shaped reframe is
  *mostly* prose rewrites, which the original five dispositions don't fit; (2) an
  **emergent-work** manifest section — a reframe can *spawn* net-new forward
  specs/ADRs the new framing reveals (servo minted 3 ADRs + 4 specs), which the
  disposition model (fates of *existing* artifacts + retrofit specs) does not
  represent. Both are now in **ADR-0024 §3** (added 2026-06-27); they land with
  the rest of 067-01 when ADR-0024 is accepted (067-01's DoR).
- **Tier placement: Tier-1.** Sibling of the other judgment skills and rides
  Tier-1 lifecycle tooling (`adr.py` / `workflow.py`). Registration surfaces (the
  spec 065-03 lesson — miss one and reconciliation surprises): `scaffold.py`
  `_TIER_SKILLS["tier-1"]` (source of truth), `install_contract.py`
  `EXPECTED_SKILLS`, `scaffold_contract.py` `_TIER_SKILLS["tier-1"]`, the root
  `CLAUDE.md` Skills table, plus the pinned-tier-set guards (`test_scaffold`
  `EXPECTED_TIER_1`, `test_migrate` `TIER1`, the `docs/product-vision.md` Tier-1
  inventory + headline count, and the `vision-elicitation` worked-example tier
  line).
- **Parked work + triggers** (ADR-0024 §7), recorded so they are not
  re-proposed. **Un-park systematic detection when ANY:** **T1** — a real
  reframe's human-checked coverage shows the single-pass read materially
  under-catches (gated at the *first* reframe, not a second miss); **T2** — the
  corpus outgrows a reliable single-pass read (the
  [spec 055](../055-context-cost-discipline/spec.md) dumb-zone threshold); **T3**
  — a second consumer (e.g. 024-02) pulls the same corpus-walking / `references:`
  infrastructure. **Graduation to a gated member (Option B)** is a separate,
  higher bar: only if reframes drift *even with good drafts in hand*.
- **Honesty.** A best-effort *correction* floor — it makes re-baselining
  expressible and human-gated; it does not auto-solve enumeration (parked) and
  the nudge is not a reliable silent-drift detector (parked). jig drafts; the
  session executes.

## Slices

- `slice-01-reframe-skill.md` — the `/jig:reframe` skill: corpus read + keystone reframe-ADR (manifest + dispositions + coverage statement) via `adr.py new` (Interface; the load-bearing slice; `arch_review` + `frame_review`)
- `slice-02-retrofit-spec-drafts.md` — one retrofit spec draft per `retrofit` disposition via `workflow.py new`, anchored on the new reference (Interface)
- `slice-03-noticing-nudge.md` — soft standing practice to reframe before building on a new reference; best-effort, no detector (Rule; closing slice)

## Open questions

_Not run through `/jig:clarify` — ADR-0024's frame-critique (4 rounds) hardened
the design; these are the residual leans it recorded._

- **Where does the re-baselining manifest live — inline in the keystone ADR or a
  sibling file?** Lean: **inline**, unless a blast radius is large enough to
  warrant its own file (resolve in 067-01).
- **Does `/jig:reframe` draft on invocation, or also offer a report-only mode?**
  Lean: **draft-on-invoke** (the drafts are the point); a read-only preview is a
  cheap add if wanted (resolve in 067-01).
- **Tier-1 placement** — stated in Design notes; confirm against the live tier
  model when 067-01 wires the registration surfaces.
- **Resolved (ADR-0024 §3, 2026-06-27) — the `rewrite` disposition (n=2).** Live,
  non-record prose whose framing must change fit none of the original five
  dispositions; added to ADR-0024 §3 and the disposition table above. Lands with
  067-01 when ADR-0024 is accepted.
- **Resolved (ADR-0024 §3, 2026-06-27) — the `## Emergent work` manifest section
  (n=2).** A reframe can spawn net-new forward specs/ADRs the new reference
  reveals (distinct from `retrofit`, which fixes *existing* code); the keystone
  manifest records them in a separate section, not a disposition row.

## Clarifications

### Q1: What should `/jig:reframe` do when its corpus read finds no artifact actually encodes the moved premise — or when the named reference can't be located?
_(category: Edge Cases & Failure Modes)_

Report "nothing to re-baseline". If the read finds nothing the reference
invalidates, the skill says so and drafts **no** keystone ADR; if the reference
can't be located, it refuses and asks for a path. No empty keystone ADR is
minted. (Resolves a 067-01 edge case — add the no-op / not-locatable refusal to
the skill's behaviour.)

### Q2: 067-01's DoR requires ADR-0024 Accepted, but it's currently Proposed. How should the spec record this dependency, and do we accept ADR-0024 now?
_(category: Dependencies & Blockers)_

Land the spec as DRAFT; accept ADR-0024 later. ADR-0024 stays Proposed — the
spec lands but 067-01 remains blocked on a separate `adr.py accept 0024`. The
DoR dependency stands as a hard blocker (no implementation until the keystone
ADR is accepted).

### Q3: The coverage statement (067-01 AC5) is the binding-risk control but can't be unit-tested for honesty. Are the planned safeguards enough?
_(category: Acceptance Criteria Testability)_

Yes — keep the planned trio: the `frame_review` pre-implementation pass + a
structural test that the coverage statement names scope / method / what-was-NOT-
covered + human confirmation at the ADR `accept` gate. Don't over-engineer at
n=1. (`frame_review` stays on 067-01.)

### Q4: When the corpus is large enough that a single-pass read is unreliable (the T2 condition) but T2 hasn't formally tripped, what does the skill do at invoke time?
_(category: Non-functional Requirements)_

Proceed, and flag the limit in the coverage statement. The skill attempts the
read; the coverage statement must disclose when the corpus was large /
single-pass / possibly incomplete — making the limit visible at the `accept`
gate (which is what trips T1). No hard size-refusal.

### Coverage summary

| Category | Status |
|---|---|
| Scope & Boundaries | Clear |
| Acceptance Criteria Testability | Resolved (Q3) |
| Dependencies & Blockers | Resolved (Q2) |
| Non-functional Requirements | Resolved (Q4) |
| Edge Cases & Failure Modes | Resolved (Q1) |
| Terminology Consistency | Clear |
